# =============================================================================
# Concurrency-Stresstests: ChromaDB VectorStore (#122)
# =============================================================================
# Testet Thread-Safety und Retry bei parallelen add()/query() Operationen.
# Verifiziert, dass kein "database is locked"-Fehler Datenverlust verursacht.
#
# Ausführung:
#   python3 -m pytest tests/test_vectordb_concurrency.py -v
# =============================================================================

import os
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _random_embedding(dim: int = 768) -> list[float]:
    """Erzeugt einen zufälligen Embedding-Vektor (für Tests ohne Ollama)."""
    import random

    return [random.uniform(-1.0, 1.0) for _ in range(dim)]


def test_vectordb_concurrent_add_query():
    """Stress-Test: 4 Threads parallel add + query — keine Lock-Fehler."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(persist_directory=tmpdir, collection_name="stress_test")

        errors = []
        results = []

        def worker(worker_id: int):
            try:
                doc_id = f"doc-{worker_id}-{uuid.uuid4().hex[:8]}"
                doc_text = f"Test document from worker {worker_id}"
                embedding = _random_embedding()

                # Add
                success = store.add_one(
                    document=doc_text,
                    embedding=embedding,
                    doc_id=doc_id,
                )
                if not success:
                    errors.append(f"Worker {worker_id}: add failed")

                # Query
                found = store.query(embedding, n_results=5)
                results.append((worker_id, len(found)))

                # Count
                c = store.count
                results.append((worker_id, f"count={c}"))
            except Exception as e:
                errors.append(f"Worker {worker_id}: {type(e).__name__}: {e}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(4)]
            for f in futures:
                f.result(timeout=10)

    assert len(errors) == 0, f"Concurrency errors: {errors}"
    assert len(results) >= 8, f"Expected ≥8 results, got {len(results)}: {results}"


def test_vectordb_concurrent_add_only():
    """Stress-Test: 8 Threads parallel add — kein Datenverlust."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(persist_directory=tmpdir, collection_name="add_stress")

        errors = []

        def worker(worker_id: int):
            try:
                doc_id = f"doc-{worker_id}-{uuid.uuid4().hex[:8]}"
                success = store.add_one(
                    document=f"Test {worker_id}",
                    embedding=_random_embedding(),
                    doc_id=doc_id,
                )
                if not success:
                    errors.append(f"Worker {worker_id}: add failed")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {type(e).__name__}: {e}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(8)]
            for f in futures:
                f.result(timeout=10)

    assert len(errors) == 0, f"Concurrency add errors: {errors}"


def test_vectordb_concurrent_mixed_operations():
    """Stress-Test: Add + Query + Count + Delete parallel — keine Korruption."""
    from vectordb.store import VectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore(persist_directory=tmpdir, collection_name="mixed_stress")

        # Zuerst 10 Dokumente einfüllen
        for i in range(10):
            store.add_one(
                document=f"Base doc {i}",
                embedding=_random_embedding(),
                doc_id=f"base-{i}",
            )

        errors = []

        def add_worker(wid: int):
            store.add_one(
                document=f"Added by {wid}",
                embedding=_random_embedding(),
                doc_id=f"added-{wid}-{uuid.uuid4().hex[:8]}",
            )

        def query_worker(wid: int):
            results = store.query(_random_embedding(), n_results=5)
            if not isinstance(results, list):
                errors.append(f"Query worker {wid}: non-list result")

        def count_worker(wid: int):
            c = store.count
            if not isinstance(c, int):
                errors.append(f"Count worker {wid}: non-int result")

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            # 2 add, 2 query, 2 count — gleichzeitig
            futures.append(executor.submit(add_worker, 0))
            futures.append(executor.submit(add_worker, 1))
            futures.append(executor.submit(query_worker, 2))
            futures.append(executor.submit(query_worker, 3))
            futures.append(executor.submit(count_worker, 4))
            futures.append(executor.submit(count_worker, 5))
            for f in futures:
                f.result(timeout=10)

    assert len(errors) == 0, f"Mixed concurrency errors: {errors}"
