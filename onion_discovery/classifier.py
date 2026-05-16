# =============================================================================
# Onion Discovery — Classifier
# =============================================================================
# Klassifiziert Onion-Seiten nach Thema, Risikoniveau und Indexierbarkeit.
# Keywords helfen bei der automatischen Kategorisierung.
# Ergebnisse fließen in die Human Review Queue.
#
# Nutzung:
#   classifier = Classifier()
#   result = classifier.classify(title="...", content="...")
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# Risikostufen
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

RISK_LEVELS = [RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL]


@dataclass
class ClassificationResult:
    """Ergebnis der Klassifikation einer Onion-Seite."""

    topic: str = "unknown"
    risk_level: str = RISK_MEDIUM
    indexable: bool = True  # Soll die Seite indexiert werden?
    requires_human_review: bool = True  # Standard: Human Review nötig
    confidence: float = 0.5  # 0.0 - 1.0
    keywords_found: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class Classifier:
    """Klassifiziert Onion-Seiten nach Thema, Risiko und Indexierbarkeit."""

    # Keywords → Themen
    TOPIC_KEYWORDS: dict[str, list[str]] = {
        "technology": [
            "software",
            "linux",
            "programming",
            "coding",
            "security",
            "encryption",
            "vpn",
            "tor",
            "privacy",
            "github",
            "git",
            "python",
            "javascript",
            "docker",
            "server",
            "network",
        ],
        "forum": [
            "forum",
            "thread",
            "post",
            "discussion",
            "board",
            "topic",
            "reply",
            "comment",
            "member",
            "register",
        ],
        "marketplace": [
            "buy",
            "sell",
            "price",
            "shop",
            "store",
            "product",
            "order",
            "payment",
            "bitcoin",
            "monero",
            "escrow",
            "shipping",
            "vendor",
            "listing",
        ],
        "whistleblow": [
            "leak",
            "whistleblow",
            "expose",
            "document",
            "evidence",
            "anonymous",
            "secure drop",
            "submission",
        ],
        "wiki": [
            "wiki",
            "encyclopedia",
            "knowledge",
            "documentation",
            "manual",
            "guide",
            "howto",
            "tutorial",
        ],
        "blog": [
            "blog",
            "article",
            "post",
            "opinion",
            "editorial",
            "newsletter",
            "update",
        ],
        "search": [
            "search",
            "index",
            "catalog",
            "directory",
            "engine",
            "find",
            "discover",
        ],
    }

    # Keywords → erhöhtes Risiko
    HIGH_RISK_KEYWORDS = [
        "child",
        "exploit",
        "weapon",
        "drug",
        "counterfeit",
        "hacked",
        "stolen",
        "credit card",
        "fraud",
        "malware",
        "ransomware",
        "bomb",
        "terrorism",
        "human trafficking",
        "hitman",
        "assassination",
        "cp",
        "child pornography",
    ]

    def classify(
        self,
        url: str = "",
        title: str = "",
        content: str = "",
        headers: Optional[dict] = None,
    ) -> ClassificationResult:
        """Klassifiziert eine Onion-Seite.

        Args:
            url: URL der Seite.
            title: Seitentitel.
            content: Text-Inhalt (bereinigt).
            headers: HTTP-Header (optional).

        Returns:
            ClassificationResult mit Bewertung.
        """
        text = f"{title} {content}".lower()
        result = ClassificationResult()

        # Thema erkennen
        topic_scores = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                topic_scores[topic] = score

        if topic_scores:
            best_topic = max(topic_scores, key=topic_scores.get)
            result.topic = best_topic
            result.keywords_found = [
                kw for kw in self.TOPIC_KEYWORDS.get(best_topic, []) if kw in text
            ]
            result.confidence = min(
                0.9,
                0.3 + (topic_scores[best_topic] * 0.15),
            )
        else:
            result.topic = "unknown"
            result.confidence = 0.2

        # Risikostufe
        high_risk_matches = sum(1 for kw in self.HIGH_RISK_KEYWORDS if kw in text)
        if high_risk_matches >= 3:
            result.risk_level = RISK_CRITICAL
            result.reasons.append(f"Multiple High-Risk-Keywords: {high_risk_matches}")
        elif high_risk_matches >= 1:
            result.risk_level = RISK_HIGH
            result.reasons.append(f"High-Risk-Keyword gefunden")

        # Marketplace immer kritisch
        if result.topic == "marketplace":
            result.risk_level = max(
                result.risk_level, RISK_HIGH, key=lambda x: RISK_LEVELS.index(x)
            )
            result.reasons.append("Marketplace erkannt")

        # Human Review Entscheidung
        if result.risk_level in (RISK_HIGH, RISK_CRITICAL):
            result.requires_human_review = True
            result.indexable = False  # Nur nach Freigabe
        elif result.topic == "unknown":
            result.requires_human_review = True
            result.indexable = False
        else:
            result.requires_human_review = False
            result.indexable = True

        logger.debug(
            f"Klassifikation: {url[:60]} -> "
            f"{result.topic} (Risiko: {result.risk_level}, "
            f"Indexierbar: {result.indexable})"
        )
        return result
