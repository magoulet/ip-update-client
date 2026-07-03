# AGENTS.md

## Overview

Single-file Python script (`main.py`) that detects public IP changes and updates DNS providers + sends notifications. No packages, no tests, no CI, no build system.

## Key files

- `main.py` — all logic (entry point via `if __name__ == "__main__"`)
- `config.yml` — runtime config with secrets (gitignored, never commit)
- `config_example.yml` — template for `config.yml`
- `prevIpAddr.pickle` — persisted last-known IP (gitignored)
- `run_ip_update.sh` — shell wrapper for cron: activates `.venv`, runs `main.py`, pings healthcheck on success

## Commands

```bash
# Install deps (uses .venv)
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Run
python main.py
```

No tests, no lint, no typecheck exist.

## Architecture

Flow: `currentIP()` → compare with pickle → if changed: update DNS providers → send notification → save pickle.

DNS providers currently active: OpenDNS, Cloudflare. AWS Route 53 is present but commented out in `__main__`. Google Domains code removed from `__main__` (config_example.yml still references it).

Notification method selected by `cfg['notifications']['method']`: `telegram` | `mailgun` | `ntfy`.

## Gotchas

- `config.yml` contains live secrets (API keys, passwords). It is gitignored via `*.yml` pattern. Never commit it or log its contents.
- `pickle` is used for state — no schema, no migration path. Changing IP source or adding fields requires manual handling.
- `config_example.yml` is stale: missing `notifications`, `ntfy`, `mailgun`, `cloudflare` sections that `main.py` actually uses.
- Cloudflare config nests under `cfg['cloudflare']` (not top-level like other providers) — each domain has its own `api_token` and `zone_id`.
- `run_ip_update.sh` hardcodes the project path and a healthcheck URL to `http://tars:8000/ping/...` — update if deploying elsewhere.
- `main.py` uses `yaml.load(open('config.yml'), Loader=yaml.FullLoader)` — relative path, must run from repo root.
