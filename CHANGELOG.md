# Changelog

## 0.3.1 — 2026-11-13

- `install.sh --force` / `install.ps1 -Force` now preserve `workspaces/` projects instead of deleting them with the skill directory.
- The installed skill now includes the `mvwb` fallback launcher (with executable bit), so the documented command works after install.
- `mvwb init` now creates an empty project by default (`原文/` placeholders, `mvs=[]`, built `workbench.html`); `mvwb init <name> --demo` copies the demo.
- `mvwb build` / `mvwb check` resolve relative `--data` / `--out` / `--workbench` against the skill root when the path does not exist in the current directory.
- Simplified the package: removed the duplicated `START_HERE.md`, screenshots/docs and GitHub download/clone instructions; the zip is the distribution channel. README is now a one-page quick start.
- Installers no longer copy `docs/`, `CHANGELOG.md`, `SECURITY.md` or `START_HERE.md` into the skill directory.

## 0.3.0 — 2026-11-13

- Removed the local config service. `workbench.html` is a plain static file again: open it by double-click or `file://`; no port, no server, no background process.
- `mvwb open` now only opens the local HTML; `mvwb server` / `mvwb status` / `mv_keys_server.py` / `mv_keys_ui.js` removed.
- Key config moved to CLI: `mvwb keys set runninghub|router` (hidden input). Balance snapshot: `mvwb keys balance --data data.json` + `mvwb build`.
- Workbench top bar no longer has a Key config button; it shows a read-only masked snapshot.
- Added `references/step-contract.md`: fixed input questions, output shape, self-check and gate for every step.
- Added `mvwb check` to verify all local asset/video/music references; completion now requires 0 missing.
- Fixed `mvwb rh/muse/timeline` passthrough argument swallowing (v0.2.7 regression).
- Fixed RunningHub raw traceback on business errors (fake key / wrong app id).

## 0.2.7 — 2026-11-13

- Renamed the skill to `zz-mv-gongzuotai`; installer target and runtime zip follow the new name.
- Repo name remains `mv-workbench`.

## 0.2.6 — 2026-11-13

- Fixed the Windows test harness decoding `mvwb status` output as cp1252; CLI output is UTF-8.

## 0.2.5 — 2026-11-13

- Fixed Windows `mvwb status` timeout: check 5 ports with 0.25s instead of 20 × 0.6s.

## 0.2.4 — 2026-11-13

- Added `mvwb open` (reuse/start service, auto-select free port) and `mvwb status`; reuse checks the served workbench path, so an old project on the same port is not reused.
- Static page now shows “只读 · Key 需服务版” and sets `data-mv-mode=static|service`.
- SKILL hard rule: Key/balance tasks must use service mode; never `file://`/plain static server.

## 0.2.3 — 2026-11-13

- Removed unused demo SVGs (`poster.svg`, `scene_store.svg`).
- Merged the two Muse prompt guides into `references/prompts/muse-guide.md`.
- Added target_duration vs actual music timeline contract for video segment planning.
- Added runtime zip (no tests/.github/dev config).

## 0.2.1 — 2026-11-13

- Windows console UTF-8 fallback for Chinese output in CI/pipes.
- CI green: Ubuntu 22.04/24.04, macOS, Windows; Python 3.9/3.11.

## 0.2.0 — 2026-11-13

- **Single-skill refactor**: `zz-mv-gongzuotai` is now the only skill; all MV logic lives here.
- Removed `zz-mv-factory` and `zz-mv-trim` as separate skills; workbench contract moved to `references/workbench-contract.md`, trim removed entirely.
- Removed the machine rough-cut stage: the project ends at video segments + `handoff`.
- Each MV now has its own directory: `01_music/`, `02_assets/`, `03_segments/`, `handoff_v1.json`.
- Folded model/prompt knowledge into `references/prompts/` and provider API into `references/providers/`.
- Folded RunningHub operations into `scripts/providers/runninghub.py` + `references/providers/runninghub.md`; no separate RH skill.
- Installer now installs one skill to `~/.agents/skills/zz-mv-gongzuotai`.
- `mvwb` commands: doctor / demo / server / keys / quote / rh / muse / timeline / init / build.
- Demo restructured to per-MV directories; no client data.

## 0.1.0 — 2026-11-13

- Initial public packaging with multiple skills.
- Local Key config service, Router Muse adapter, clean demo, macOS/Linux/Windows installers.
