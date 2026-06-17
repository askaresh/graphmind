# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in GraphMind, please report it privately
rather than opening a public issue.

- Use GitHub's [private vulnerability reporting](https://github.com/askaresh/graphmind/security/advisories/new)
  ("Report a vulnerability" under the repository's **Security** tab), or
- Contact the maintainer directly via the email on their GitHub profile.

Please include steps to reproduce, the affected version or commit, and any relevant
logs (with secrets redacted). We aim to acknowledge reports within a few business days.

## Supported versions

GraphMind is pre-1.0; security fixes are applied to the latest `main` and the most
recent release.

## Handling secrets

GraphMind authenticates to Microsoft Graph using credentials you supply. **Never commit
secrets.** The following are already excluded via `.gitignore` and must stay out of the
repository:

- `.env` and `.env.*.local` — tenant ID, client ID, client secret
- `.graphmind_token_cache.json` — the persisted MSAL token cache
- `*.pem` / `key.pem` — certificates and private keys
- `scripts/local/` — tenant-specific helper scripts

Recommendations:

- Prefer **interactive** auth for local development (no stored secret).
- For CI/servers, store `TENANT_ID`, `CLIENT_ID`, and `CLIENT_SECRET` as repository or
  environment secrets — never in source.
- Grant the **minimum** Graph permissions needed; start with the read-only starter set
  in [docs/entra_setup.md](docs/entra_setup.md).
- Use `GRAPHMIND_READ_ONLY=true` to block all write methods when only reads are needed.
- After rotating credentials or changing permissions, delete
  `.graphmind_token_cache.json` so a fresh token is acquired.
