from audit_risk_mapper.data_io import join_multi, parse_multi


def test_multi_value_round_trip():
    assert parse_multi("a|b|a") == ["a", "b", "a"]
    assert join_multi(["a", "b", "a", ""]) == "a|b"
