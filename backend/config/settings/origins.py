"""Build CSRF / CORS origins from Django hosts.

o2switch often serves both http://*.odns.fr (before AutoSSL) and https://.
An empty CSRF_TRUSTED_ORIGINS plus a misleading X-Forwarded-Proto: https
makes every POST (setup, login, forms) return 403 CSRF.
"""

from __future__ import annotations


def trusted_origins_from_hosts(hosts, extra=()):
    """Return http+https origins for each host, plus any explicit extra URLs."""
    origins: list[str] = []
    for raw in list(hosts) + list(extra):
        host = str(raw or "").strip().rstrip("/")
        if not host or host == "*":
            continue
        if "://" in host:
            origins.append(host)
            continue
        origins.append(f"https://{host}")
        origins.append(f"http://{host}")

    seen: set[str] = set()
    unique: list[str] = []
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            unique.append(origin)
    return unique
