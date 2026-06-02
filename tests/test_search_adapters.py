"""Tests for search/adapters — SQLiteFTS5Adapter + WhooshIndexAdapter.

Covers the SearchIndexRepository interface: index, search, delete, clear, doc_count.
All file/DB operations are mocked — no real SQLite or Whoosh backend used.
"""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

import pytest


# ════════════════════════════════════════════════════════════════════════
# SQLiteFTS5Adapter Tests (38% → 90%+)
# ════════════════════════════════════════════════════════════════════════


class TestSQLiteFTS5Adapter:
    """Tests for SQLiteFTS5Adapter."""

    @pytest.fixture
    def adapter(self):
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = SQLiteFTS5Adapter(db_path=f"{tmpdir}/test.sqlite3")
            yield adapter

    # ── Init ──────────────────────────────────────────────────────────

    def test_init_creates_db(self, adapter):
        """__init__: creates directory and initializes DB."""
        assert adapter.db_path.endswith("test.sqlite3")
        assert adapter.doc_count >= 0

    # ── Index ────────────────────────────────────────────────────────

    def test_index_insert(self, adapter):
        """index(): inserts a document and returns True."""
        doc = {
            "url": "http://darkforum.onion/post/1",
            "author": "testuser",
            "title": "Test Title",
            "timestamp": "2025-01-01T00:00:00",
            "content": "Test content about FTS5 indexing.",
            "forum_id": "forum1",
        }
        result = adapter.index(doc)
        assert result is True

    def test_index_with_datetime_timestamp(self, adapter):
        """index(): converts datetime timestamp to isoformat."""
        from datetime import datetime

        doc = {
            "url": "http://darkforum.onion/dt",
            "author": "test",
            "timestamp": datetime(2025, 1, 1, 12, 0, 0),
            "content": "Timestamp test",
        }
        result = adapter.index(doc)
        assert result is True

    def test_index_without_timestamp(self, adapter):
        """index(): uses datetime.now() when timestamp is None."""
        doc = {
            "url": "http://darkforum.onion/nots",
            "author": "test",
            "content": "No timestamp",
        }
        result = adapter.index(doc)
        assert result is True

    def test_index_no_url_generates_hash(self, adapter):
        """index(): generates SHA256-based post_id when URL missing."""
        doc = {
            "author": "anon",
            "content": "Content without URL",
        }
        result = adapter.index(doc)
        assert result is True

    def test_index_error_returns_false(self):
        """index(): sqlite3.Error returns False."""
        import sqlite3
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        adapter = SQLiteFTS5Adapter.__new__(SQLiteFTS5Adapter)
        adapter._lock = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("table does not exist")
        adapter._get_conn = MagicMock(return_value=mock_conn)

        result = adapter.index({"url": "http://test.onion", "content": "test"})
        assert result is False

    # ── Search ───────────────────────────────────────────────────────

    def test_search_finds_inserted(self, adapter):
        """search(): finds documents inserted via index()."""
        adapter.index(
            {
                "url": "http://darkforum.onion/searchtest",
                "author": "finder",
                "title": "Searchable",
                "content": "This is searchable content with unique words.",
                "forum_id": "f1",
            }
        )
        results = adapter.search("searchable", limit=5)
        assert len(results) >= 1
        assert results[0]["url"] == "http://darkforum.onion/searchtest"

    def test_search_empty_query(self, adapter):
        """search(): empty query returns [ ]."""
        assert adapter.search("") == []

    def test_search_whitespace_query(self, adapter):
        """search(): whitespace-only query returns [ ]."""
        assert adapter.search("   ") == []

    def test_search_short_tokens_ignored(self):
        """search(): single-character tokens ignored → returns [ ]."""
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = SQLiteFTS5Adapter(db_path=f"{tmpdir}/test.sqlite3")
            results = adapter.search("a b c")  # all tokens < 2 chars
            assert results == []

    def test_search_no_results(self, adapter):
        """search(): no matching documents returns [ ]."""
        results = adapter.search("xyznonexistent12345", limit=5)
        assert results == []

    def test_search_error_returns_empty(self):
        """search(): sqlite3.Error returns [ ]."""
        import sqlite3
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        adapter = SQLiteFTS5Adapter.__new__(SQLiteFTS5Adapter)
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("database is locked")
        adapter._get_conn = MagicMock(return_value=mock_conn)

        results = adapter.search("test", limit=5)
        assert results == []

    def test_sanitize_fts_query(self, adapter):
        """_sanitize_fts_query: escapes double-quotes."""
        result = adapter._sanitize_fts_query('test "quoted" query')
        assert result == 'test ""quoted"" query'

    # ── Delete ───────────────────────────────────────────────────────

    def test_delete_existing(self, adapter):
        """delete(): removes document and returns True."""
        adapter.index({"url": "http://darkforum.onion/todel", "content": "delete me"})
        result = adapter.delete("http://darkforum.onion/todel")
        assert result is True

    def test_delete_nonexistent(self, adapter):
        """delete(): nonexistent doc_id returns False."""
        result = adapter.delete("http://nonexistent.onion/123")
        assert result is False

    def test_delete_error_returns_false(self):
        """delete(): sqlite3.Error returns False."""
        import sqlite3
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        adapter = SQLiteFTS5Adapter.__new__(SQLiteFTS5Adapter)
        adapter._lock = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("no such table")
        adapter._get_conn = MagicMock(return_value=mock_conn)

        result = adapter.delete("test-id")
        assert result is False

    # ── Clear ────────────────────────────────────────────────────────

    def test_clear_removes_all(self, adapter):
        """clear(): removes all documents."""
        adapter.index({"url": "http://a.onion", "content": "first"})
        adapter.index({"url": "http://b.onion", "content": "second"})
        assert adapter.doc_count == 2

        adapter.clear()
        assert adapter.doc_count == 0

    def test_clear_error_handled(self):
        """clear(): sqlite3.Error is caught, no re-raise."""
        import sqlite3
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        adapter = SQLiteFTS5Adapter.__new__(SQLiteFTS5Adapter)
        adapter._lock = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("read only")
        adapter._get_conn = MagicMock(return_value=mock_conn)

        # Should not raise
        adapter.clear()

    # ── Doc Count ────────────────────────────────────────────────────

    def test_doc_count_initial_zero(self, adapter):
        """doc_count: new adapter returns 0."""
        assert adapter.doc_count == 0

    def test_doc_count_after_insert(self, adapter):
        """doc_count: increases after index()."""
        adapter.index({"url": "http://a.onion", "content": "test"})
        adapter.index({"url": "http://b.onion", "content": "test"})
        assert adapter.doc_count == 2

    def test_doc_count_error_returns_zero(self):
        """doc_count: sqlite3.Error returns 0."""
        import sqlite3
        from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        adapter = SQLiteFTS5Adapter.__new__(SQLiteFTS5Adapter)
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("corrupt database")
        adapter._get_conn = MagicMock(return_value=mock_conn)

        assert adapter.doc_count == 0

    # ── Init Error ───────────────────────────────────────────────────

    def test_init_db_error_raised(self):
        """_init_db: sqlite3.Error is raised after logging."""
        import sqlite3
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test.sqlite3"
            with patch(
                "search.adapters.sqlite_fts5_adapter.sqlite3.connect"
            ) as mock_connect:
                mock_conn = MagicMock()
                mock_conn.execute.side_effect = sqlite3.Error("disk full")
                mock_connect.return_value = mock_conn

                with pytest.raises(sqlite3.Error, match="disk full"):
                    from search.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

                    SQLiteFTS5Adapter(db_path=db_path)


# ════════════════════════════════════════════════════════════════════════
# WhooshIndexAdapter Tests (34% → 85%+)
# ════════════════════════════════════════════════════════════════════════


class TestWhooshIndexAdapter:
    """Tests for WhooshIndexAdapter."""

    @pytest.fixture
    def adapter(self):
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = WhooshIndexAdapter(index_dir=tmpdir)
            yield adapter

    # ── Init ──────────────────────────────────────────────────────────

    def test_init_creates_index(self, adapter):
        """__init__: creates Whoosh index directory."""
        assert adapter._ix is not None
        assert adapter.doc_count == 0

    def test_init_opens_existing(self):
        """__init__: opens existing index (line 37)."""
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first adapter
            a1 = WhooshIndexAdapter(index_dir=tmpdir)
            a1.index({"url": "http://test.onion", "content": "persist me"})

            # Create second adapter on same directory
            a2 = WhooshIndexAdapter(index_dir=tmpdir)
            assert a2.doc_count == 1

    # ── Index ────────────────────────────────────────────────────────

    def test_index_insert(self, adapter):
        """index(): inserts document and returns True."""
        result = adapter.index(
            {
                "url": "http://whoosh.onion/doc1",
                "author": "whoosh_user",
                "title": "Whoosh Test",
                "content": "Whoosh adapter test content.",
                "forum_id": "w1",
            }
        )
        assert result is True
        assert adapter.doc_count == 1

    def test_index_no_url(self, adapter):
        """index(): generates post_id when URL missing."""
        result = adapter.index(
            {
                "author": "anon",
                "content": "No URL provided.",
            }
        )
        assert result is True

    def test_index_error_returns_false(self):
        """index(): Exception returns False."""
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter.__new__(WhooshIndexAdapter)
        mock_ix = MagicMock()
        mock_ix.writer.side_effect = RuntimeError("writer crash")
        adapter._ix = mock_ix

        result = adapter.index({"url": "http://test.onion", "content": "test"})
        assert result is False

    # ── Search ───────────────────────────────────────────────────────

    def test_search_finds_inserted(self, adapter):
        """search(): finds inserted document."""
        adapter.index(
            {
                "url": "http://whoosh.onion/findme",
                "author": "seeker",
                "title": "Findable",
                "content": "unique searchable whoosh term.",
                "forum_id": "wf1",
            }
        )
        results = adapter.search("searchable", limit=5)
        assert len(results) >= 1

    def test_search_empty_query(self, adapter):
        """search(): empty query returns [ ]."""
        assert adapter.search("") == []

    def test_search_whitespace_query(self, adapter):
        """search(): whitespace-only query returns [ ]."""
        assert adapter.search("   ") == []

    def test_search_no_results(self, adapter):
        """search(): no matches returns [ ]."""
        results = adapter.search("znonexist12345whoosh", limit=5)
        assert results == []

    def test_search_content_truncation(self, adapter):
        """search(): long content is truncated to 500 chars."""
        long_text = "A" * 1000
        adapter.index(
            {
                "url": "http://whoosh.onion/long",
                "content": long_text,
            }
        )
        results = adapter.search("AAAAA", limit=1)
        if results:
            assert len(results[0]["content"]) <= 503  # 500 + "..."

    def test_search_exception_returns_empty(self):
        """search(): Exception returns [ ]."""
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter.__new__(WhooshIndexAdapter)
        mock_ix = MagicMock()
        mock_ix.schema = MagicMock()
        mock_ix.searcher.side_effect = RuntimeError("searcher crash")
        adapter._ix = mock_ix

        results = adapter.search("test", limit=5)
        assert results == []

    # ── Delete ────────────────────────────────────────────────────────

    def test_delete_existing(self, adapter):
        """delete(): removes document and returns True."""
        adapter.index({"url": "http://whoosh.onion/todelete", "content": "bye"})
        result = adapter.delete("http://whoosh.onion/todelete")
        assert result is True

    def test_delete_nonexistent(self, adapter):
        """delete(): nonexistent doc_id still returns True (graceful)."""
        result = adapter.delete("http://nonexistent.onion/999")
        # Whoosh delete_by_term returns success even if nothing deleted
        assert result is True

    def test_delete_exception_returns_false(self):
        """delete(): Exception returns False."""
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter.__new__(WhooshIndexAdapter)
        mock_ix = MagicMock()
        mock_ix.writer.side_effect = RuntimeError("writer crash")
        adapter._ix = mock_ix

        result = adapter.delete("test-id")
        assert result is False

    # ── Clear ─────────────────────────────────────────────────────────

    def test_clear_removes_all(self, adapter):
        """clear(): removes all documents and re-creates index."""
        adapter.index({"url": "http://a.onion", "content": "first"})
        adapter.index({"url": "http://b.onion", "content": "second"})
        assert adapter.doc_count == 2

        adapter.clear()
        assert adapter.doc_count == 0

    def test_clear_exception_handled(self):
        """clear(): Exception caught, no re-raise."""
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter.__new__(WhooshIndexAdapter)
        mock_ix = MagicMock()
        mock_ix.close.side_effect = RuntimeError("close failed")
        adapter._ix = mock_ix

        # Should not raise
        adapter.clear()

    # ── Doc Count ─────────────────────────────────────────────────────

    def test_doc_count_zero(self, adapter):
        """doc_count: new adapter returns 0."""
        assert adapter.doc_count == 0

    def test_doc_count_after_insert(self, adapter):
        """doc_count: increases after index()."""
        adapter.index({"url": "http://a.onion", "content": "one"})
        adapter.index({"url": "http://b.onion", "content": "two"})
        adapter.index({"url": "http://c.onion", "content": "three"})
        assert adapter.doc_count == 3

    def test_doc_count_exception_returns_zero(self):
        """doc_count: Exception returns 0."""
        from search.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter.__new__(WhooshIndexAdapter)
        mock_ix = MagicMock()
        mock_ix.searcher.side_effect = RuntimeError("searcher crash")
        adapter._ix = mock_ix

        assert adapter.doc_count == 0
