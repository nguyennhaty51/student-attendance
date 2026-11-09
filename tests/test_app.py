import pytest

from app import create_app
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client


def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Student Attendance System" in response.data
