# Security policy

## Scope

Reports cover current repository code (0.1.0 and ongoing development): secret exposure, unsafe output paths, subprocess invocation, update integrity, archive extraction, packaging and dependency integration. Older versions have no separate maintenance promise. Binaries are not currently distributed. Ordinary platform/extractor failures belong in bug reports.

## Reporting

Use GitHub's private [Report a vulnerability](https://github.com/mr-ransaz/MediaGrab/security/advisories/new) route if available; repository configuration controls its availability. If unavailable, open an issue requesting a private maintainer contact without publishing exploit details or secrets. Wait for a private route before sending sensitive evidence. No dedicated security email or response-time guarantee is advertised.

Provide affected version/commit, environment, impact, a minimal reproduction using synthetic data and remediation details if known. Remove cookies, tokens, headers, signed URLs and private paths. Do not test against other people's accounts/systems. Coordinate disclosure privately until a fix is ready.

## Boundaries

MediaGrab runs with local user permissions and invokes trusted installed tools. HTTP/HTTPS validation permits private hosts; it is not server request isolation. Output checks do not guarantee protection against hostile local filesystem races. Cookie opt-in gives the engine browser-session access. Self-check reports contain paths; review shared diagnostics after redaction.

See [Architecture](docs/ARCHITECTURE.md) and [Third-party notices](THIRD_PARTY_NOTICES.md). Report upstream defects through upstream reporting channels without posting secrets here.
