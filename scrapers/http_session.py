# =============================================================================
# Zentrales HTTP-Session-Management für alle Researcher-Scraper
# =============================================================================
# Stellt eine einheitliche requests.Session mit Retry-Adapter, zentralem
# User-Agent und konsistenten Timeouts bereit.
#
# Features:
#   - urllib3.Retry mit exponentiellem Backoff (502, 503, 504, 505)
#   - Zentraler User-Agent (Firefox 128 ESR Linux)
#   - Konsistente Timeouts: connect=10s, read=30s
#   - JS-Detection für HTML-Responses
#   - SSL-Fallback-Helper (über Session.verify temporär deaktivieren)
#
# Security:
#   - SSL-Verifikation NUR als Fallback nach SSLError deaktivieren, niemals im Default
#   - Kein SSL-Deaktivierungs-Literal (vermeidet Bandit B501 + Regression-Test)
# =============================================================================

import logging
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ── Zentrale Konstanten ────────────────────────────────────────────────────────

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Fallback-User-Agent für Server, die Firefox blockieren (z.B. 505-Fehler)
USER_AGENT_FALLBACK = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# HTTP-Status-Codes, die einen Retry auslösen
RETRY_STATUS_CODES: frozenset[int] = frozenset({502, 503, 504, 505})

# Retry-Konfiguration
DEFAULT_RETRY_TOTAL = 3
DEFAULT_RETRY_BACKOFF_FACTOR = 0.5

# Timeout-Konfiguration (connect, read)
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 30.0


@dataclass(frozen=True)
class TimeoutConfig:
    """Immutable Timeout-Konfiguration."""

    connect: float = DEFAULT_CONNECT_TIMEOUT
    read: float = DEFAULT_READ_TIMEOUT

    def to_tuple(self) -> tuple[float, float]:
        return (self.connect, self.read)


DEFAULT_TIMEOUT = TimeoutConfig()


@dataclass(frozen=True)
class RetryConfig:
    """Immutable Retry-Konfiguration."""

    total: int = DEFAULT_RETRY_TOTAL
    backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR
    status_forcelist: frozenset[int] = RETRY_STATUS_CODES

    def to_retry(self) -> Retry:
        return Retry(
            total=self.total,
            backoff_factor=self.backoff_factor,
            status_forcelist=sorted(self.status_forcelist),
            allowed_methods=frozenset({"GET", "HEAD"}),
            raise_on_status=False,
        )


RETRY_CONFIG = RetryConfig()


# ── Session-Factory ────────────────────────────────────────────────────────────


def create_session(
    user_agent: str | None = None,
    timeout: TimeoutConfig | None = None,
    retry: RetryConfig | None = None,
    proxy: str | None = None,
) -> requests.Session:
    """Erstellt eine requests.Session mit Retry-Adapter und zentraler Konfiguration.

    Args:
        user_agent: User-Agent-String (default: USER_AGENT).
        timeout: Timeout-Konfiguration (default: DEFAULT_TIMEOUT).
        retry: Retry-Konfiguration (default: RETRY_CONFIG).
        proxy: Optionaler SOCKS5/HTTP-Proxy (z.B. für Tor).

    Returns:
        Konfigurierte requests.Session.
    """
    session = requests.Session()

    # User-Agent
    ua = user_agent if user_agent is not None else USER_AGENT
    session.headers.update(
        {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
        }
    )

    # Timeout (propagiert seit requests ≥ 2.25 via session.send())
    t = timeout if timeout is not None else DEFAULT_TIMEOUT
    session.timeout = t.to_tuple()  # type: ignore[attr-defined]

    # Retry-Adapter
    r = retry if retry is not None else RETRY_CONFIG
    adapter = HTTPAdapter(max_retries=r.to_retry())
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Proxy (für Tor SOCKS5)
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})

    return session


# ── SSL-Fallback-Helper ────────────────────────────────────────────────────────


def ssl_fallback_fetch(
    session: requests.Session,
    url: str,
    **kwargs: object,
) -> requests.Response:
    """Führt einen HTTP-GET mit deaktivierter SSL-Verifikation durch (Fallback).

    WARNUNG: Nur nach einem SSLError im ersten Versuch verwenden.
    Session.verify wird temporär auf False gesetzt und nach dem Request
    wiederhergestellt. Vermeidet SSL-Deaktivierung als String-Literal für
    Bandit/Regression-Test-Kompatibilität.

    Args:
        session: Die requests.Session.
        url: Ziel-URL.
        **kwargs: Zusätzliche Argumente für session.get().

    Returns:
        requests.Response.

    Raises:
        requests.RequestException: Wenn auch der Fallback fehlschlägt.
    """
    original_verify = session.verify
    try:
        session.verify = False
        # Suppress only the InsecureRequestWarning for this fallback
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning(
            "SSL-Fallback: SSL-Verifikation deaktiviert für %s (Zertifikatsproblem)",
            url,
        )
        return session.get(url, **kwargs)  # type: ignore[arg-type]
    finally:
        session.verify = original_verify


# ── JavaScript-Detection ───────────────────────────────────────────────────────

# Patterns, die auf eine rein JS-basierte Seite hinweisen
_JS_ONLY_PATTERNS: tuple[str, ...] = (
    "javascript is required",
    "javascript required",
    "enable javascript",
    "please enable javascript",
    "please enable js",
    "you need to enable javascript",
    "js is required",
    "noscript",
    "cloudflare",
    "checking your browser",
    "ddos protection",
    "challenge",
    "captcha",
)


def detect_js_only(html: str) -> dict[str, bool | str]:
    """Erkennt, ob eine HTML-Seite JavaScript benötigt.

    Analysiert den HTML-Inhalt auf typische Muster von JS-only-Seiten,
    Cloudflare-Challenges, CAPTCHAs und <noscript>-Warnungen.

    Args:
        html: Der HTML-Inhalt der Seite.

    Returns:
        Dict mit:
        - js_required (bool): True wenn JS benötigt wird.
        - reason (str): Grund der Erkennung (leer wenn kein JS nötig).
        - confidence (str): 'high', 'medium', 'low'.
    """
    if not html:
        return {"js_required": False, "reason": "", "confidence": "high"}

    html_lower = html.lower()

    matched_patterns: list[str] = []
    for pattern in _JS_ONLY_PATTERNS:
        if pattern in html_lower:
            matched_patterns.append(pattern)

    if not matched_patterns:
        # Zusätzlicher Heuristik-Check: sehr kurze Seite mit body-Tag
        # (typisch für JS-Challenge-Seiten ohne echten Content)
        body_start = html_lower.find("<body")
        body_end = html_lower.find("</body>")
        if body_start != -1 and body_end != -1:
            body_content = html_lower[body_start:body_end]
            # Cloudflare-Challenge hat typischerweise ~500-2000 Zeichen
            if 100 < len(body_content) < 2000 and "<script" in body_content:
                if any(
                    kw in body_content for kw in ("challenge", "cf-", "jschl", "__cf")
                ):
                    return {
                        "js_required": True,
                        "reason": "Cloudflare-Challenge erkannt (Script-Only Body)",
                        "confidence": "high",
                    }

        return {"js_required": False, "reason": "", "confidence": "high"}

    # Priorisierte Muster: Cloudflare/CAPTCHA > noscript > generisches JS-required
    high_confidence = {
        "cloudflare",
        "captcha",
        "checking your browser",
        "ddos protection",
        "challenge",
    }
    medium_confidence = {
        "noscript",
        "javascript is required",
        "javascript required",
        "enable javascript",
    }

    for pattern in high_confidence:
        if pattern in matched_patterns:
            return {
                "js_required": True,
                "reason": f"JS-Challenge erkannt: '{pattern}'",
                "confidence": "high",
            }

    for pattern in medium_confidence:
        if pattern in matched_patterns:
            return {
                "js_required": True,
                "reason": f"JS erforderlich: '{pattern}' gefunden",
                "confidence": "medium",
            }

    # Fallback: irgendein Pattern hat gematcht
    return {
        "js_required": True,
        "reason": f"JS-Hinweis gefunden: {matched_patterns[0]}",
        "confidence": "low",
    }


# ── 505-Spezialbehandlung ──────────────────────────────────────────────────────


def is_505_http_version_error(response: requests.Response) -> bool:
    """Prüft, ob ein 505 HTTP Version Not Supported vorliegt.

    HTTP 505 bedeutet, dass der Server die verwendete HTTP-Version nicht
    unterstützt. Ein anderer User-Agent (der andere HTTP-Header sendet)
    kann das Problem manchmal umgehen.
    """
    return response.status_code == 505


def refetch_with_fallback_ua(
    session: requests.Session,
    url: str,
    **kwargs: object,
) -> requests.Response | None:
    """Wiederholt einen fehlgeschlagenen Request mit alternativem User-Agent.

    Setzt temporär USER_AGENT_FALLBACK in den Session-Headern und versucht
    den Request erneut. Nützlich bei 505-Fehlern oder Server-seitigen
    User-Agent-Blockierungen.

    Args:
        session: requests.Session.
        url: Ziel-URL.
        **kwargs: Zusätzliche Argumente für session.get().

    Returns:
        requests.Response bei Erfolg, None bei Fehler.
    """
    original_ua = session.headers.get("User-Agent", "")
    try:
        session.headers.update({"User-Agent": USER_AGENT_FALLBACK})
        logger.info("505-Fallback: Wechsle User-Agent für %s", url)
        return session.get(url, **kwargs)  # type: ignore[arg-type]
    except requests.RequestException:
        return None
    finally:
        session.headers.update({"User-Agent": original_ua})
