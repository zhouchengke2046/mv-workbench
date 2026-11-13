# Security

## API keys

- Keys are stored only in `~/.config/mv-workbench/keys.json` (directory 0700, file 0600 on macOS/Linux).
- Keys are configured with `mvwb keys set runninghub|router` (hidden input) or a manual edit of the local file. Raw keys never enter HTML, `DATA`, logs, or screenshots.
- `mv_keys.py exec` clears stale `RUNNINGHUB_API_KEY` / `ROUTER_API_KEY` / `APIMART_KEY` from the child environment, then injects the local keys.
- Do not commit `keys.json`, `.env`, screenshots with keys, or shell history containing keys.
- Do not paste keys into an agent chat. If a key was pasted, revoke it at the provider and create a new one.

## Workbench

- The workbench is a plain static HTML file. It starts no server, opens no port, and makes no network requests.
- `DATA.keys` contains only a masked key, balance snapshot, and check time.
- Sharing the HTML shares the project view but not the key file.

## Reporting

Open a private security advisory on GitHub, or contact the maintainer. Do not include real keys in reports.
