# =============================================================================
# Tests — Konfiguration (conftest.py)
# =============================================================================
import importlib.util
import os
import sys

# Projekt-Root zum Import-Pfad hinzufügen
_proj_root = os.path.join(os.path.dirname(__file__), "..")
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

# ---------------------------------------------------------------------------
# Compatibility-Imports: gpt_researcher.ports / gpt_researcher.adapters
# ---------------------------------------------------------------------------
# Die Adapter/Ports liegen unter search/ports und search/adapters.
# Für Abwärtskompatibilität werden sie als gpt_researcher.* re-exportiert.
# Da gpt_researcher via pip install -e zum Submodul-Paket aufgelöst wird,
# müssen diese Module manuell in sys.modules registriert werden.
# ---------------------------------------------------------------------------

_adapter_init = os.path.join(_proj_root, "search", "adapters", "__init__.py")
_port_init = os.path.join(_proj_root, "search", "ports", "__init__.py")
_adapter_dir = os.path.join(_proj_root, "search", "adapters")
_port_dir = os.path.join(_proj_root, "search", "ports")

if os.path.isfile(_adapter_init) and "gpt_researcher.adapters" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "gpt_researcher.adapters",
        _adapter_init,
        submodule_search_locations=[_adapter_dir],
    )
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["gpt_researcher.adapters"] = _mod
        _spec.loader.exec_module(_mod)

if os.path.isfile(_port_init) and "gpt_researcher.ports" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "gpt_researcher.ports",
        _port_init,
        submodule_search_locations=[_port_dir],
    )
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["gpt_researcher.ports"] = _mod
        _spec.loader.exec_module(_mod)
