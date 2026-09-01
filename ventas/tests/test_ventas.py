import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def base_datos_temporal(monkeypatch, tmp_path):
    """Aisla cada prueba con una base de datos SQLite temporal."""
    db_file = tmp_path / "ventas_test.db"
    monkeypatch.setattr(main, "DB_PATH", str(db_file))
    main.init_db()
    yield


@pytest.fixture
def client(monkeypatch):
    """Evita llamadas de red reales al servicio de Arqueo durante las pruebas."""
    llamadas = []

    def fake_post(url, json=None, timeout=None):
        llamadas.append((url, json))

        class FakeResponse:
            status_code = 201

            def json(self_inner):
                return {"ok": True}

        return FakeResponse()

    monkeypatch.setattr(main.requests, "post", fake_post)
    test_client = TestClient(main.app)
    test_client.llamadas = llamadas
    return test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ventas"}


def test_registrar_venta_exitosa(client):
    payload = {"producto": "Paracetamol 500mg", "cantidad": 2, "precio_unitario": 5.50}
    response = client.post("/ventas", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["producto"] == "Paracetamol 500mg"
    assert data["total"] == 11.0
    assert "id" in data and "fecha" in data


def test_registrar_venta_notifica_a_arqueo_como_esperado(client):
    payload = {"producto": "Ibuprofeno 400mg", "cantidad": 1, "precio_unitario": 3.0}
    client.post("/ventas", json=payload)

    assert len(client.llamadas) == 1
    url, body = client.llamadas[0]
    assert "/arqueo/movimientos" in url
    assert body["tipo"] == "esperado"
    assert body["monto"] == 3.0


def test_registrar_venta_no_llama_directamente_a_cobro(client):
    payload = {"producto": "Alcohol en gel", "cantidad": 1, "precio_unitario": 8.0}
    client.post("/ventas", json=payload)

    urls_llamadas = [url for url, _ in client.llamadas]
    assert not any("/cobros" in url for url in urls_llamadas)


def test_registrar_venta_cantidad_invalida(client):
    payload = {"producto": "Alcohol en gel", "cantidad": 0, "precio_unitario": 8.0}
    response = client.post("/ventas", json=payload)
    assert response.status_code == 400


def test_registrar_venta_precio_invalido(client):
    payload = {"producto": "Mascarillas", "cantidad": 3, "precio_unitario": -1}
    response = client.post("/ventas", json=payload)
    assert response.status_code == 400


def test_listar_ventas(client):
    client.post("/ventas", json={"producto": "Vitamina C", "cantidad": 1, "precio_unitario": 12.0})
    client.post("/ventas", json={"producto": "Jarabe para la tos", "cantidad": 1, "precio_unitario": 9.5})

    response = client.get("/ventas")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
