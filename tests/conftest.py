"""Shared pytest fixtures for Nikon Camera Controller tests."""

import pytest
from fasthtml.common import Client

from app.main import app


@pytest.fixture
def client() -> Client:
    """Create a FastHTML test client."""
    return Client(app)
