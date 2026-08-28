from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _preflight(origin: str):
    return client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )


def test_cors_allows_localhost_and_127_0_0_1_variants_for_both_frontends():
    # localhost e 127.0.0.1 sao origens diferentes pro navegador mesmo apontando pro mesmo
    # servidor - sem as duas variantes liberadas, quem abre o frontend por IP toma
    # "Disallowed CORS origin" (400) silenciosamente bem no preflight do login.
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    for origin in allowed_origins:
        response = _preflight(origin)
        assert response.status_code == 200, f"origem {origin} deveria ser aceita no CORS"
        assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_origin_fora_da_lista():
    response = _preflight("http://exemplo-malicioso.com")
    assert response.status_code == 400
    assert response.text == "Disallowed CORS origin"
