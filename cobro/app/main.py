"""
Microservicio de Cobro - Farmacia
Recibe y registra los pagos que la cajera cobra por cada venta.
Este registro es independiente del que hace Ventas: representa lo que
realmente entro a caja, y puede diferir de lo que Ventas esperaba cobrar.
"""
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cobro")

DB_PATH = os.getenv("DB_PATH", "cobro.db")
ARQUEO_URL = os.getenv("ARQUEO_URL", "http://localhost:8002")

app = FastAPI(title="Servicio de Cobro - Farmacia", version="1.0.0")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cobros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            monto REAL NOT NULL,
            metodo_pago TEXT NOT NULL,
            fecha TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


class CobroIn(BaseModel):
    venta_id: int
    monto: float
    fecha: Optional[str] = None
    metodo_pago: str = "efectivo"


@app.get("/health")
def health():
    return {"status": "ok", "service": "cobro"}


@app.post("/cobros", status_code=201)
def registrar_cobro(cobro: CobroIn):
    fecha = cobro.fecha or datetime.now(timezone.utc).isoformat()
    fecha_registro = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO cobros (venta_id, monto, metodo_pago, fecha, fecha_registro) "
        "VALUES (?, ?, ?, ?, ?)",
        (cobro.venta_id, cobro.monto, cobro.metodo_pago, fecha, fecha_registro),
    )
    conn.commit()
    cobro_id = cursor.lastrowid
    conn.close()

    notificar_arqueo(cobro.venta_id, cobro.monto, fecha)

    return {
        "id": cobro_id,
        "venta_id": cobro.venta_id,
        "monto": cobro.monto,
        "metodo_pago": cobro.metodo_pago,
        "fecha": fecha,
    }


def notificar_arqueo(venta_id: int, monto: float, fecha: str) -> None:
    """Informa a Arqueo cuanto se cobro realmente para esta venta."""
    payload = {
        "venta_id": venta_id,
        "tipo": "cobrado",
        "monto": monto,
        "fecha": fecha,
    }

    try:
        requests.post(f"{ARQUEO_URL}/arqueo/movimientos", json=payload, timeout=5)
    except requests.RequestException as exc:
        logger.warning("No se pudo notificar al servicio de Arqueo: %s", exc)


@app.get("/cobros")
def listar_cobros():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM cobros ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
