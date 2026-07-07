# Terminal Escape Cheatsheet

## Stuck in an unclosed quote (`>` prompt)?
Press `Ctrl+C` — if that doesn't work, type a closing `'` or `"` then press Enter, then Ctrl+C.

## Stuck inside a `docker exec` shell?
- Type `exit` and press Enter
- Or press `Ctrl+D`
- Or press `Ctrl+P` then `Ctrl+Q` (detach without killing)

## Stuck and nothing works?
Open a NEW terminal tab and run:
```bash
make kill-exec
```
or manually:
```bash
docker compose restart
```

## Use the Makefile — never raw docker exec
| Instead of...                        | Use...              |
|--------------------------------------|---------------------|
| `docker compose exec backend bash`   | `make run-backend CMD="python -V"` |
| `docker compose up -d`               | `make up`           |
| `docker compose logs -f`             | `make logs`         |
| `docker compose build --no-cache && docker compose up -d` | `make rebuild` |

Interactive container shells are intentionally disabled here to prevent terminal lockups.
