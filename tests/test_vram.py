# =============================================================================
# Tests: VRAM-Optimierung
# =============================================================================
# Testet die VRAM-Konfiguration und das Monitoring-Script.
#
# Ausführung:
#   python3 -m pytest tests/test_vram.py -v
# =============================================================================

import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_vram_script_exists():
    """VRAM: Monitoring-Script existiert."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "check-vram.sh"
    )
    assert os.path.exists(script_path), "check-vram.sh fehlt"
    assert os.access(script_path, os.X_OK), "check-vram.sh muss ausführbar sein"


def test_vram_script_help():
    """VRAM: Script gibt Hilfe aus."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "check-vram.sh"
    )
    result = subprocess.run(
        [script_path, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "check-vram.sh" in result.stdout


def test_vram_params_in_modelfile():
    """VRAM: Modelfile enthält num_ctx=4096."""
    modelfile_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "Modelfile.qwen3.5-9b-uncensored-hauhaucs-aggressive",
    )
    assert os.path.exists(modelfile_path)

    with open(modelfile_path) as f:
        content = f.read()

    assert "num_ctx" in content, "num_ctx muss in Modelfile gesetzt sein"
    assert "4096" in content, "num_ctx=4096 erwartet"


def test_vram_params_in_serve_script():
    """VRAM: serve_qwen3.5_uncensored.sh enthält VRAM-Optimierungen."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "serve_qwen3.5_uncensored.sh"
    )
    assert os.path.exists(script_path)

    with open(script_path) as f:
        content = f.read()

    assert "-c 4096" in content, "Kontextfenster 4096 erwartet"
    assert "-np 1" in content, "Single sequence erwartet"


def test_vram_env_params():
    """VRAM: .env.example enthält VRAM-Parameter."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.exists(env_path)

    with open(env_path) as f:
        content = f.read()

    assert "MAX_CONCURRENT_REQUESTS=1" in content
    assert "OLLAMA_NUM_PARALLEL=1" in content


def test_vram_docs_exist():
    """VRAM: Dokumentation existiert."""
    doc_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "vram-optimization.md"
    )
    assert os.path.exists(doc_path), "VRAM-Dokumentation fehlt"
