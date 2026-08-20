import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_item():
    r = client.post("/items", json={"name": "book", "price": 10.0})
    assert r.status_code == 200
    assert r.json()["total_with_tax"] == 11.0
