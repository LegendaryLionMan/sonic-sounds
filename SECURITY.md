# Security Policy

## Reporting a Vulnerability

If you discover a security issue in Sonic Studio, please email **the maintainer directly** rather than filing a public GitHub issue. Use the contact info in `git log` for the latest committer.

We aim to acknowledge security reports within 48 hours and provide a remediation plan within 7 days.

## Threat model

Sonic Studio is a **local-first, single-user desktop application**. The threat model is correspondingly narrow:

| In scope | Out of scope |
|---|---|
| Local SQLite database corruption (handled by WAL mode + sweepers) | Cloud account compromise (we don't use cloud) |
| Daemon binding to `127.0.0.1` (not `0.0.0.0`) | Multi-user authentication (only one user per install) |
| Path traversal in the static-file handler (Quart's `safe_join`) | CSRF / session hijacking (no cookies, no auth) |
| API key leakage via git history | Production deployment hardening (no production deploys) |

## Secret-handling rules

1. **Never commit secrets.** API keys, tokens, passwords, private keys — none of these should ever appear in this repository, in commits, or in PRs.
2. **Use environment variables.** If a feature requires a secret (e.g. an LLM API key), read it from an env var at runtime. Document the env var name in the README but do NOT include any value.
3. **Sensitive defaults are explicit.** When a default value is sensitive, require the user to set it explicitly. Never silently fall back to a hardcoded credential.
4. **The `.gitignore` excludes** `.env`, `.env.local`, `*.key`, `*.pem`. Do not commit files matching these patterns even if you think they're harmless.

## Verification

The repo has been audited for the following patterns on **2026-09-04** (commit `16f3218`):

```bash
git grep -nIE 'sk-[A-Za-z0-9_-]{20,}|gho_[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_-]{20,}|github_pat_[A-Za-z0-9_-]{20,}|sk-or-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|AIzaSy[A-Za-z0-9_-]{20,}|xai-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|ASIA[A-Z0-9]{16}|-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----'
```

Result: **zero matches**.

```bash
git grep -nIE 'sqlite:///(?!/dev/null)[^"\x27 ]+|postgres://[^"\x27 ]+:[^@]+@|mongodb://[^"\x27 ]+:[^@]+@|redis://[^"\x27 ]+:[^@]+@'
```

Result: **zero matches**.

To re-run this audit at any time:

```bash
./tools/security-audit.sh    # (TODO: add this script)
# or use the inline commands above
```

## Dependency vulnerabilities

We don't yet have a scheduled Dependabot run. To check manually:

```bash
python -m pip install pip-audit
pip-audit -r requirements.txt
```

If you find a vulnerability, follow the reporting process above.

## Database encryption

The SQLite database at `.meta/sonic-studio.db` is **not encrypted at rest**. This is intentional: the project is single-user, local-only, and the user owns the filesystem. If you need encryption, mount the `.meta/` directory on an encrypted volume (BitLocker, FileVault, LUKS, etc.).

## Updates

This policy was last updated on **2026-09-04** as part of the rename from `album-studio` → `Sonic Studio`. See [CHANGELOG.md](./CHANGELOG.md) for the release history.
