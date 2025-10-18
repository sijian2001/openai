# Repository Guidelines

## Project Structure & Module Organization
- Place production code under `src/`, keeping the HTTP fetcher, parser, and summarizer modules isolated (for example `src/fetcher.py`, `src/parser/`, `src/summarizer/`).
- Expose the main entry point via `src/cli.py` with a callable `main()` that accepts the earnings-report URL parameter.
- Keep automated checks in `tests/` using mirrored subpackages (e.g., `tests/test_fetcher.py`) and store small sample filings in `tests/fixtures/`.
- Add persistent reference material to `docs/`, and use `.cache/` (gitignored) for transient downloads to avoid committing large files.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create and activate the local virtual environment defined in the README.
- `pip install -r requirements.txt` — install runtime and tooling dependencies before running any scripts.
- `python -m src.cli <filing_url>` — execute the summarizer end-to-end against a live earnings report.
- `pytest` — run the unit and integration suites; add `-k` to target a single module when iterating.
- `ruff check src tests` and `black src tests` — lint and format code prior to opening a pull request.

## Coding Style & Naming Conventions
- Follow Python 4-space indentation and keep modules under 300 logical lines; split reusable helpers into packages.
- Use snake_case for functions and variables, PascalCase for classes, and prefix private callables with `_`.
- Document public functions with concise docstrings that note expected URL schemas and output structure.
- All network access should be wrapped in functions that accept an optional `session` argument to simplify testing.

## Testing Guidelines
- Prefer `pytest` with descriptive test names (`test_parser_handles_blank_table`) and mirrors of the `src/` tree.
- Include at least one integration test that exercises fetching, parsing, and summarizing against a stored fixture.
- Maintain ≥90% coverage on new modules; run `pytest --cov=src --cov-report=term-missing` before submission.
- Guard edge cases such as HTTP timeouts, unexpected table layouts, and non-UTF8 filings with targeted unit tests.

## Commit & Pull Request Guidelines
- Write commits in the imperative mood with the scope first (`parser: handle unbalanced rows`) and keep them focused.
- Reference related GitHub issues in the commit footer (`Refs #42`) and link them in the pull request description.
- PRs should summarize implementation choices, list test commands run, and add screenshots or console excerpts when behavior changes.
- Request review only after lint, format, and full test suites pass locally; include follow-up tasks as TODO items in the PR body if needed.
