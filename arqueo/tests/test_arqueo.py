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


def test_registrar_movimiento_esperado(client):
    payload = {"venta_id": 1, "tipo": "esperado", "monto": 11.0}
    response = client.post("/arqueo/movimientos", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["tipo"] == "esperado"
    assert data["monto"] == 11.0


def test_registrar_movimiento_tipo_invalido(client):
    payload = {"venta_id": 1, "tipo": "otro", "monto": 11.0}
    response = client.post("/arqueo/movimientos", json=payload)
    assert response.status_code == 422


def test_listar_movimientos(client):
    client.post("/arqueo/movimientos", json={"venta_id": 1, "tipo": "esperado", "monto": 11.0})
    client.post("/arqueo/movimientos", json={"venta_id": 1, "tipo": "cobrado", "monto": 11.0})

    response = client.get("/arqueo/movimientos")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_resumen_cuadrado_cuando_esperado_igual_a_cobrado(client):
    client.post("/arqueo/movimientos", json={"venta_id": 1, "tipo": "esperado", "monto": 11.0})
    client.post("/arqueo/movimientos", json={"venta_id": 2, "tipo": "esperado", "monto": 20.0})
    client.post("/arqueo/movimientos", json={"venta_id": 1, "tipo": "cobrado", "monto": 11.0})
    client.post("/arqueo/movimientos", json={"venta_id": 2, "tipo": "cobrado", "monto": 20.0})

    response = client.get("/arqueo/resumen")
    assert response.status_code == 200
    data = response.json()
    assert data["total_esperado"] == 31.0
    assert data["total_cobrado"] == 31.0
    assert data["diferencia"] == 0
    assert data["estado"] == "cuadrado"


def test_resumen_detecta_descuadre_cuando_se_cobra_de_menos(client):
    client.post("/arqueo/movimientos", json={"venta_id": 1, "tipo": "esperado", "monto": 11.0})
    # La cajera solo cobro 9.0 en vez de 11.0 (error o descuento no autorizado)
    client.post("/arqueo/movimientos", json={"venta_id": 1, "tipo": "cobrado", "monto": 9.0})

    response = client.get("/arqueo/resumen")
    data = response.json()
    assert data["total_esperado"] == 11.0
    assert data["total_cobrado"] == 9.0
    assert data["diferencia"] == -2.0
    assert data["estado"] == "descuadre"


def test_resumen_sin_movimientos(client):
    response = client.get("/arqueo/resumen")
    data = response.json()
    assert data["total_esperado"] == 0
    assert data["total_cobrado"] == 0
    assert data["diferencia"] == 0
    assert data["estado"] == "cuadrado"
