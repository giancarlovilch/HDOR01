"""
Microservicio de Arqueo - Farmacia
Recibe los movimientos de cada venta y calcula el cuadre de caja del dia.
"""
import os
import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "arqueo.db")

app = FastAPI(title="Servicio de Arqueo de Caja - Farmacia", version="1.0.0")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


class MovimientoIn(BaseModel):
    venta_id: int
    monto: float
    fecha: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "arqueo"}


@app.post("/arqueo/movimientos", status_code=201)
def registrar_movimiento(mov: MovimientoIn):
    fecha = mov.fecha or datetime.now(timezone.utc).isoformat()
    fecha_registro = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO movimientos (venta_id, monto, fecha, fecha_registro) "
        "VALUES (?, ?, ?, ?)",
        (mov.venta_id, mov.monto, fecha, fecha_registro),
    )
    conn.commit()
    mov_id = cursor.lastrowid
    conn.close()

    return {"id": mov_id, "venta_id": mov.venta_id, "monto": mov.monto, "fecha": fecha}


@app.get("/arqueo/movimientos")
def listar_movimientos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM movimientos ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/arqueo/resumen")
def resumen_del_dia():
    """Calcula el cuadre de caja del dia actual (UTC)."""
    hoy = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM movimientos WHERE fecha LIKE ?", (f"{hoy}%",)
    ).fetchall()
    conn.close()

    total = sum(row["monto"] for row in rows)
    return {
        "fecha": hoy,
        "cantidad_movimientos": len(rows),
        "total_cuadre": round(total, 2),
    }
