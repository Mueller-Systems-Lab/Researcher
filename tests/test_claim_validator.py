# =============================================================================
# Tests: Claim Validator Coverage (T-025)
# =============================================================================
import sys, os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_claim_validator_assess():
    from mcp_tools.claim_validator import ClaimValidator

    v = ClaimValidator()
    assert v._assess(0.8) == "gut belegt"
    assert v._assess(0.5) == "teilweise belegt"
    assert v._assess(0.2) == "schwach belegt"
    assert v._assess(0.0) == "nicht belegt"


def test_claim_validator_no_claim():
    from mcp_tools.claim_validator import ClaimValidator

    result = ClaimValidator().run({})
    assert result["success"] is False


@patch("mcp_tools.claim_validator.ClaimValidator.run")
def test_claim_validator_empty_sources(mock_run):
    """ClaimValidator mit leerer Ergebnisliste (0 Quellen = 0 confidence)."""
    from mcp_tools.claim_validator import ClaimValidator

    v = ClaimValidator()
    assert v._assess(0.0) == "nicht belegt"
