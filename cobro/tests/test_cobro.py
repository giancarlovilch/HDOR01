import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def base_datos_temporal(monkeypatch, tmp_path):
    db_file = tmp_path / "cobro_test.db"
    monkeypatch.setattr(main, "DB_PATH", str(db_file))
    main.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "cobro"}


def test_registrar_cobro(client):
    payload = {"venta_id": 1, "monto": 15.5, "metodo_pago": "efectivo"}
    response = client.post("/cobros", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["venta_id"] == 1
    assert data["monto"] == 15.5
    assert data["metodo_pago"] == "efectivo"


def test_registrar_cobro_metodo_pago_por_defecto(client):
    payload = {"venta_id": 2, "monto": 20.0}
    response = client.post("/cobros", json=payload)

    assert response.status_code == 201
    assert response.json()["metodo_pago"] == "efectivo"


def test_listar_cobros(client):
    client.post("/cobros", json={"venta_id": 1, "monto": 10.0})
    client.post("/cobros", json={"venta_id": 2, "monto": 25.0})

    response = client.get("/cobros")
    assert response.status_code == 200
    assert len(response.json()) == 2
