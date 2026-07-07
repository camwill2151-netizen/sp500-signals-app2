.PHONY: up down build rebuild logs logs-backend logs-frontend \
        restart ps health clean run-backend run-frontend kill-exec .validate-cmd

# ── lifecycle ─────────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

restart:
	docker compose restart

# ── observability ─────────────────────────────────────────────────────────────
logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

ps:
	docker compose ps

health:
	@echo "=== backend ===" && \
	docker compose exec -T backend python -c \
	  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())" \
	  2>&1 || echo "backend not healthy"

# ── safe one-shot exec (no interactive shell, no quote trap) ──────────────────
# Usage: make run-backend CMD="python -c 'print(1)'"
# Blocks dangerous shell control operators (; & | ` $ < >) in CMD.
.validate-cmd:
	@test -n "$(CMD)" || (echo "Usage: make run-backend CMD='...' (or run-frontend)" && exit 1)
	@if printf '%s' "$(CMD)" | grep -q '[;&|`$$<>]'; then echo "Unsafe CMD: control operators are not allowed"; exit 1; fi
	@if printf '%s' "$(CMD)" | grep -q '[[:cntrl:]]'; then echo "Unsafe CMD: control characters are not allowed"; exit 1; fi

run-backend: .validate-cmd
	docker compose exec -T backend sh -c 'exec sh -c "$$1"' _ "$(CMD)"

run-frontend: .validate-cmd
	docker compose exec -T frontend sh -c 'exec sh -c "$$1"' _ "$(CMD)"

# ── emergency escape ──────────────────────────────────────────────────────────
# If you ever get stuck in a shell: press Ctrl+P then Ctrl+Q to detach,
# or open a NEW terminal tab and run:  make kill-exec
kill-exec:
	@echo "Restarting services to clear stuck exec sessions..."
	@docker compose restart
	@echo "Done. Reattach with logs/health commands as needed."

# ── cleanup ───────────────────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	docker system prune -f
