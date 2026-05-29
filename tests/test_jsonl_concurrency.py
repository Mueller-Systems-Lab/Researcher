# =============================================================================
# Concurrency-Stresstests: JSONL Persistence (#125)
# =============================================================================
# Testet Thread-Safety bei parallelen JSONL-Append- und Read-Operationen
# mit dem evidence_store und audit_log.
#
# Ausführung:
#   python3 -m pytest tests/test_jsonl_concurrency.py -v
# =============================================================================

import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _write_jsonl_line(path: Path, record: dict) -> None:
    """Thread-safe JSONL append (gleiches Pattern wie _safe_append in store.py)."""
    line = json.dumps(record, ensure_ascii=False)
    with threading.Lock():  # module-level lock wie in evidence_store
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _read_jsonl_lines(path: Path) -> list[dict]:
    """Robust JSONL reader — ignoriert korrupte Zeilen."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def test_jsonl_concurrent_append_read():
    """Stress-Test: 4 Threads parallel JSONL append + read — keine Korruption."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "stress.jsonl"
        errors = []

        def append_worker(wid: int):
            for j in range(10):
                _write_jsonl_line(path, {"worker": wid, "seq": j, "ts": time.time()})

        def read_worker(wid: int):
            for _ in range(5):
                entries = _read_jsonl_lines(path)
                for e in entries:
                    if not isinstance(e, dict):
                        errors.append(f"Read {wid}: non-dict entry")
                    if "worker" not in e or "seq" not in e:
                        errors.append(f"Read {wid}: missing keys in {e}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(append_worker, 0),
                executor.submit(append_worker, 1),
                executor.submit(read_worker, 2),
                executor.submit(read_worker, 3),
            ]
            for f in futures:
                f.result(timeout=15)

        # Final read — alle 20 Einträge (2 Worker × 10) sollten da sein
        all_entries = _read_jsonl_lines(path)
        assert len(all_entries) >= 20, f"Expected ≥20 entries, got {len(all_entries)}"

    assert len(errors) == 0, f"Concurrency errors: {errors}"


def test_jsonl_concurrent_single_writer_multi_reader():
    """Stress-Test: 1 Writer, 3 Reader parallel — keine korrupten Zeilen."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "single_writer.jsonl"
        errors = []

        def writer():
            for j in range(50):
                _write_jsonl_line(path, {"seq": j, "data": f"line-{j}"})
                time.sleep(0.001)  # kleine Pause, sonst alles in einem Batch

        def reader(wid: int):
            for _ in range(10):
                entries = _read_jsonl_lines(path)
                for e in entries:
                    if not isinstance(e, dict) or "seq" not in e:
                        errors.append(f"Reader {wid}: corrupt entry: {e}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(writer),
                executor.submit(reader, 1),
                executor.submit(reader, 2),
                executor.submit(reader, 3),
            ]
            for f in futures:
                f.result(timeout=15)

        all_entries = _read_jsonl_lines(path)
        assert len(all_entries) >= 50, f"Expected ≥50 entries, got {len(all_entries)}"

    assert len(errors) == 0, f"Single-writer errors: {errors}"


def test_jsonl_no_partial_lines():
    """Edge-Case: Kein Thread hinterlässt partielle JSONL-Zeilen."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "partial.jsonl"
        done = threading.Event()

        def writer(wid: int):
            for j in range(20):
                _write_jsonl_line(path, {"w": wid, "j": j})
            done.set()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(writer, w) for w in range(2)]
            for f in futures:
                f.result(timeout=10)

        # Nachdem alle fertig sind, muss jede Zeile valides JSON sein
        for i, line in enumerate(
            path.read_text(encoding="utf-8").strip().split("\n"), 1
        ):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                assert isinstance(data, dict), f"Line {i}: not a dict"
                assert "w" in data and "j" in data, f"Line {i}: missing keys"
            except json.JSONDecodeError as e:
                raise AssertionError(f"Line {i}: invalid JSON: {e} (line={line!r})")
