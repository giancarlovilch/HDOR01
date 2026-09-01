"""
Microservicio de Cobro - Farmacia
Recibe y registra los pagos asociados a cada venta del dia.
"""
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "cobro.db")

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

    return {
        "id": cobro_id,
        "venta_id": cobro.venta_id,
        "monto": cobro.monto,
        "metodo_pago": cobro.metodo_pago,
        "fecha": fecha,
    }


@app.get("/cobros")
def listar_cobros():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM cobros ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
