# Changelog

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

- **Single-skill refactor**: `mv-gongzuotai` is now the only skill; all MV logic lives here.
- Removed `zz-mv-factory` and `zz-mv-trim` as separate skills; workbench contract moved to `references/workbench-contract.md`, trim removed entirely.
- Removed the machine rough-cut stage: the project ends at video segments + `handoff`.
- Each MV now has its own directory: `01_music/`, `02_assets/`, `03_segments/`, `handoff_v1.json`.
- Folded model/prompt knowledge into `references/prompts/` and provider API into `references/providers/`.
- Folded RunningHub operations into `scripts/providers/runninghub.py` + `references/providers/runninghub.md`; no separate RH skill.
- Installer now installs one skill to `~/.agents/skills/mv-gongzuotai`.
- `mvwb` commands: doctor / demo / server / keys / quote / rh / muse / timeline / init / build.
- Demo restructured to per-MV directories; no client data.

## 0.1.0 — 2026-11-13

- Initial public packaging with multiple skills.
- Local Key config service, Router Muse adapter, clean demo, macOS/Linux/Windows installers.
