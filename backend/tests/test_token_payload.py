from schemas import TokenPayload


def test_token_payload_coerces_tv():
    data = TokenPayload.model_validate({"sub": "admin", "uid": "1", "role": "admin", "tv": "3"})
    assert data.tv == 3
