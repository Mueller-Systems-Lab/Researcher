# =============================================================================
# Onion Discovery — Policy Gateway
# =============================================================================
# Zentrale Prüfinstanz für Sicherheits- und Compliance-Regeln.
# Prüft vor Fetch, vor Speicherung und vor Ausgabe:
#   - Blocklist (Hosts, URLs, Patterns)
#   - Allowlist (nur erlaubte Seeds/Quellen)
#   - Opt-out (Hosts, die nicht gecrawlt werden wollen)
#   - Rate-Limits (per Host und global)
#   - Content-Type-Filter
#
# Nutzung:
#   gateway = PolicyGateway()
#   if gateway.is_allowed("http://darkforum.onion"):
#       crawler.crawl()
# =============================================================================

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """Ergebnis einer Policy-Prüfung."""

    allowed: bool
    reason: str = ""
    block_type: str = ""  # blocklist, rate_limit, content_type, not_in_allowlist


class PolicyGateway:
    """Zentrale Policy-Prüfung für Onion Discovery."""

    def __init__(
        self,
        allowlist: list[str] | None = None,
        blocklist: list[str] | None = None,
        opt_out: list[str] | None = None,
        max_requests_per_host: int = 2,
        global_delay: float = 10.0,
    ):
        self.allowlist = set(allowlist or [])
        self.blocklist = set(blocklist or [])
        self.opt_out = set(opt_out or [])
        self.max_requests_per_host = max_requests_per_host
        self.global_delay = global_delay

        # Rate-Limiting-Tracking
        self._host_requests: dict[str, list[float]] = defaultdict(list)
        self._last_global_request: float = 0.0

    def _extract_host(self, url: str) -> str:
        """Extrahiert den Host aus einer URL."""
        match = re.match(r"(?:https?://)?([^:/]+)", url.lower())
        return match.group(1) if match else url.lower()

    def is_allowed(self, url: str) -> PolicyDecision:
        """Prüft, ob eine URL gecrawlt werden darf.

        Reihenfolge: Blocklist → Allowlist → Opt-out → Rate-Limit
        Blocklist hat Vorrang vor Allowlist (Deny-overrides-allow).
        """
        host = self._extract_host(url)
        url_lower = url.lower()

        # Blocklist-Prüfung (hat VORRANG vor Allowlist — Deny-overrides-allow)
        if host in self.blocklist:
            return PolicyDecision(False, f"Host {host} ist blocklistiert", "blocklist")
        for pattern in self.blocklist:
            if re.search(pattern, url_lower):
                return PolicyDecision(
                    False, f"URL {url} matcht Blocklist-Pattern {pattern}", "blocklist"
                )

        # Allowlist-Prüfung (wenn gesetzt, nur erlaubte Hosts)
        if self.allowlist:
            if host not in self.allowlist:
                return PolicyDecision(
                    False, f"Host {host} nicht in Allowlist", "not_in_allowlist"
                )

        # Opt-out-Prüfung
        if host in self.opt_out:
            return PolicyDecision(False, f"Host {host} hat Opt-out", "blocklist")

        # Rate-Limiting (global)
        now = time.time()
        if now - self._last_global_request < self.global_delay:
            return PolicyDecision(
                False,
                f"Globales Rate-Limit ({self.global_delay}s)",
                "rate_limit",
            )

        # Rate-Limiting (per Host)
        host_times = [t for t in self._host_requests[host] if now - t < 60]
        if len(host_times) >= self.max_requests_per_host:
            return PolicyDecision(
                False,
                f"Host-Rate-Limit für {host} erreicht "
                f"({self.max_requests_per_host}/min)",
                "rate_limit",
            )
        self._host_requests[host].append(now)
        self._last_global_request = now

        return PolicyDecision(True, "Allowed")

    def add_to_blocklist(self, host_or_pattern: str):
        """Fügt einen Host oder Pattern zur Blocklist hinzu."""
        self.blocklist.add(host_or_pattern)
        logger.warning(f"Zur Blocklist hinzugefügt: {host_or_pattern}")

    def add_to_opt_out(self, host: str):
        """Fügt einen Host zur Opt-out-Liste hinzu."""
        self.opt_out.add(host.lower())
        logger.info(f"Opt-out für Host: {host}")

    def is_onion_url(self, url: str) -> bool:
        """Prüft, ob eine URL eine .onion-Adresse ist."""
        return ".onion" in url.lower()

    @property
    def stats(self) -> dict:
        """Liefert aktuelle Policy-Statistiken."""
        return {
            "allowlist_size": len(self.allowlist),
            "blocklist_size": len(self.blocklist),
            "opt_out_size": len(self.opt_out),
            "active_hosts": len(self._host_requests),
        }
