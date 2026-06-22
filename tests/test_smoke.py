def test_stack_is_reachable(anon_client):
    resp = anon_client.get("/properties")
    assert resp.status_code == 200
