# Security

## API keys

- Keys are stored only in `~/.config/mv-workbench/keys.json` (directory 0700, file 0600 on macOS/Linux).
- The workbench UI and `/api/keys` return **masked** keys only; raw keys never enter HTML, `DATA`, logs, or screenshots.
- `mv_keys.py exec` clears stale `RUNNINGHUB_API_KEY` / `ROUTER_API_KEY` / `APIMART_KEY` from the child environment, then injects the local keys.
- Do not commit `keys.json`, `.env`, screenshots with keys, or shell history containing keys.

## Local config server

- Binds `127.0.0.1` only; not reachable from LAN/Internet.
- `POST /api/keys` checks `Origin` and `Content-Type`; cross-site requests are rejected.
- The server only reads/writes the local key file and queries provider balances. It does not run generation, queue jobs, or upload media.
- Any local process running as your user can read the key file; the server does not add remote exposure.

## Reporting

Open a private security advisory on GitHub, or contact the maintainer. Do not include real keys in reports.
