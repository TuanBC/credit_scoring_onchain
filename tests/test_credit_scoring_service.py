from services.credit_scoring_service import CreditScoringService


def test_extract_features_empty():
    service = CreditScoringService()
    features = service.extract_features([], "0xabc")
    assert features == {}


def test_extract_features_minimal():
    service = CreditScoringService()
    txs = [
        {
            "timeStamp": 1609459200,  # Jan 1, 2021
            "value": 1000000000000000000,
            "from": "0xabc",
            "to": "0xdef",
            "input": "",
            "isError": 0,
        }
    ]
    features = service.extract_features(txs, "0xabc")
    assert features["total_transactions"] == 1
    assert features["total_eth_sent"] == 1.0
    assert features["total_eth_received"] == 0.0


def test_calculate_credit_score_empty():
    service = CreditScoringService()
    score = service.calculate_credit_score({})
    assert score == 0.0


def test_calculate_scorecard_credit_score_basic():
    service = CreditScoringService()
    features = {
        "account_age_days": 600,
        "avg_tx_value": 0.02,
        "tx_count_6m": 5,
        "unique_counterparties": 10,
        "contract_interactions": 3,
        "largest_outgoing_tx": 50,
        "months_with_tx": 20,
        "tx_value_skewness": 10,
        "total_transactions": 100,
    }
    score = service.calculate_scorecard_credit_score(features)
    assert isinstance(score, float)
    assert score > 0
