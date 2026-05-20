# =============================================================================
# Benchmark: WhooshIndexAdapter vs SQLiteFTS5Adapter
# =============================================================================
# Misst index() und search() für 100, 1.000, 10.000 Dokumente.
# pytest-benchmark kompatibel.
#
# Installation:
#   pip install pytest-benchmark
# Ausführung:
#   python -m pytest tests/benchmarks/ -v --benchmark-only
# =============================================================================

import os
import tempfile
import time

import pytest

# Graceful skip wenn pytest-benchmark nicht installiert ist
pytest.importorskip("pytest_benchmark")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _generate_docs(n: int) -> list[dict]:
    """Generiert n synthetische Dokumente für den Benchmark."""
    docs = []
    for i in range(n):
        docs.append(
            {
                "url": f"https://darknet.example/post_{i}",
                "author": f"researcher_{i % 10}",
                "title": f"Analysis of Darknet Market {i}",
                "content": (
                    f"This is document number {i}. "
                    f"It contains analysis of darknet marketplace activity. "
                    f"Key findings include price trends for various illicit goods "
                    f"and services. The document discusses cryptocurrency payments, "
                    f"escrow mechanisms, vendor reputation systems, and forum "
                    f"communication patterns. Additional metadata includes "
                    f"timestamps, geolocation hints, and language analysis."
                ),
                "forum_id": f"market_{i % 5}",
            }
        )
    return docs


@pytest.fixture
def benchmark_docs_100():
    return _generate_docs(100)


@pytest.fixture
def benchmark_docs_1000():
    return _generate_docs(1000)


@pytest.fixture
def temp_whoosh_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_sqlite_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ---------------------------------------------------------------------------
# Whoosh Benchmarks
# ---------------------------------------------------------------------------


class TestWhooshBenchmark:
    """Benchmarks für WhooshIndexAdapter."""

    @pytest.mark.benchmark
    def test_whoosh_index_100(self, benchmark, benchmark_docs_100, temp_whoosh_dir):
        """Whoosh: 100 Dokumente indexieren."""
        from gpt_researcher.adapters.whoosh_index_adapter import WhooshIndexAdapter

        def run():
            adapter = WhooshIndexAdapter(temp_whoosh_dir)
            for doc in benchmark_docs_100:
                adapter.index(doc)
            return adapter.doc_count

        count = benchmark(run)
        assert count == 100

    @pytest.mark.benchmark
    def test_whoosh_search_100(self, benchmark, benchmark_docs_100, temp_whoosh_dir):
        """Whoosh: Suche in 100 Dokumenten."""
        from gpt_researcher.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter(temp_whoosh_dir)
        for doc in benchmark_docs_100:
            adapter.index(doc)

        result = benchmark(lambda: adapter.search("darknet marketplace", limit=10))
        assert len(result) > 0

    @pytest.mark.benchmark
    def test_whoosh_index_1000(self, benchmark, benchmark_docs_1000, temp_whoosh_dir):
        """Whoosh: 1000 Dokumente indexieren."""
        from gpt_researcher.adapters.whoosh_index_adapter import WhooshIndexAdapter

        def run():
            adapter = WhooshIndexAdapter(temp_whoosh_dir)
            for doc in benchmark_docs_1000:
                adapter.index(doc)
            return adapter.doc_count

        count = benchmark(run)
        assert count == 1000

    @pytest.mark.benchmark
    def test_whoosh_search_1000(self, benchmark, benchmark_docs_1000, temp_whoosh_dir):
        """Whoosh: Suche in 1000 Dokumenten."""
        from gpt_researcher.adapters.whoosh_index_adapter import WhooshIndexAdapter

        adapter = WhooshIndexAdapter(temp_whoosh_dir)
        for doc in benchmark_docs_1000:
            adapter.index(doc)

        result = benchmark(lambda: adapter.search("darknet marketplace", limit=10))
        assert len(result) > 0


# ---------------------------------------------------------------------------
# SQLite FTS5 Benchmarks
# ---------------------------------------------------------------------------


class TestSQLiteFTS5Benchmark:
    """Benchmarks für SQLiteFTS5Adapter."""

    @pytest.mark.benchmark
    def test_sqlite_index_100(self, benchmark, benchmark_docs_100, temp_sqlite_dir):
        """SQLite FTS5: 100 Dokumente indexieren."""
        from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        db_path = os.path.join(temp_sqlite_dir, "bench.sqlite3")

        def run():
            adapter = SQLiteFTS5Adapter(db_path)
            for doc in benchmark_docs_100:
                adapter.index(doc)
            return adapter.doc_count

        count = benchmark(run)
        assert count == 100

    @pytest.mark.benchmark
    def test_sqlite_search_100(self, benchmark, benchmark_docs_100, temp_sqlite_dir):
        """SQLite FTS5: Suche in 100 Dokumenten."""
        from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        db_path = os.path.join(temp_sqlite_dir, "bench.sqlite3")
        adapter = SQLiteFTS5Adapter(db_path)
        for doc in benchmark_docs_100:
            adapter.index(doc)

        result = benchmark(lambda: adapter.search("darknet marketplace", limit=10))
        assert len(result) > 0

    @pytest.mark.benchmark
    def test_sqlite_index_1000(self, benchmark, benchmark_docs_1000, temp_sqlite_dir):
        """SQLite FTS5: 1000 Dokumente indexieren."""
        from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        db_path = os.path.join(temp_sqlite_dir, "bench.sqlite3")

        def run():
            adapter = SQLiteFTS5Adapter(db_path)
            for doc in benchmark_docs_1000:
                adapter.index(doc)
            return adapter.doc_count

        count = benchmark(run)
        assert count == 1000

    @pytest.mark.benchmark
    def test_sqlite_search_1000(self, benchmark, benchmark_docs_1000, temp_sqlite_dir):
        """SQLite FTS5: Suche in 1000 Dokumenten."""
        from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

        db_path = os.path.join(temp_sqlite_dir, "bench.sqlite3")
        adapter = SQLiteFTS5Adapter(db_path)
        for doc in benchmark_docs_1000:
            adapter.index(doc)

        result = benchmark(lambda: adapter.search("darknet marketplace", limit=10))
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Vergleichs-Benchmark (100 docs, beide Backends)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_compare_index_100(
    benchmark, benchmark_docs_100, temp_whoosh_dir, temp_sqlite_dir
):
    """Vergleich: Whoosh vs SQLite FTS5 index() für 100 Dokumente."""
    from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter
    from gpt_researcher.adapters.whoosh_index_adapter import WhooshIndexAdapter

    db_path = os.path.join(temp_sqlite_dir, "bench.sqlite3")

    # Whoosh
    def whoosh_run():
        adapter = WhooshIndexAdapter(temp_whoosh_dir)
        for doc in benchmark_docs_100:
            adapter.index(doc)
        return adapter.doc_count

    whoosh_result = benchmark.pedantic(whoosh_run, rounds=3, warmup_rounds=1)

    # SQLite FTS5
    def sqlite_run():
        adapter = SQLiteFTS5Adapter(db_path)
        for doc in benchmark_docs_100:
            adapter.index(doc)
        return adapter.doc_count

    # Einfacher Zeitvergleich (ohne benchmark fixture für sqlite)
    start = time.perf_counter()
    sqlite_count = sqlite_run()
    sqlite_time = time.perf_counter() - start

    assert whoosh_result == 100
    assert sqlite_count == 100
    print("\n  Whoosh index 100: (benchmarked above)")
    print(f"  SQLite FTS5 index 100: {sqlite_time:.4f}s")
