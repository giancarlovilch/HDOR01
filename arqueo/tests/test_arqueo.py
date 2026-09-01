import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def base_datos_temporal(monkeypatch, tmp_path):
    db_file = tmp_path / "arqueo_test.db"
    monkeypatch.setattr(main, "DB_PATH", str(db_file))
    main.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "arqueo"}


def test_registrar_movimiento(client):
    payload = {"venta_id": 1, "monto": 11.0}
    response = client.post("/arqueo/movimientos", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["venta_id"] == 1
    assert data["monto"] == 11.0


def test_listar_movimientos(client):
    client.post("/arqueo/movimientos", json={"venta_id": 1, "monto": 11.0})
    client.post("/arqueo/movimientos", json={"venta_id": 2, "monto": 5.0})

    response = client.get("/arqueo/movimientos")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_resumen_del_dia(client):
    client.post("/arqueo/movimientos", json={"venta_id": 1, "monto": 11.0})
    client.post("/arqueo/movimientos", json={"venta_id": 2, "monto": 20.0})

    response = client.get("/arqueo/resumen")
    assert response.status_code == 200
    data = response.json()
    assert data["cantidad_movimientos"] == 2
    assert data["total_cuadre"] == 31.0
