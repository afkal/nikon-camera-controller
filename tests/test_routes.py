"""Tests for FastHTML routes."""


def test_homepage_returns_200(client):
    """GET / should return 200 with the main page."""
    response = client.get("/")
    assert response.status_code == 200


def test_homepage_contains_title(client):
    """GET / should contain the application title."""
    response = client.get("/")
    assert "Nikon Camera Controller" in response.text


def test_homepage_contains_layout_elements(client):
    """GET / should contain the main layout structure."""
    response = client.get("/")
    html = response.text
    assert "app-shell" in html
    assert "app-header" in html
    assert "sidebar" in html
    assert "content-area" in html


def test_homepage_contains_panels(client):
    """GET / should contain all expected panels."""
    response = client.get("/")
    html = response.text
    assert "preview-panel" in html
    assert "histogram-display" in html
    assert "metrics-display" in html
