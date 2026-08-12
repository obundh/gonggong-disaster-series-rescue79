from __future__ import annotations

from fastapi.testclient import TestClient

from rescue79.app import app


def test_index_and_safety_headers() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Rescue79" in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_health_is_local_safe_model() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["local_only"] is True
    assert body["human_review_required"] is True
    assert body["automatic_dispatch_enabled"] is False


def test_review_rejects_wrong_media_type_before_inference() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/review",
        data={"expected_digit": "7"},
        files={"image": ("note.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415
    assert "PNG" in response.json()["detail"]


def test_review_rejects_cross_site_request() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/review",
        data={"expected_digit": "7"},
        files={"image": ("sample.png", b"not needed", "image/png")},
        headers={"origin": "https://attacker.example"},
    )
    assert response.status_code == 403


def test_review_rejects_large_request_before_multipart_parsing() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/review",
        content=b"x",
        headers={
            "content-type": "multipart/form-data; boundary=safe",
            "content-length": str(13 * 1024 * 1024),
        },
    )
    assert response.status_code == 413
