"""
Microservicio de Ventas - Farmacia
Registra las ventas del dia (producto, cantidad, precio) y notifica
al microservicio de Cobro y al microservicio de Arqueo.
"""
import logging
import os
import sqlite3
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ventas")

DB_PATH = os.getenv("DB_PATH", "ventas.db")
ARQUEO_URL = os.getenv("ARQUEO_URL", "http://localhost:8002")

app = FastAPI(title="Servicio de Ventas - Farmacia", version="1.0.0")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            total REAL NOT NULL,
            fecha TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


class VentaIn(BaseModel):
    producto: str
    cantidad: int
    precio_unitario: float


class VentaOut(VentaIn):
    id: int
    total: float
    fecha: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "ventas"}


@app.post("/ventas", response_model=VentaOut, status_code=201)
def registrar_venta(venta: VentaIn):
    if venta.cantidad <= 0 or venta.precio_unitario <= 0:
        raise HTTPException(
            status_code=400,
            detail="cantidad y precio_unitario deben ser mayores a 0",
        )

    total = round(venta.cantidad * venta.precio_unitario, 2)
    fecha = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO ventas (producto, cantidad, precio_unitario, total, fecha) "
        "VALUES (?, ?, ?, ?, ?)",
        (venta.producto, venta.cantidad, venta.precio_unitario, total, fecha),
    )
    conn.commit()
    venta_id = cursor.lastrowid
    conn.close()

    notificar_arqueo(venta_id, total, fecha)

    return VentaOut(id=venta_id, total=total, fecha=fecha, **venta.model_dump())


def notificar_arqueo(venta_id: int, total: float, fecha: str) -> None:
    """Informa a Arqueo cuanto se esperaba cobrar por esta venta.

    Ventas NO le avisa a Cobro directamente: el registro del pago real
    lo hace la cajera de forma independiente en el microservicio Cobro.
    Si Arqueo no responde, la venta ya quedo registrada localmente: se
    registra el error pero no se revierte la venta.
    """
    payload = {
        "venta_id": venta_id,
        "tipo": "esperado",
        "monto": total,
        "fecha": fecha,
    }

    try:
        requests.post(f"{ARQUEO_URL}/arqueo/movimientos", json=payload, timeout=5)
    except requests.RequestException as exc:
        logger.warning("No se pudo notificar al servicio de Arqueo: %s", exc)


@app.get("/ventas")
def listar_ventas():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ventas ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
