"""Orchestrator Service — API-Gateway fuer die TI-Radar v2 Plattform.

Empfaengt REST-Requests vom Frontend und verteilt sie per gRPC
an 12 UC-Microservices. Implementiert Graceful Degradation, Per-UC-Timeouts
und Prometheus-Metriken.
"""

__version__ = "2.0.0"
