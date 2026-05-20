# =============================================================================
# Onion Discovery — Seed Queue
# =============================================================================
# Verwaltet bekannte .onion-Seeds, priorisiert und trackt deren Status.
# Seeds können aus Dateien, manueller Eingabe oder anderen Quellen stammen.
#
# Nutzung:
#   queue = SeedQueue()
#   queue.add_seed("http://darkforumabc123.onion")
#   seed = queue.get_next()
#   queue.mark_completed(seed_id)
# =============================================================================

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SeedEntry:
    """Ein einzelner Seed-Eintrag."""

    url: str
    source: str = "manual"  # manual, file, crawl, submission
    priority: int = 5  # 1-10 (10 = höchste)
    status: str = (
        "pending"  # pending, fetching, parsed, reviewed, approved, rejected, error
    )
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    fetched_at: str | None = None
    reviewed_at: str | None = None
    error: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""


class SeedQueue:
    """Verwaltet die Warteschlange der bekannten .onion-Seeds."""

    def __init__(self, seed_file: str | None = None):
        self.seed_file = seed_file or os.getenv("ONION_SEED_FILE", "./onion_seeds.json")
        self._seeds: dict[str, SeedEntry] = {}
        self._load()

    def _load(self):
        """Lädt Seeds aus der JSON-Datei."""
        if os.path.exists(self.seed_file):
            try:
                with open(self.seed_file) as f:
                    data = json.load(f)
                for entry in data:
                    seed = SeedEntry(**entry)
                    self._seeds[seed.url] = seed
                logger.info(f"{len(self._seeds)} Seeds aus {self.seed_file} geladen")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Fehler beim Laden der Seeds: {e}")

    def _save(self):
        """Speichert Seeds in die JSON-Datei."""
        try:
            os.makedirs(os.path.dirname(self.seed_file) or ".", exist_ok=True)
            with open(self.seed_file, "w") as f:
                json.dump(
                    [asdict(s) for s in self._seeds.values()],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except (OSError, TypeError) as e:
            logger.error(f"Fehler beim Speichern der Seeds: {e}")

    def add_seed(
        self,
        url: str,
        source: str = "manual",
        priority: int = 5,
        tags: list[str] | None = None,
        auto_save: bool = True,
    ) -> bool:
        """Fügt einen neuen Seed hinzu (ignoriert Duplikate).

        Args:
            url: Die Seed-URL.
            source: Quelle des Seeds.
            priority: Priorität 1–10 (10 = höchste).
            tags: Optionale Tags.
            auto_save: Wenn False, wird nicht automatisch gespeichert.
                Nützlich für Batch-Operationen via add_seeds().

        Returns:
            True bei neuem Seed, False bei Duplikat.
        """
        url = url.rstrip("/")
        if url in self._seeds:
            return False
        self._seeds[url] = SeedEntry(
            url=url,
            source=source,
            priority=max(1, min(10, priority)),
            tags=tags or [],
        )
        if auto_save:
            self._save()
        logger.info(f"Seed hinzugefügt: {url} (Quelle: {source})")
        return True

    def add_seeds(
        self,
        urls: list[str],
        source: str = "manual",
        priority: int = 5,
    ) -> int:
        """Fügt mehrere Seeds hinzu (Batch mit einem Save).

        Returns:
            Anzahl neu hinzugefügter Seeds.
        """
        count = 0
        for url in urls:
            if self.add_seed(url, source, priority, auto_save=False):
                count += 1
        if count > 0:
            self._save()
            logger.info(f"{count} Seeds batch-hinzugefügt (Quelle: {source})")
        return count

    def get_next(self, max_priority: int = 10) -> SeedEntry | None:
        """Holt den nächsten zu verarbeitenden Seed (höchste Priorität zuerst).

        Args:
            max_priority: Maximal zu berücksichtigende Priorität.

        Returns:
            SeedEntry oder None, wenn keine pending Seeds.
        """
        pending = [
            s
            for s in self._seeds.values()
            if s.status == "pending" and s.priority <= max_priority
        ]
        if not pending:
            return None
        # Sortieren: höchste Priorität, älteste zuerst
        pending.sort(key=lambda s: (-s.priority, s.added_at))
        seed = pending[0]
        seed.status = "fetching"
        self._save()
        return seed

    def mark_completed(self, url: str, status: str = "approved"):
        """Markiert einen Seed als verarbeitet."""
        if url in self._seeds:
            self._seeds[url].status = status
            self._seeds[url].fetched_at = datetime.now().isoformat()
            self._save()

    def mark_error(self, url: str, error: str):
        """Markiert einen Seed als fehlgeschlagen."""
        if url in self._seeds:
            self._seeds[url].status = "error"
            self._seeds[url].error = error
            self._save()

    @property
    def pending_count(self) -> int:
        """Anzahl der noch zu verarbeitenden Seeds."""
        return sum(1 for s in self._seeds.values() if s.status == "pending")

    @property
    def total_count(self) -> int:
        return len(self._seeds)

    def get_stats(self) -> dict:
        """Liefert Statistiken über die Seed-Queue."""
        statuses: dict[str, int] = {}
        for s in self._seeds.values():
            statuses[s.status] = statuses.get(s.status, 0) + 1
        return {
            "total": self.total_count,
            "pending": self.pending_count,
            **statuses,
        }
