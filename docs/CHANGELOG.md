# Changelog

## 0.4.12 — 2026-11-14

- `mvwb init --dir <目录>`: create a standalone project in ANY directory (one project per directory), not only under the skill's `workspaces/`. Refuses non-empty dirs; all other commands already take explicit `--data/--out` paths, so a standalone directory is a first-class citizen (verified against the 半糖晚风 project moved out of the test shell).

## 0.4.11 — 2026-11-14

- Progress ring simplified to THREE colors by completion (user decision): green = stage fully generated; orange = in progress (partial like 2/4 images, or tasks running — whole ring breathes via the pulse animation while `status:"generating"`); gray = not started. Derivation is data-driven (`detail.script.body` / current music audio / assets count vs `stages.assets.total` / segments with current videos); Step 3 writes `stages.assets.total` so partial completion is visible. Replaces the per-status color map.

## 0.4.10 — 2026-11-14

- Progress ring now covers all four steps (script → music → assets → video) instead of three, matching the v0.4.5 step system; `stages.script` added to the DATA contract example.
- `STATUS_COLOR` covers the full status vocabulary: planning/planned gray, generating blue (with the previously unused pulse animation wired: any generating stage makes the ring blink), review purple, draft orange, locked green, failed red, stale dark orange.

## 0.4.9 — 2026-11-14

- Fixed video history ordering in the workbench: `videoCell` used "first entry = current", which pushed newly appended v2 into 历史 when data grows append-style (found on the 半糖晚风 workbench). Now `segments[].videos` is append-style with the `current:true` flag marking the current video — the same convention the music table already uses; contract doc updated to match.

## 0.4.8 — 2026-11-14

- Codified the verified main-chain paths (from the 半糖晚风 E2E run) into the skill:
  - New `references/router-playbook.md`: the authoritative path for music / assets / video / timeline / billing reconciliation, snapshot-based verification trick (PNG tEXt / MP3 ID3 TXXX), and the fallback ladder (B001 → RunningHub/APIMart → keyframe method → H3 multi-ref → face-fix).
  - `references/step-contract.md` Step 4 now carries the tested commands: `tokentech_task.py music/image`, `tokentech_video.py` with R2V dual reference images as the DEFAULT (character shots must not be pure text-to-video), plus frame-grab consistency self-check.
  - Billing wording: always write actual billed amounts (usage delta) into cost/spent; quote/fx is budget-only.

## 0.4.7 — 2026-11-14

- Muse R2V reference-image channel verified on `/v1/videos`: `image` (single URL) and `image_urls` (array) are honored as reference images. Tested recipe — character turnaround sheet + storefront image → the same person across shots and correct brand signage in generated video. Documented in `references/providers/router.md`, `config/models.json` (muse router verified) and `scripts/providers/tokentech_video.py`.

## 0.4.6 — 2026-11-14

- Fixed `mvwb timeline` contract mismatch found during the v0.4.5 end-to-end test:
  - Input now accepts `lyric.json` (`{"lines":[{"line_id","text"}…]}`) as documented; plain-text lyrics still work.
  - `--out` ending with `.json` now writes real JSON (`{"mv_id","duration","lines":[{"line_id","start","end"}]}`, matching the demo schema) instead of a markdown table written into a `.json` filename.

## 0.4.5 — 2026-11-14

- Reference-script + picture-script system (from a second workbench iteration):
  - "脚本" renamed "参考脚本" (client's original text, shown as-is, for adaptation only); each MV gains a picture script block (`detail.script.body` / `00_script.md`, adapted from the reference script; storyboards are broken down from it). The three big sections became four: 脚本 → 音乐 → 资产图 → 分镜表.
  - Adaptation rules added to Step 3 hard rules: keep the skeleton (characters/scenes/plot/style), lyrics never change, every shot must match the lyric line it covers.
  - Workbench UI round two: storyboard table drops the "对应句" column (7 columns); fixed the music cost bubble reusing the badge pill style (dead `.mv-cost` removed, cost column 1fr full text); sidebar 原文 area base CSS added.
  - Demo updated to the new structure with three original picture scripts and `00_script.md` files.

## 0.4.4 — 2026-11-14

- Router task protocol verified end-to-end (`moss-t2i-rh-ck` image, `ace-step-1.5-rh-ck` music):
  - `POST /v1/responses` with `background:true`; params travel ONLY via `metadata.nodeInfoList` (straight pass-through to the RunningHub workflow nodes). With `nodeInfoList` present, `input` is not mapped to lyrics.
  - moss nodes: 4 prompt / 5 negative / 16 seed. ace nodes: 114 style / 115 lyrics / 116 duration-seconds / 117 BPM / 94 language/keyscale/timesignature (defaults zh, C major, 4; not individually probed).
  - Duration is controllable: 116.value=60 produced a 60.0s track (default is 180).
  - Verification method: outputs embed the executed workflow snapshot (PNG tEXt / MP3 ID3 TXXX "prompt").
  - Billing is charged by actual RunningHub runtime; per-run amounts vary (moss ¥0.31–0.37, ace ¥0.31–0.46 observed). Display actual billed amounts; `fx.rh_coin` stays as the quote fallback.
- New adapter `scripts/providers/tokentech_task.py` (image/music subcommands) with the unified alert wiring (K001/P1–P6, platform=router).
- `config/models.json`: moss/ace router slots marked verified 2026-11-14 with the protocol note; `references/providers/router.md` documents the task protocol.

## 0.4.3 — 2026-11-14

- Workbench UI cleanup per review:
  - Removed the in-page Key configuration feature entirely (button, modal, download flow); keys come from `zz-keys.json` / `start/setup-keys` / `mvwb keys set`.
  - Top bar now shows only the configured key's balance — no masked key value, no config button.
  - Removed the "累计" cost badge in the MV header (duplicate of the sidebar total).
  - "音乐未生成" empty state now uses the same wrapper as "资产未生成" (aligned padding).
  - Removed every "只读" label from the page (title, sidebar, meta rows, badges, CSS).
  - Top-bar order: 生成时间 first, balance chip far right.

## 0.4.2 — 2026-11-14

- Reorganized the package for humans: all entry points (installers, `mvwb` wrappers, one-click key setup) moved into `start/`; developer files into `dev/` (CONTRIBUTING, pyproject, requirements-dev, check_secrets); CHANGELOG/SECURITY into `docs/`.
- Root now only holds `SKILL.md`, `README.md`, `LICENSE`, `NOTICE.md` plus categorized folders; README gained a directory map explaining what each folder is for.
- Key example renamed to `config/zz-keys.example.json` (matches the distributed `zz-keys.json` naming).
- No behavior changes; installers/doctor/tests updated for the new paths.

## 0.4.1 — 2026-11-14

- Added a unified alert format (`scripts/alerts.py`) with a full code table (`references/alerts.md`): K/B/P/W/T/Q series.
- Wired alerts into `mvwb keys` (missing key, bad import file, watch timeout, non-interactive), `mvwb rh` / `mvwb muse` (auth/quota/submit/task-failed/timeout/download), `mvwb check` / `build` (missing refs, invalid DATA).
- Backup-key flow is now alert-driven: router repeated failures emit **B001**; the student forwards the alert text to the teacher, who decides whether to issue a backup `zz-keys.json`. No more "go ask the teacher for keys" wording.
- Manual gained a "把提醒原文发给老师" section; raw errors are truncated to 300 chars and redacted.

## 0.4.0 — 2026-11-14

- Router is the primary platform: students start with a Router-only `zz-keys.json`; backup RunningHub/APIMart keys are issued only when the relay keeps failing.
- Workbench top bar now shows only the Router balance; all costs are displayed in CNY. RunningHub coin→CNY rate is configurable in `config/models.json` (`fx.rh_coin`); `mvwb quote` prints the CNY conversion.
- Key layer supports a third provider: `apimart` section in `keys.json`, `keys set/config/import/balance/status` and `exec --need apimart`.
- Backup-key reminder rule: router failures ≥3 times in 10 minutes without a backup configured → ask the teacher for a backup `zz-keys.json`; importing it enables the fallback platforms.

## 0.3.9 — 2026-11-14

- Renamed the teacher-issued key file to `zz-keys.json` (from `keys.incoming.json`).
- `mvwb keys watch` now recognizes both `mv-keys-import*.json` and a minimal `zz-keys.json` in the watched download folders.
- Updated README, SKILL, reference, example and manual.

## 0.3.8 — 2026-11-14

- Simplified the teacher-issued key JSON to two fields: `{"runninghub": "...", "router": "..."}`.
- `issued_to` / `expires_at` / `mv_keys_import` are now optional; only needed for accounting or watcher auto-pickup.
- Updated example, reference, README, SKILL and manual.

## 0.3.7 — 2026-11-14

- Added the teacher-issued key workflow: put `keys.incoming.json` in the project root; agent imports and deletes it with `mvwb keys import --file ... --delete-source`.
- Added `config/keys.distribute.example.json` and `references/key-distribution.md` (standard JSON, per-student keys, expiry/metadata, why project-root beats chat attachments).
- Added `keys.incoming.json` / `mv-keys-import*.json` to `.gitignore`.
- Manual now leads with the teacher-issued file; the in-workbench panel is the self-service alternative.

## 0.3.6 — 2026-11-14

- Added `mvwb keys watch`: a short-lived watcher for `~/Downloads` / `~/Desktop` / `~/下载`.
- Agent can start it before the user configures keys; when the workbench downloads `mv-keys-import.json`, the watcher imports it, deletes the file, and (with `--data`) refreshes balances and rebuilds the workbench.
- Avoids a second chat message after the user downloads the key file; no HTTP service, no port.

## 0.3.5 — 2026-11-14

- Added a local Key panel in the static workbench: fill RunningHub/Router keys, download `mv-keys-import.json`; no service, no network, keys are not written into the HTML.
- Added `mvwb keys import --file <json> [--delete-source]`; validates, masks, writes `keys.json` 0600, optionally deletes the download.
- The agent flow is now: user configures in the workbench → downloads the file → agent imports and deletes it → balance/build.
- Hard rules/docs updated; downloaded import file is treated as sensitive and must be deleted after import.

## 0.3.4 — 2026-11-14

- Added one-click key setup: `setup-keys.command` (macOS) / `setup-keys.cmd` (Windows); prompts twice, input hidden, writes `~/.config/mv-workbench/keys.json`.
- `mvwb keys set` now refuses cleanly when there is no interactive terminal instead of raising a getpass/termios traceback; agents must not type keys for the user.
- Workbench video thumbnails now show the first frame (`#t=0.1`) instead of a black box.
- `mvwb keys init` next-step hint now uses `balance --data <data.json>` + `build` (no old `--write` HTML hint).

## 0.3.3 — 2026-11-13

- Added `references/variation.md`: genome dimensions, deterministic assignment, collision rules and dedup gates for cast/story/music/visual/edit.
- Added `references/prompts/casting-style.md`: casting cards, MOSS three-view template, style packs (小红书穿搭/日系甜妹/韩系欧巴/清爽帅哥/清冷知性/治愈系电影), video subject blocks and negative prompts.
- Step 3 now requires a `genome` and a differentiation table; duplicate combinations stop the batch.
- Asset QA now follows the MOSS rule: left face close-up, middle full-body with head fully out of frame, right back.
- Feishu manual gained a "怎么让每条不一样、角色好看" section with dialogue examples.

## 0.3.2 — 2026-11-13

- Aligned the skill logic with the human-facing manual:
  - Key is entered by the user in a local terminal; the agent only guides and never asks for or types the key.
  - Project name is part of the initial questions.
  - Added the three explicit gates: original → workbench → MV framework.
  - Documented music lock (no song swap after lock) and the >1s/2% duration pause.
  - Documented asset QA (`pass / warn / fail`) and the large-change impact/quote rule.
  - Added `data.json` to the final project tree.
- Updated the Feishu manual to the same logic.

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
