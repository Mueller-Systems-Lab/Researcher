# =============================================================================
# Concurrency-Stresstests: WhooshIndex (#123)
# =============================================================================
# Testet Thread-Safety bei parallelen add_post/search/optimize/clear.
#
# Ausführung:
#   python3 -m pytest tests/test_whoosh_concurrency.py -v
# =============================================================================

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_post(post_id: str, content: str) -> dict:
    return {
        "url": f"http://forum.onion/{post_id}",
        "author": "testuser",
        "title": f"Post {post_id}",
        "timestamp": datetime.now(),
        "content": content,
        "forum_id": "test_forum",
    }


def test_whoosh_concurrent_add_search():
    """Stress-Test: 4 Threads parallel add + search — keine Lock-Fehler."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        # Pre-populate with some data
        for i in range(5):
            idx.add_post(_make_post(f"pre-{i}", f"Base content {i}"))

        errors = []

        def add_worker(wid: int):
            try:
                ok = idx.add_post(_make_post(f"add-{wid}", f"Added by {wid}"))
                if not ok:
                    errors.append(f"Add worker {wid}: add failed")
            except Exception as e:
                errors.append(f"Add worker {wid}: {type(e).__name__}: {e}")

        def search_worker(wid: int):
            try:
                results = idx.search("content", limit=5)
                if not isinstance(results, list):
                    errors.append(f"Search worker {wid}: non-list result")
            except Exception as e:
                errors.append(f"Search worker {wid}: {type(e).__name__}: {e}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(add_worker, 0),
                executor.submit(add_worker, 1),
                executor.submit(search_worker, 2),
                executor.submit(search_worker, 3),
            ]
            for f in futures:
                f.result(timeout=10)

    assert len(errors) == 0, f"Concurrency errors: {errors}"


def test_whoosh_concurrent_add_optimize():
    """Stress-Test: parallel add + optimize — keine Korruption."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        for i in range(10):
            idx.add_post(_make_post(f"pre-{i}", f"Content {i}"))

        errors = []

        def add_worker(wid: int):
            try:
                ok = idx.add_post(_make_post(f"opt-add-{wid}", f"Optimize add {wid}"))
                if not ok:
                    errors.append(f"Worker {wid}: add failed")
            except Exception as e:
                errors.append(f"Worker {wid}: {e}")

        def optimize_worker():
            try:
                idx.optimize()
            except Exception as e:
                errors.append(f"Optimize: {e}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(add_worker, 0),
                executor.submit(add_worker, 1),
                executor.submit(optimize_worker),
            ]
            for f in futures:
                f.result(timeout=10)

    assert len(errors) == 0, f"Add+optimize errors: {errors}"


def test_whoosh_concurrent_bulk_operations():
    """Stress-Test: 6 Threads — add + search + optimize + count — keine Fehler."""
    from darknet_search.index import WhooshIndex

    with tempfile.TemporaryDirectory() as tmpdir:
        idx = WhooshIndex(tmpdir)
        for i in range(20):
            idx.add_post(_make_post(f"bulk-{i}", f"Bulk content {i}"))

        errors = []

        def worker(op: str, wid: int):
            try:
                if op == "add":
                    idx.add_post(_make_post(f"w{wid}", f"Worker {wid} content"))
                elif op == "search":
                    idx.search("content", limit=5)
                elif op == "count":
                    c = idx.doc_count
                    if not isinstance(c, int):
                        errors.append(f"Count: non-int: {c}")
                elif op == "optimize":
                    idx.optimize()
            except Exception as e:
                errors.append(f"{op}-{wid}: {type(e).__name__}: {e}")

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [
                executor.submit(worker, "add", 0),
                executor.submit(worker, "add", 1),
                executor.submit(worker, "search", 2),
                executor.submit(worker, "search", 3),
                executor.submit(worker, "count", 4),
                executor.submit(worker, "optimize", 5),
            ]
            for f in futures:
                f.result(timeout=10)

    assert len(errors) == 0, f"Bulk errors: {errors}"
