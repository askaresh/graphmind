# GraphMind — agent instructions

API-aware MCP server for Microsoft Graph. For **Entra ID, users, groups, Cloud PCs,
Intune, or any M365 tenant data**, use the GraphMind MCP tools automatically — do not
guess API paths from training data.

## MCP workflow (required)

1. **`search_graph_api`** — natural language query first
2. **`get_endpoint_schema`** — if parameters are unclear
3. **`call_graph_api`** — execute the chosen endpoint

Never call Graph without searching the local index first.

## Write operations

POST, PATCH, PUT, and DELETE (reboot, delete, assign, etc.) require confirmation:

1. Call `call_graph_api` **without** `confirmed` → returns a preview
2. Show the preview to the user and ask for approval
3. Re-call with **`confirmed: true`** only if they approve

`GRAPHMIND_READ_ONLY=true` blocks all writes regardless.

## Reads at scale

- Counts: `GET /users/$count` (single request)
- Large lists: `paginate=true`, `aggregate=true` on `call_graph_api`
- Use `$select`, `$filter`, `$top` in `query_params`

## Cloud PC / Windows 365

- Many APIs are **beta-only** — GraphMind auto-selects `api_version=beta` for Cloud PC / snapshot queries
- **Restore points:** `GET .../cloudPCs/{id}/retrieveSnapshots()` — not the tenant `/snapshots` collection
- OData functions use a `()` suffix in the URL

## Defaults

- `api_version`: `v1.0` unless beta is needed (Cloud PC / snapshots auto-upgrade)
- `filter_by_permissions`: `true`
- Auth via `.env` (app-only or interactive)

## Full rule set

See [`.cursor/rules/graphmind-mcp.mdc`](.cursor/rules/graphmind-mcp.mdc) for examples and edge cases.

## If MCP tools are unavailable

Say so explicitly. Do not fabricate Graph API responses or endpoint paths.
