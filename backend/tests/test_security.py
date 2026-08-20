from backend.src.infra.security import issue_jwt, verify_jwt, authorize

def test_jwt_and_abac():
    tok = issue_jwt("sekhar", "plant-01", "operator")
    claims = verify_jwt(tok)
    assert claims["plant_id"] == "plant-01"
    assert authorize(claims, "operator", "plant-01")
    assert not authorize(claims, "operator", "plant-02")
