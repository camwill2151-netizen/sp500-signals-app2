.PHONY: up down build rebuild logs logs-backend logs-frontend \
        restart ps health clean run-backend run-frontend kill-exec

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
# Note: CMD is executed via `sh -c`; use trusted local input only.
run-backend:
	@test -n "$(CMD)" || (echo "Usage: make run-backend CMD='...'" && exit 1)
	docker compose exec -T backend sh -c "$(CMD)"

run-frontend:
	@test -n "$(CMD)" || (echo "Usage: make run-frontend CMD='...'" && exit 1)
	docker compose exec -T frontend sh -c "$(CMD)"

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
