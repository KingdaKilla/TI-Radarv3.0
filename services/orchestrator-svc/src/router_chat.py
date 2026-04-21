"""Chat-Router — REST-Endpoint für interaktiven RAG-Chat.

v3.6.0: Retrieval-Augmented-Generation aktiviert. Der Endpoint ruft zuerst
den `retrieval-svc` (semantische pgvector-Suche über Patents/Projects/Papers)
und übergibt die Top-K Dokumente als Kontext an den `llm-svc`. Wenn
Retrieval nicht verfügbar ist oder die DB-Embedding-Spalten leer sind
(vor dem initialen Embedding-Job), liefert die Retrieval-Ebene eine leere
Dokument-Liste und der Chat nutzt nur den `panel_context`. Der Chat
funktioniert also in jedem Zustand — RAG ist ein Enhancement, kein Blocker.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import grpc
import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.auth import verify_api_key
from src.config import Settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatMessageIn(BaseModel):
    role: str = Field(..., min_length=1, max_length=32)
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequestBody(BaseModel):
    technology: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessageIn] = []
    panel_context: dict[str, Any] | None = None


class ChatResponseBody(BaseModel):
    answer: str
    sources: list[str]
    key_findings: list[str]
    model_used: str
    processing_time_ms: int


_llm_channel_lock = asyncio.Lock()
_llm_stub: Any = None
_retrieval_channel_lock = asyncio.Lock()
_retrieval_stub: Any = None


async def _get_llm_stub(settings: Settings) -> Any:
    """Lazy-initialisierter gRPC-Stub für llm-svc (identisch zu router_analyze)."""
    global _llm_stub
    if _llm_stub is not None:
        return _llm_stub
    async with _llm_channel_lock:
        if _llm_stub is not None:
            return _llm_stub
        try:
            from shared.generated.python import llm_pb2_grpc  # type: ignore
        except ImportError as exc:
            logger.warning("llm_stubs_nicht_verfuegbar", error=str(exc))
            return None
        channel = grpc.aio.insecure_channel(
            settings.llm_address,
            options=[
                ("grpc.max_receive_message_length", settings.grpc_max_message_size),
                ("grpc.max_send_message_length", settings.grpc_max_message_size),
            ],
        )
        _llm_stub = llm_pb2_grpc.LlmAnalysisServiceStub(channel)
        logger.info("llm_stub_erzeugt_chat", address=settings.llm_address)
        return _llm_stub


async def _get_retrieval_stub(settings: Settings) -> Any:
    """Lazy-initialisierter gRPC-Stub für retrieval-svc (v3.6.0)."""
    global _retrieval_stub
    if _retrieval_stub is not None:
        return _retrieval_stub
    async with _retrieval_channel_lock:
        if _retrieval_stub is not None:
            return _retrieval_stub
        try:
            from shared.generated.python import retrieval_pb2_grpc  # type: ignore
        except ImportError as exc:
            logger.warning("retrieval_stubs_nicht_verfuegbar", error=str(exc))
            return None
        channel = grpc.aio.insecure_channel(
            settings.retrieval_address,
            options=[
                ("grpc.max_receive_message_length", settings.grpc_max_message_size),
                ("grpc.max_send_message_length", settings.grpc_max_message_size),
            ],
        )
        _retrieval_stub = retrieval_pb2_grpc.RetrievalServiceStub(channel)
        logger.info("retrieval_stub_erzeugt", address=settings.retrieval_address)
        return _retrieval_stub


async def _retrieve_context(
    settings: Settings, technology: str, query: str
) -> list[Any]:
    """Ruft retrieval-svc für semantische Suche. Leere Liste bei Fehler."""
    stub = await _get_retrieval_stub(settings)
    if stub is None:
        return []
    try:
        from shared.generated.python import retrieval_pb2  # type: ignore
    except ImportError:
        return []
    try:
        req = retrieval_pb2.RetrievalRequest(
            technology=technology,
            query=query,
            top_k=settings.retrieval_top_k,
            sources=["patents", "projects", "papers"],
        )
        resp = await asyncio.wait_for(
            stub.Retrieve(req), timeout=settings.retrieval_timeout_s
        )
        return list(resp.documents)
    except asyncio.TimeoutError:
        logger.warning("retrieval_timeout", technology=technology)
        return []
    except grpc.RpcError as exc:  # type: ignore[misc]
        logger.info(
            "retrieval_grpc_unavailable",
            code=str(exc.code()) if hasattr(exc, "code") else "unknown",
            hint="retrieval-svc nicht deployed oder Embeddings leer; Chat läuft ohne RAG weiter",
        )
        return []
    except Exception as exc:
        logger.warning("retrieval_fehler", error=str(exc))
        return []


@router.post(
    "/chat",
    response_model=ChatResponseBody,
    dependencies=[Depends(verify_api_key)],
)
async def chat(
    body: ChatRequestBody,
    http_request: Request,
) -> ChatResponseBody:
    """Interaktiver Chat: Benutzer-Frage → LLM → Antwort.

    Nutzt Panel-Context (aktuell angezeigte Analyse-Daten) als
    Ground-Truth. Kein RAG-Retrieval in v3.5.1 — context_documents
    wird leer übergeben.
    """
    t0 = time.monotonic()
    settings: Settings = http_request.app.state.settings

    def fallback(msg: str = "Entschuldigung, der Chat ist momentan nicht verfügbar.") -> ChatResponseBody:
        return ChatResponseBody(
            answer=msg,
            sources=[],
            key_findings=[],
            model_used="none",
            processing_time_ms=int((time.monotonic() - t0) * 1000),
        )

    stub = await _get_llm_stub(settings)
    if stub is None:
        return fallback()

    try:
        from shared.generated.python import llm_pb2  # type: ignore
    except ImportError:
        logger.warning("llm_pb2_nicht_verfuegbar_chat")
        return fallback()

    # v3.6.0: RAG-Retrieval vor dem LLM-Call (Graceful bei Fehler)
    context_docs = await _retrieve_context(settings, body.technology, body.message)
    if context_docs:
        logger.info(
            "retrieval_erfolgreich",
            technology=body.technology,
            docs=len(context_docs),
        )

    try:
        history_msgs = [
            llm_pb2.ChatMessage(role=m.role, content=m.content) for m in body.history
        ]
        panel_context_json = (
            json.dumps(body.panel_context, ensure_ascii=False)
            if body.panel_context
            else ""
        )
        chat_request = llm_pb2.ChatRequest(
            technology=body.technology,
            user_message=body.message,
            context_documents=context_docs,  # v3.6.0: RAG-Dokumente
            history=history_msgs,
            language="de",
            panel_context_json=panel_context_json,
        )
        chat_response = await asyncio.wait_for(
            stub.Chat(chat_request),
            timeout=settings.llm_timeout_s,
        )
        return ChatResponseBody(
            answer=str(chat_response.answer or ""),
            sources=list(chat_response.sources),
            key_findings=list(chat_response.key_findings),
            model_used=str(chat_response.model_used or ""),
            processing_time_ms=int((time.monotonic() - t0) * 1000),
        )
    except asyncio.TimeoutError:
        logger.warning("chat_timeout", technology=body.technology, timeout=settings.llm_timeout_s)
        return fallback("Die Anfrage dauert länger als erwartet. Bitte erneut versuchen.")
    except grpc.RpcError as exc:  # type: ignore[misc]
        logger.warning(
            "chat_grpc_fehler",
            technology=body.technology,
            code=str(exc.code()) if hasattr(exc, "code") else "unknown",
        )
        return fallback()
    except Exception as exc:
        logger.error("chat_fehler", technology=body.technology, error=str(exc))
        return fallback()
