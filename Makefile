.PHONY: up down build rebuild logs logs-backend logs-frontend \
        shell-backend shell-frontend restart ps health clean run-backend run-frontend kill-exec

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
run-backend:
	docker compose exec -T backend sh -c "$(CMD)"

run-frontend:
	docker compose exec -T frontend sh -c "$(CMD)"

# ── emergency escape ──────────────────────────────────────────────────────────
# If you ever get stuck in a shell: press Ctrl+P then Ctrl+Q to detach,
# or open a NEW terminal tab and run:  make kill-exec
kill-exec:
	@echo "Killing all docker exec sessions..."
	@docker ps -q | xargs -I{} docker exec {} kill -9 1 2>/dev/null || true
	@echo "Done. Your original terminal should now be free."

# ── cleanup ───────────────────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	docker system prune -f
