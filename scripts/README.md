# Scripts

Optional dev helpers that call Graph directly (bypass MCP search and write confirmation).

## In this repo (`scripts/`)

Generic scripts — work with any tenant configured in `.env`:

| Script | Purpose |
|---|---|
| `count_users.py` | Entra user count |
| `count_cloud_pcs.py` | Cloud PC count |
| `list_cloud_pcs.py` | List all Cloud PCs |
| `cloudpc_specs.py` | Cloud PC SKU details |

Run from repo root:

```bash
python scripts/count_users.py
```

## Personal / tenant-specific (`scripts/local/`)

**Not committed to git.** Use this folder for scripts tied to your tenant (named Cloud PCs, groups, policies).

Examples moved here during setup:

- `cloudpc_snapshots.py` — restore points for a named Cloud PC
- `reboot_cloudpc.py` — reboot a named Cloud PC
- `list_group_members.py` — members of a named group
- `provisioning_policy.py` / `provisioning_policy_detail.py` / `provisioning_policy_groups.py` — policy lookup

Run from repo root:

```bash
python scripts/local/cloudpc_snapshots.py
```

For day-to-day use, prefer **GraphMind MCP** (`search_graph_api` → `call_graph_api`) in Cursor.
