# =============================================================================
# Onion Discovery — Human Review Queue
# =============================================================================
# Verwaltet die Warteschlange für manuelle Freigabe von Onion-Quellen.
# Gemäß ADR-006: dauerhafte Speicherung und Ausgabe nur nach Human Approval.
#
# Nutzung:
#   review = ReviewQueue()
#   review.add(crawl_result, classification)
#   item = review.get_next_pending()
#   review.approve(item_id)
#   review.reject(item_id, reason="...")
# =============================================================================

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    """Ein Element in der Review-Queue."""

    id: str
    url: str
    title: str = ""
    content_preview: str = ""  # Max 500 Zeichen
    topic: str = "unknown"
    risk_level: str = "medium"
    confidence: float = 0.0
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reviewed_at: str | None = None
    status: str = "pending"  # pending, approved, rejected
    reviewed_by: str = ""
    review_notes: str = ""
    source_seed: str = ""


class ReviewQueue:
    """Review-Queue für Onion-Discovery-Freigaben."""

    def __init__(self, queue_file: str | None = None):
        self.queue_file = queue_file or os.getenv(
            "ONION_REVIEW_FILE", "./onion_review_queue.json"
        )
        self._items: dict[str, ReviewItem] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file) as f:
                    data = json.load(f)
                for entry in data:
                    item = ReviewItem(**entry)
                    self._items[item.id] = item
                logger.info(f"{len(self._items)} Review-Items geladen")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Fehler beim Laden der Review-Queue: {e}")

    def _save(self):
        """Speichert die Queue atomar (tempfile + os.replace)."""
        try:
            os.makedirs(os.path.dirname(self.queue_file) or ".", exist_ok=True)
            content = json.dumps(
                [asdict(item) for item in self._items.values()],
                indent=2,
                ensure_ascii=False,
            )
            fd, tmp = tempfile.mkstemp(
                dir=os.path.dirname(self.queue_file) or ".",
                suffix=".tmp",
            )
            try:
                with open(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp, self.queue_file)
            except Exception:
                os.unlink(tmp)
                raise
        except (OSError, TypeError) as e:
            logger.error(f"Fehler beim Speichern der Review-Queue: {e}")

    def add(
        self,
        item_id: str,
        url: str,
        title: str = "",
        content: str = "",
        topic: str = "unknown",
        risk_level: str = "medium",
        confidence: float = 0.0,
        source_seed: str = "",
    ) -> bool:
        """Fügt ein neues Review-Item hinzu."""
        if item_id in self._items:
            return False

        self._items[item_id] = ReviewItem(
            id=item_id,
            url=url,
            title=title,
            content_preview=content[:500],
            topic=topic,
            risk_level=risk_level,
            confidence=confidence,
            source_seed=source_seed,
        )
        self._save()
        logger.info(f"Review-Item hinzugefügt: {url[:60]} (Risiko: {risk_level})")
        return True

    def get_next_pending(self) -> ReviewItem | None:
        """Holt das nächste zu reviewende Item (höchstes Risiko zuerst)."""
        from onion_discovery.classifier import RISK_LEVELS

        pending = [item for item in self._items.values() if item.status == "pending"]
        if not pending:
            return None
        # Nach Risiko sortieren (höchstes zuerst)
        pending.sort(
            key=lambda x: (
                RISK_LEVELS.index(x.risk_level) if x.risk_level in RISK_LEVELS else 2
            ),
            reverse=True,
        )
        return pending[0]

    def get_pending_items(self, limit: int = 10) -> list[ReviewItem]:
        """Holt die nächsten pending Review-Items (älteste zuerst).

        Args:
            limit: Maximale Anzahl zurückgegebener Items.

        Returns:
            Liste von ReviewItems, sortiert nach Entdeckungszeitpunkt.
        """
        pending = [item for item in self._items.values() if item.status == "pending"]
        pending.sort(key=lambda x: x.discovered_at)
        return pending[:limit]

    def approve(self, item_id: str, reviewer: str = "", notes: str = "") -> bool:
        """Genehmigt ein Item (erlaubt Indexierung).

        Args:
            item_id: ID des zu genehmigenden Items.
            reviewer: Name/Kennung des Reviewers. Wird aus Umgebungsvariable
                      REVIEWER_DEFAULT oder 'unknown' gesetzt, wenn leer.
            notes: Optionale Notizen zur Genehmigung.
        """
        if item_id not in self._items:
            return False
        if not reviewer:
            reviewer = os.getenv("REVIEWER_DEFAULT", "unknown")
        self._items[item_id].status = "approved"
        self._items[item_id].reviewed_at = datetime.now().isoformat()
        self._items[item_id].reviewed_by = reviewer
        self._items[item_id].review_notes = notes
        self._save()
        logger.info(f"Review-Item {item_id[:12]} genehmigt von {reviewer}")
        return True

    def reject(self, item_id: str, reviewer: str = "", reason: str = "") -> bool:
        """Lehnt ein Item ab (keine Indexierung).

        Args:
            item_id: ID des abzulehnenden Items.
            reviewer: Name/Kennung des Reviewers. Wird aus Umgebungsvariable
                      REVIEWER_DEFAULT oder 'unknown' gesetzt, wenn leer.
            reason: Grund für die Ablehnung.
        """
        if item_id not in self._items:
            return False
        if not reviewer:
            reviewer = os.getenv("REVIEWER_DEFAULT", "unknown")
        self._items[item_id].status = "rejected"
        self._items[item_id].reviewed_at = datetime.now().isoformat()
        self._items[item_id].reviewed_by = reviewer
        self._items[item_id].review_notes = reason
        self._save()
        logger.info(f"Review-Item {item_id[:12]} abgelehnt von {reviewer}: {reason}")
        return True

    @property
    def pending_count(self) -> int:
        return sum(1 for item in self._items.values() if item.status == "pending")

    def get_stats(self) -> dict:
        """Liefert Statistiken über die Review-Queue."""
        stats = {"pending": 0, "approved": 0, "rejected": 0}
        for item in self._items.values():
            if item.status in stats:
                stats[item.status] += 1
        return stats
