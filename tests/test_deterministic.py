# =============================================================================
# Tests: Deterministisches Research-Profil (T-015)
# =============================================================================
#
# Ausführung:
#   python3 -m pytest tests/test_deterministic.py -v
# =============================================================================

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_is_deterministic_default():
    """Default: RESEARCH_DETERMINISTIC nicht gesetzt = false."""
    from config.config import is_deterministic

    # Entferne die Variable falls gesetzt
    old = os.environ.pop("RESEARCH_DETERMINISTIC", None)
    try:
        assert is_deterministic() is False
    finally:
        if old is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old


def test_is_deterministic_true():
    """RESEARCH_DETERMINISTIC=true → true."""
    from config.config import is_deterministic

    old = os.environ.get("RESEARCH_DETERMINISTIC")
    os.environ["RESEARCH_DETERMINISTIC"] = "true"
    try:
        assert is_deterministic() is True
    finally:
        if old is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old
        else:
            del os.environ["RESEARCH_DETERMINISTIC"]


def test_is_deterministic_false():
    """RESEARCH_DETERMINISTIC=false → false."""
    from config.config import is_deterministic

    old = os.environ.get("RESEARCH_DETERMINISTIC")
    os.environ["RESEARCH_DETERMINISTIC"] = "false"
    try:
        assert is_deterministic() is False
    finally:
        if old is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old
        else:
            del os.environ["RESEARCH_DETERMINISTIC"]


def test_is_deterministic_1():
    """RESEARCH_DETERMINISTIC=1 → true."""
    from config.config import is_deterministic

    old = os.environ.get("RESEARCH_DETERMINISTIC")
    os.environ["RESEARCH_DETERMINISTIC"] = "1"
    try:
        assert is_deterministic() is True
    finally:
        if old is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old
        else:
            del os.environ["RESEARCH_DETERMINISTIC"]


def test_apply_deterministic_sets_temperature():
    """apply_deterministic_config setzt temperature=0."""
    from config.config import apply_deterministic_config

    old_det = os.environ.get("RESEARCH_DETERMINISTIC")
    os.environ["RESEARCH_DETERMINISTIC"] = "true"
    old_temp = os.environ.pop("LLM_TEMPERATURE", None)
    old_top = os.environ.pop("LLM_TOP_P", None)
    old_seed = os.environ.pop("LLM_SEED", None)

    try:
        apply_deterministic_config()
        assert os.environ["LLM_TEMPERATURE"] == "0"
        assert os.environ["LLM_TOP_P"] == "1"
        assert os.environ["LLM_SEED"] == "42"
        assert os.environ["FAST_LLM_TEMPERATURE"] == "0"
    finally:
        if old_det is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old_det
        else:
            del os.environ["RESEARCH_DETERMINISTIC"]
        for var, val in [
            ("LLM_TEMPERATURE", old_temp),
            ("LLM_TOP_P", old_top),
            ("LLM_SEED", old_seed),
        ]:
            if val is not None:
                os.environ[var] = val
            else:
                os.environ.pop(var, None)


def test_apply_deterministic_non_deterministic():
    """Wenn nicht deterministisch, ändert apply nichts."""
    from config.config import apply_deterministic_config

    old_det = os.environ.get("RESEARCH_DETERMINISTIC")
    os.environ["RESEARCH_DETERMINISTIC"] = "false"
    old_temp = os.environ.pop("LLM_TEMPERATURE", None)

    try:
        apply_deterministic_config()
        # LLM_TEMPERATURE sollte NICHT gesetzt sein
        assert "LLM_TEMPERATURE" not in os.environ
    finally:
        if old_det is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old_det
        else:
            del os.environ["RESEARCH_DETERMINISTIC"]
        if old_temp is not None:
            os.environ["LLM_TEMPERATURE"] = old_temp


def test_apply_deterministic_does_not_override():
    """apply_deterministic_config überschreibt nicht bereits gesetzte Werte."""
    from config.config import apply_deterministic_config

    old_det = os.environ.get("RESEARCH_DETERMINISTIC")
    os.environ["RESEARCH_DETERMINISTIC"] = "true"
    os.environ["LLM_TEMPERATURE"] = "0.5"  # Bereits gesetzt

    try:
        apply_deterministic_config()
        # setdefault → kein Überschreiben
        assert os.environ["LLM_TEMPERATURE"] == "0.5"
    finally:
        if old_det is not None:
            os.environ["RESEARCH_DETERMINISTIC"] = old_det
        else:
            del os.environ["RESEARCH_DETERMINISTIC"]
        os.environ.pop("LLM_TEMPERATURE", None)


def test_env_example_has_deterministic():
    """.env.example enthält RESEARCH_DETERMINISTIC."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    with open(env_path) as f:
        content = f.read()
    assert "RESEARCH_DETERMINISTIC" in content
    assert "temperature=0" in content or "reproduzierbar" in content
