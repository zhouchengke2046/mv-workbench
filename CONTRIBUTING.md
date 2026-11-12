# Contributing

1. Never commit client lyrics/scripts/assets, API keys, phone numbers, or absolute personal paths.
2. Run `python3 scripts/check_secrets.py` before committing.
3. Add tests for new providers/parsers; do not call paid APIs in CI.
4. Update `config/models.json` with an `as_of` date when changing prices/workflows.
5. Keep the workbench static template data-free; use `scripts/build_workbench.py` with a `DATA.json`.
6. For new prompt skills, keep model-specific rules separate; do not reuse H3 prompts for Muse/ACE.
