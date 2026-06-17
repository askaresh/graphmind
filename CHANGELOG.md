# Changelog

All notable changes to GraphMind are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- VS Code (GitHub Copilot) MCP configuration (`.vscode/mcp.json`) and setup docs.
- OSS hygiene: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR
  templates, and README badges.
- README prerequisites, cross-platform env setup, and first-run / time-to-first-query
  expectations.

### Changed
- Default `AUTH_MODE` in `.cursor/mcp.json` switched to `interactive` to match the
  recommended dev onboarding path.

## [0.1.0] - 2026-06-17

### Added
- API-aware MCP server for Microsoft Graph with a 3-tier search funnel
  (structural filter → cross-encoder rerank → schema injection).
- MCP tools: `search_graph_api`, `get_endpoint_schema`, `get_changelog`,
  `call_graph_api`.
- Domain hints (e.g. Cloud PC / snapshot queries auto-select `api_version=beta`).
- Write confirmation gate for POST/PATCH/PUT/DELETE and `GRAPHMIND_READ_ONLY` mode.
- Pagination with aggregate count + sample for large GET collections.
- Permission-aware filtering from the granted-scopes JWT claims.
- CLI: `serve`, `bootstrap`, `refresh`, `scheduler`, `stats`, `search`.
- Auth modes: interactive, client secret, and certificate (MSAL).
- GitHub Actions for tests and daily spec refresh + diff.
- Cursor MCP config and agent rules (`.cursor/`).

[Unreleased]: https://github.com/askaresh/graphmind/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/askaresh/graphmind/releases/tag/v0.1.0
