"""Analyze-Panel-Router — REST-Endpoint für LLM-gestützte Panel-Analyse.

v3.5.0: Forwardet Frontend-Requests (`POST /api/analyze-panel`) per gRPC
an den `llm-svc`. Graceful Degradation: Bei fehlender LLM-Verfügbarkeit
oder Fehlern wird ein leeres Ergebnis zurückgegeben, damit die UI nicht
bricht.
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
router = APIRouter(prefix="/api/v1", tags=["analyze"])


class AnalyzePanelRequestBody(BaseModel):
    technology: str = Field(..., min_length=1, max_length=200)
    use_case_key: str = Field(..., min_length=1, max_length=64)
    panel_data: dict[str, Any]
    language: str = "de"


class AnalyzePanelResponseBody(BaseModel):
    analysis_text: str
    model_used: str
    key_findings: list[str]
    confidence: float
    processing_time_ms: int


_llm_channel_lock = asyncio.Lock()
_llm_stub: Any = None


async def _get_llm_stub(settings: Settings) -> Any:
    """Lazy-initialisierter gRPC-Stub für llm-svc."""
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
        logger.info("llm_stub_erzeugt", address=settings.llm_address)
        return _llm_stub


@router.post(
    "/analyze-panel",
    response_model=AnalyzePanelResponseBody,
    dependencies=[Depends(verify_api_key)],
)
async def analyze_panel(
    body: AnalyzePanelRequestBody,
    http_request: Request,
) -> AnalyzePanelResponseBody:
    """LLM-gestützte Analyse eines UC-Panels.

    Forwardet Panel-Daten an den `llm-svc` (AnalyzePanel gRPC-Call) und
    liefert eine Markdown-Analyse zurück. Bei Fehlern/Timeout wird ein
    leeres Ergebnis zurückgegeben (Graceful Degradation), damit die UI
    nicht blockiert.
    """
    t0 = time.monotonic()
    settings: Settings = http_request.app.state.settings

    # Empty result fallback helper
    def empty_result() -> AnalyzePanelResponseBody:
        return AnalyzePanelResponseBody(
            analysis_text="",
            model_used="none",
            key_findings=[],
            confidence=0.0,
            processing_time_ms=int((time.monotonic() - t0) * 1000),
        )

    stub = await _get_llm_stub(settings)
    if stub is None:
        return empty_result()

    try:
        from shared.generated.python import llm_pb2  # type: ignore
    except ImportError:
        logger.warning("llm_pb2_nicht_verfuegbar")
        return empty_result()

    try:
        panel_json = json.dumps(body.panel_data, ensure_ascii=False)
        grpc_request = llm_pb2.AnalyzePanelRequest(
            technology=body.technology,
            use_case_key=body.use_case_key,
            panel_data_json=panel_json,
            language=body.language or "de",
        )
        grpc_response = await asyncio.wait_for(
            stub.AnalyzePanel(grpc_request),
            timeout=settings.llm_timeout_s,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return AnalyzePanelResponseBody(
            analysis_text=str(grpc_response.analysis_text or ""),
            model_used=str(grpc_response.model_used or ""),
            key_findings=list(grpc_response.key_findings),
            confidence=float(grpc_response.confidence or 0.0),
            processing_time_ms=elapsed_ms,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "analyze_panel_timeout",
            technology=body.technology,
            uc=body.use_case_key,
            timeout=settings.llm_timeout_s,
        )
        return empty_result()
    except grpc.RpcError as exc:  # type: ignore[misc]
        logger.warning(
            "analyze_panel_grpc_fehler",
            technology=body.technology,
            uc=body.use_case_key,
            code=str(exc.code()) if hasattr(exc, "code") else "unknown",
        )
        return empty_result()
    except Exception as exc:
        logger.error(
            "analyze_panel_fehler",
            technology=body.technology,
            uc=body.use_case_key,
            error=str(exc),
        )
        return empty_result()
