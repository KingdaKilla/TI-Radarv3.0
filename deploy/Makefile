# =============================================================================
# Makefile — TI-Radar v2 Build-Automatisierung
# =============================================================================

PROJECT_ROOT := $(shell cd $(dir $(abspath $(lastword $(MAKEFILE_LIST))))/.. && pwd)
COMPOSE_CMD  := docker compose --env-file $(PROJECT_ROOT)/.env -f $(PROJECT_ROOT)/deploy/docker-compose.yml

.PHONY: help proto lint test docker up down clean

help: ## Hilfe anzeigen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# gRPC Stubs
# ---------------------------------------------------------------------------

proto: ## gRPC Python-Stubs aus proto/ generieren
	bash $(PROJECT_ROOT)/scripts/generate_protos.sh

# ---------------------------------------------------------------------------
# Code Quality
# ---------------------------------------------------------------------------

lint: ## Ruff + Mypy auf shared/ und services/
	ruff check $(PROJECT_ROOT)/packages/shared/ $(PROJECT_ROOT)/services/
	mypy $(PROJECT_ROOT)/packages/shared/domain/ --ignore-missing-imports

test: ## Pytest auf alle Services
	pytest $(PROJECT_ROOT)/services/*/tests/ $(PROJECT_ROOT)/packages/shared/tests/ -v --tb=short

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

docker: ## Alle Docker-Images bauen
	$(COMPOSE_CMD) build

up: ## Stack starten (detached)
	$(COMPOSE_CMD) up -d

down: ## Stack stoppen
	$(COMPOSE_CMD) down

logs: ## Docker Compose Logs folgen
	$(COMPOSE_CMD) logs -f --tail=50

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

install-shared: ## Shared-Package im editable Modus installieren
	pip install -e $(PROJECT_ROOT)/packages/shared/

install-all: install-shared ## Alle Services installieren (editable)
	@for svc in $(PROJECT_ROOT)/services/*/; do \
		if [ -f "$$svc/pyproject.toml" ]; then \
			echo "Installing $$svc..."; \
			pip install -e "$$svc"; \
		fi; \
	done

clean: ## Build-Artefakte aufraeumen
	find $(PROJECT_ROOT) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(PROJECT_ROOT) -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find $(PROJECT_ROOT) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find $(PROJECT_ROOT) -name "*.pyc" -delete 2>/dev/null || true
