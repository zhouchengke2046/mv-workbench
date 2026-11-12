# Changelog

## 0.1.0 — 2026-11-13

- Public packaging of the MV workbench skill suite.
- Added `mvwb` CLI: doctor / demo / server / keys / quote / rh / muse / timeline / init / build.
- Added local Key config service (`mv_keys_server.py` + `mv_keys_ui.js`), loopback only, masked keys.
- Added Router (TokenTech/new-api) Muse adapter: `POST /v1/videos` async, 2s tested.
- Added `ace-music` and `muse-router` skills; removed APIMart as the default path.
- Added clean demo: original lyrics/story, SVG placeholder assets, silent audio, 3 MVs.
- Added macOS/Linux `install.sh` and Windows `install.ps1` / `mvwb.cmd`.
- Added tests, secret scan, GitHub Actions CI.
