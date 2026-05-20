# =============================================================================
# Tests: Deutsche Report-Evaluation (Issue #76)
# =============================================================================
# Prüft, dass die Report-Evaluation deutsche Umlaut-Reports korrekt bewertet.
# Alle Tests sind gemockt — keine echten Netzwerkdienste.
# =============================================================================
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helper ────────────────────────────────────────────────────────────────────


def _make_german_report(content: str, tmpdir: str) -> str:
    """Schreibt einen deutschen Report und gibt den Pfad zurück."""
    path = os.path.join(tmpdir, "german_report_test.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ── Report mit Umlauten bleibt lesbar / parse_report ───────────────────────────


def test_parse_german_report_with_umlauts():
    """parse_report() verarbeitet Reports mit deutschen Umlauten korrekt."""
    from scripts.evaluate_research_report import parse_report

    with tempfile.TemporaryDirectory() as d:
        path = _make_german_report(
            "# Research Report\n\n"
            "## Metadata\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            "| Query | Was bedeutet Übergröße? |\n"
            "| SearXNG Result Count | 4 |\n"
            "| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
            "| Ollama Chat Model Used | `qwen3.5:9b` |\n"
            "| Model Fallback Used | false |\n"
            "| Degraded Mode | false |\n"
            "\n"
            "## Summary\n\n"
            "Übergröße bezeichnet Kleidungsstücke in besonders großen Größen.\n"
            "Dies ist ein Fakt aus den Quellen [S1], [S2].\n"
            "\n"
            "## Sources\n\n"
            "### [S1] Quelle Eins\n\n"
            "- **URL:** https://example.com/1\n\n"
            "### [S2] Quelle Zwei\n\n"
            "- **URL:** https://example.com/2\n\n"
            "### [S3] Quelle Drei\n\n"
            "- **URL:** https://example.com/3\n\n"
            "### [S4] Quelle Vier\n\n"
            "- **URL:** https://example.com/4\n\n"
            "\n"
            "## Limitations and Warnings\n\n"
            "- Grenzen des Reports.\n",
            d,
        )
        report = parse_report(path)

        # Query mit Umlaut muss erhalten sein
        assert report["query"] == "Was bedeutet Übergröße?"
        assert "Ü" in report["query"]

        # Source Count
        assert report["source_count"] == 4

        # Abschnitte erkannt
        assert report["has_metadata_section"] is True
        assert report["has_source_section"] is True
        assert report["has_summary_section"] is True
        assert report["has_limitations_section"] is True

        # Source-IDs erkannt
        assert report["source_ids"] >= 2

        # Keine Cloud-Referenzen
        assert report["cloud_references"] == []

        # Nicht degraded
        assert report["model_fallback"] is False


def test_parse_german_report_fussgaengerzone():
    """parse_report() verarbeitet 'Fußgängerzone'-Report korrekt."""
    from scripts.evaluate_research_report import parse_report

    with tempfile.TemporaryDirectory() as d:
        path = _make_german_report(
            "# Research Report\n\n"
            "## Metadata\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            "| Query | Was ist eine Fußgängerzone? |\n"
            "| SearXNG Result Count | 3 |\n"
            "| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
            "| Ollama Chat Model Used | `qwen3.5:9b` |\n"
            "| Model Fallback Used | false |\n"
            "| Degraded Mode | false |\n"
            "\n"
            "## Summary\n\n"
            "Eine Fußgängerzone ist ein Bereich für den Fußverkehr.\n"
            "\n"
            "## Sources\n\n"
            "### [S1] Wikipedia\n\n"
            "- **URL:** https://de.wikipedia.org/wiki/Fu%C3%9Fg%C3%A4ngerzone\n"
            "\n"
            "## Limitations and Warnings\n\n"
            "- Grenzen.\n",
            d,
        )
        report = parse_report(path)

        assert report["query"] == "Was ist eine Fußgängerzone?"
        assert "ß" in report["query"]
        assert report["source_count"] == 3
        assert report["has_source_section"] is True


def test_parse_german_report_muellerstrasse():
    """parse_report() verarbeitet 'Müllerstraße'-Report korrekt."""
    from scripts.evaluate_research_report import parse_report

    with tempfile.TemporaryDirectory() as d:
        path = _make_german_report(
            "# Research Report\n\n"
            "## Metadata\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            "| Query | Was ist die Müllerstraße als Wortbeispiel? |\n"
            "| SearXNG Result Count | 2 |\n"
            "| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
            "| Ollama Chat Model Used | `qwen3.5:9b` |\n"
            "| Model Fallback Used | false |\n"
            "| Degraded Mode | false |\n"
            "\n"
            "## Summary\n\n"
            "Die Müllerstraße ist ein häufiger Straßenname.\n"
            "\n"
            "## Sources\n\n"
            "### [S1] Beispielquelle\n\n"
            "- **URL:** https://example.com\n"
            "\n"
            "## Limitations and Warnings\n\n"
            "- Grenzen.\n",
            d,
        )
        report = parse_report(path)

        assert "Müllerstraße" in report["query"]
        assert "ü" in report["query"]
        assert report["source_count"] == 2


# ── Source Coverage mit deutschen Reports ──────────────────────────────────────


def test_source_coverage_german_report():
    """Source Coverage funktioniert für deutschen Report."""
    from scripts.evaluate_research_report import score_source_coverage

    report = {
        "has_source_section": True,
        "source_count": 4,
        "sources_listed": 4,
        "has_summary_section": True,
    }
    score, notes = score_source_coverage(report)
    assert score >= 80, f"Source Coverage zu niedrig: {score} ({notes})"


def test_source_coverage_german_report_no_sources():
    """Source Coverage erkennt fehlende Quellen im deutschen Report."""
    from scripts.evaluate_research_report import score_source_coverage

    report = {
        "has_source_section": False,
        "source_count": 0,
        "sources_listed": 0,
        "has_summary_section": False,
    }
    score, notes = score_source_coverage(report)
    assert score <= 20, f"Source Coverage sollte niedrig sein: {score}"
    assert notes != "OK"


# ── Traceability mit deutschen Reports ─────────────────────────────────────────


def test_traceability_german_report_with_ids():
    """Traceability erkennt Quellen-IDs in deutschen Reports."""
    from scripts.evaluate_research_report import score_traceability

    report = {
        "query": "Was ist eine Fußgängerzone?",
        "source_count": 3,
        "source_ids": 3,
        "model_requested": "qwen3.5:9b",
        "model_used": "qwen3.5:9b",
        "model_fallback": False,
        "has_metadata_section": True,
        "has_limitations_section": True,
        "degraded": False,
        "sources_listed": 3,
        "model_mentioned": True,
    }
    score, notes = score_traceability(report)
    assert score >= 85, f"Traceability zu niedrig: {score} ({notes})"


def test_traceability_german_report_degraded():
    """Traceability erkennt Degraded-Mode im deutschen Report."""
    from scripts.evaluate_research_report import score_traceability

    report = {
        "query": "Was bedeutet Übergröße?",
        "source_count": 1,
        "source_ids": 1,
        "model_requested": "",
        "model_used": "",
        "model_fallback": False,
        "has_metadata_section": False,
        "has_limitations_section": False,
        "degraded": True,
        "sources_listed": 1,
        "model_mentioned": False,
    }
    score, notes = score_traceability(report)
    assert score <= 40, f"Traceability sollte niedrig sein bei degraded: {score}"
    # Degraded-Hinweis sollte in Notes sein
    assert notes != "OK"


# ── Hallucination-Risk mit deutschen Report-Texten ─────────────────────────────


def test_hallucination_risk_german_clean():
    """Hallucination-Risk: Sachlicher deutscher Report = geringes Risiko."""
    from scripts.evaluate_research_report import score_hallucination_risk

    report = {
        "summary": "Eine Fußgängerzone ist ein verkehrsberuhigter Bereich. "
        "Sie dient dem Fußverkehr und der Aufenthaltsqualität.",
        "has_source_section": True,
        "source_count": 3,
    }
    score, notes = score_hallucination_risk(report)
    assert score >= 90, f"Hallucination-Risk zu hoch: {score} ({notes})"
    assert notes == "OK"


def test_hallucination_risk_german_high():
    """Hallucination-Risk: Deutsche Risikowörter werden erkannt."""
    from scripts.evaluate_research_report import score_hallucination_risk

    report = {
        "summary": "Dies beweist garantierte Ergebnisse ohne jeden Zweifel. "
        "Alle Experten sind sich immer einig.",
        "has_source_section": False,
        "source_count": 0,
    }
    score, notes = score_hallucination_risk(report)
    assert score < 50, f"Hallucination-Risk sollte hoch sein: {score}"
    assert "Riskante Wörter" in notes


def test_hallucination_risk_german_risk_words_detected():
    """Deutsche Risikowörter (niemals, garantiert, etc.) werden gefunden."""
    from scripts.evaluate_research_report import RISK_WORDS_DE, score_hallucination_risk

    # Prüfe, dass die deutschen Risikowörter definiert sind
    assert len(RISK_WORDS_DE) >= 4, "Zu wenige deutsche Risikowörter"
    assert "niemals" in RISK_WORDS_DE
    assert "garantiert" in RISK_WORDS_DE

    report = {
        "summary": "Dies ist garantiert richtig und zweifelsfrei belegt. "
        "Niemals wurde etwas anderes bewiesen.",
        "has_source_section": True,
        "source_count": 3,
    }
    score, notes = score_hallucination_risk(report)
    assert score < 100, f"Hallucination-Risk sollte Risikowörter erkennen: {score}"
    assert "Riskante Wörter" in notes


# ── Local-First mit deutschen Reports ──────────────────────────────────────────


def test_local_first_german_report():
    """Local-First bleibt 100 für deutschen Report ohne Cloud-Referenzen."""
    from scripts.evaluate_research_report import score_local_first

    report = {"cloud_references": [], "model_mentioned": True}
    score, notes = score_local_first(report)
    assert score == 100, f"Local-First sollte 100 sein: {score} ({notes})"
    assert notes == "OK"


def test_local_first_german_report_with_cloud():
    """Local-First erkennt Cloud-Referenzen in deutschem Report."""
    from scripts.evaluate_research_report import score_local_first

    report = {"cloud_references": ["openai"], "model_mentioned": True}
    score, notes = score_local_first(report)
    assert score < 100, f"Local-First sollte <100 sein bei Cloud: {score}"
    assert "openai" in notes


# ── Full Evaluation eines deutschen Reports ────────────────────────────────────


def test_full_evaluation_german_report():
    """generate_evaluation() funktioniert für einen deutschen Report."""
    from scripts.evaluate_research_report import generate_evaluation

    with tempfile.TemporaryDirectory() as d:
        path = _make_german_report(
            "# Research Report\n\n"
            "## Metadata\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            "| Query | Was bedeutet Übergröße? |\n"
            "| SearXNG Result Count | 4 |\n"
            "| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
            "| Ollama Chat Model Used | `qwen3.5:9b` |\n"
            "| Model Fallback Used | false |\n"
            "| Degraded Mode | false |\n"
            "\n"
            "## Summary\n\n"
            "Übergröße bezeichnet Kleidung in großen Größen [S1].\n"
            "\n"
            "## Sources\n\n"
            "### [S1] Wikipedia\n\n"
            "- **URL:** https://example.com/1\n\n"
            "### [S2] Quelle 2\n\n"
            "- **URL:** https://example.com/2\n\n"
            "### [S3] Quelle 3\n\n"
            "- **URL:** https://example.com/3\n\n"
            "### [S4] Quelle 4\n\n"
            "- **URL:** https://example.com/4\n\n"
            "\n"
            "## Limitations and Warnings\n\n"
            "- Grenzen.\n",
            d,
        )
        eval_dir = os.path.join(d, "eval_output")
        eval_data = generate_evaluation(path, eval_dir)

        # Gesamtscore sollte > 0 sein
        assert eval_data["overall"] > 0

        # JSON und MD wurden erstellt
        assert os.path.exists(eval_data["json_path"])
        assert os.path.exists(eval_data["md_path"])

        # JSON enthält Scores
        import json

        with open(eval_data["json_path"]) as f:
            j = json.load(f)
            assert "scores" in j
            assert "overall" in j

        # MD enthält Überschrift
        with open(eval_data["md_path"]) as f:
            md = f.read()
            assert "Overall Score" in md

        # Query mit Umlaut wurde korrekt dokumentiert
        assert "Übergröße" in j.get("report_metadata", {}).get("query", "")


def test_full_evaluation_fussgaengerzone():
    """generate_evaluation() für Fußgängerzone-Report."""
    from scripts.evaluate_research_report import generate_evaluation

    with tempfile.TemporaryDirectory() as d:
        path = _make_german_report(
            "# Research Report\n\n"
            "## Metadata\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            "| Query | Was ist eine Fußgängerzone? |\n"
            "| SearXNG Result Count | 3 |\n"
            "| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
            "| Ollama Chat Model Used | `qwen3.5:9b` |\n"
            "| Model Fallback Used | false |\n"
            "| Degraded Mode | false |\n"
            "\n"
            "## Summary\n\n"
            "Eine Fußgängerzone ist ein verkehrsberuhigter Bereich.\n"
            "\n"
            "## Sources\n\n"
            "### [S1] Wikipedia\n\n"
            "- **URL:** https://de.wikipedia.org\n\n"
            "### [S2] Stadtplanung\n\n"
            "- **URL:** https://example.com\n\n"
            "### [S3] Verkehrslexikon\n\n"
            "- **URL:** https://example.org\n\n"
            "\n"
            "## Limitations and Warnings\n\n"
            "- Grenzen.\n",
            d,
        )
        eval_dir = os.path.join(d, "eval_output")
        eval_data = generate_evaluation(path, eval_dir)

        scores = eval_data["scores"]
        assert scores["source_coverage"] >= 50, (
            f"Source Coverage zu niedrig: {scores['source_coverage']}"
        )
        assert scores["traceability"] >= 50, (
            f"Traceability zu niedrig: {scores['traceability']}"
        )
        assert scores["hallucination_risk"] >= 90, (
            f"Hallucination zu hoch: {scores['hallucination_risk']}"
        )
        assert scores["local_first"] == 100, f"Local-First: {scores['local_first']}"


# ── Unicode Edge Cases ─────────────────────────────────────────────────────────


def test_report_with_nfd_umlauts_still_evaluated():
    """Reports mit NFD-kodierten Umlauten werden trotzdem evaluiert."""
    from scripts.evaluate_research_report import generate_evaluation

    with tempfile.TemporaryDirectory() as d:
        # Query mit NFD-kodiertem 'ü' (u + combining diaeresis)
        query_nfd = "Was bedeutet U\u0308bergro\u0308\u00dfe?"
        # In NFC wäre das: "Was bedeutet Übergröße?"

        path = _make_german_report(
            f"# Research Report\n\n"
            f"## Metadata\n\n"
            f"| Field | Value |\n"
            f"|---|---|\n"
            f"| Query | {query_nfd} |\n"
            f"| SearXNG Result Count | 2 |\n"
            f"| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
            f"| Ollama Chat Model Used | `qwen3.5:9b` |\n"
            f"| Model Fallback Used | false |\n"
            f"| Degraded Mode | false |\n"
            f"\n"
            f"## Summary\n\n"
            f"Test.\n\n"
            f"## Sources\n\n"
            f"### [S1] S1\n\n- **URL:** https://x.com\n\n"
            f"### [S2] S2\n\n- **URL:** https://y.com\n\n"
            f"## Limitations and Warnings\n\n- Grenzen.\n",
            d,
        )
        eval_dir = os.path.join(d, "eval_output")
        eval_data = generate_evaluation(path, eval_dir)

        # Sollte ohne Fehler evaluieren
        assert eval_data["overall"] > 0
        # Die Query im parse_report sollte die NFD-Version enthalten (wie geschrieben)
        # oder NFC-normalisiert sein — beides ist akzeptabel
        assert len(eval_data["report_metadata"]["query"]) > 0


# ── Evaluation bleibt stabil mit deutschen Queries ─────────────────────────────


def test_evaluation_scores_deterministic_for_german():
    """Scores sind deterministisch für identische deutsche Reports."""
    from scripts.evaluate_research_report import generate_evaluation

    report_content = (
        "# Research Report\n\n"
        "## Metadata\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        "| Query | Was ist freie Software? |\n"
        "| SearXNG Result Count | 3 |\n"
        "| Ollama Chat Model Requested | `qwen3.5:9b` |\n"
        "| Ollama Chat Model Used | `qwen3.5:9b` |\n"
        "| Model Fallback Used | false |\n"
        "| Degraded Mode | false |\n"
        "\n"
        "## Summary\n\n"
        "Freie Software ist Software, die Freiheiten garantiert.\n"
        "\n"
        "## Sources\n\n"
        "### [S1] S1\n\n- **URL:** https://fsfe.org\n\n"
        "### [S2] S2\n\n- **URL:** https://gnu.org\n\n"
        "### [S3] S3\n\n- **URL:** https://example.com\n\n"
        "\n"
        "## Limitations and Warnings\n\n- Grenzen.\n"
    )

    with tempfile.TemporaryDirectory() as d:
        subdir = os.path.join(d, "sub")
        os.makedirs(subdir, exist_ok=True)
        path1 = _make_german_report(report_content, d)
        path2 = _make_german_report(report_content, subdir)

        eval1 = generate_evaluation(path1, os.path.join(d, "eval1"))
        eval2 = generate_evaluation(path2, os.path.join(d, "eval2"))

        assert eval1["overall"] == eval2["overall"], (
            f"Scores nicht deterministisch: {eval1['overall']} vs {eval2['overall']}"
        )
        assert eval1["scores"] == eval2["scores"]
