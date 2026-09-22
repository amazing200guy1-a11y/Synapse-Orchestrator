# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Yes    |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email: security@mehd.ai with subject line `[SECURITY] Synapse-Orchestrator`.

Expected response: within 48 hours.

## Threat Model

- **API Key Leakage**: Keys must be supplied via environment variables only. Never commit real keys.
- **Prompt Injection**: All model responses are validated against a strict Pydantic schema before arithmetic — free-form prose is rejected at the parse boundary.
- **Supply Chain**: Dependencies are pinned to exact versions in `requirements.txt`.