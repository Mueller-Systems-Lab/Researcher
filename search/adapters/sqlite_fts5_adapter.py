"""SQLiteFTS5Adapter — SQLite FTS5-based search index adapter."""

import hashlib
import logging
import os
import sqlite3
from datetime import datetime
from threading import Lock

from search.ports.search_index_repository import SearchIndexRepository

logger = logging.getLogger(__name__)

_CREATE_CONTENT_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    post_id    TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    author     TEXT DEFAULT '',
    title      TEXT DEFAULT '',
    timestamp  TEXT DEFAULT '',
    content    TEXT DEFAULT '',
    forum_id   TEXT DEFAULT 'unknown'
)
"""
_CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
    author, title, content, forum_id,
    content='posts', content_rowid='rowid'
)
"""
_CREATE_INSERT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, author, title, content, forum_id)
    VALUES (new.rowid, new.author, new.title, new.content, new.forum_id);
END
"""
_CREATE_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, author, title, content, forum_id)
    VALUES ('delete', old.rowid, old.author, old.title, old.content, old.forum_id);
END
"""
_CREATE_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, author, title, content, forum_id)
    VALUES ('delete', old.rowid, old.author, old.title, old.content, old.forum_id);
    INSERT INTO posts_fts(rowid, author, title, content, forum_id)
    VALUES (new.rowid, new.author, new.title, new.content, new.forum_id);
END
"""


class SQLiteFTS5Adapter(SearchIndexRepository):
    def __init__(self, db_path: str = "./darknet_index/darknet_index.sqlite3"):
        self.db_path = db_path
        self._lock = Lock()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                for stmt in [
                    _CREATE_CONTENT_TABLE,
                    _CREATE_FTS_TABLE,
                    _CREATE_INSERT_TRIGGER,
                    _CREATE_DELETE_TRIGGER,
                    _CREATE_UPDATE_TRIGGER,
                ]:
                    conn.execute(stmt)
                conn.commit()
                logger.info(f"SQLite FTS5-Index initialisiert: {self.db_path}")
            except sqlite3.Error as e:
                logger.exception(f"Fehler bei DB-Initialisierung: {e}")
                raise
            finally:
                conn.close()

    def _sanitize_fts_query(self, query: str) -> str:
        return query.replace('"', '""')

    def index(self, doc: dict) -> bool:
        post_id = doc.get("url") or hashlib.sha256(str(doc).encode()).hexdigest()[:32]
        ts = doc.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.isoformat()
        elif not ts:
            ts = datetime.now().isoformat()
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO posts "
                    "(post_id, url, author, title, timestamp, content, forum_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        post_id,
                        doc.get("url", ""),
                        doc.get("author", ""),
                        doc.get("title", ""),
                        str(ts),
                        doc.get("content", ""),
                        doc.get("forum_id", "unknown"),
                    ),
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                logger.exception(f"SQLite FTS5-Indexfehler: {e}")
                return False
            finally:
                conn.close()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        if not query.strip():
            return []
        conn = self._get_conn()
        try:
            sanitized = self._sanitize_fts_query(query)
            tokens = [t for t in sanitized.split() if len(t) >= 2]
            if not tokens:
                return []
            fts_query = " AND ".join(tokens)
            cursor = conn.execute(
                "SELECT p.post_id, p.url, p.author, p.title, "
                "p.timestamp, p.content, p.forum_id, "
                "bm25(posts_fts) AS score "
                "FROM posts_fts JOIN posts p ON p.rowid = posts_fts.rowid "
                "WHERE posts_fts MATCH ? ORDER BY score LIMIT ?",
                (fts_query, limit),
            )
            output = []
            for row in cursor.fetchall():
                content = row[5][:500] + "..." if len(row[5]) > 500 else row[5]
                output.append(
                    {
                        "url": row[1],
                        "author": row[2],
                        "title": row[3] if row[3] else "Darknet Post",
                        "timestamp": row[4],
                        "content": content,
                        "source": "Darknet Forum (SQLite FTS5)",
                        "score": float(row[7] or 0),
                        "forum_id": row[6],
                    }
                )
            return output
        except sqlite3.Error as e:
            logger.exception(f"SQLite FTS5-Suchfehler: {e}")
            return []
        finally:
            conn.close()

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("DELETE FROM posts WHERE post_id = ?", (doc_id,))
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                logger.exception(f"SQLite FTS5-Löschfehler: {e}")
                return False
            finally:
                conn.close()

    def clear(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM posts")
                conn.execute("DELETE FROM posts_fts")
                conn.commit()
                logger.info("SQLite FTS5-Index geleert")
            except sqlite3.Error as e:
                logger.exception(f"SQLite FTS5-Fehler beim Leeren: {e}")
            finally:
                conn.close()

    @property
    def doc_count(self) -> int:
        conn = self._get_conn()
        try:
            return conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()
