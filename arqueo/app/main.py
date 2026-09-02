"""
Microservicio de Arqueo - Farmacia
Recibe dos tipos de movimientos de forma independiente:
  - "esperado": lo que Ventas dice que se debio cobrar por cada venta.
  - "cobrado":  lo que Cobro dice que la cajera realmente recibio.

El arqueo del dia compara ambos totales y determina si hay diferencia
(descuadre) entre lo vendido y lo efectivamente cobrado.
"""
import os
import sqlite3
from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "arqueo.db")

app = FastAPI(title="Servicio de Arqueo de Caja - Farmacia", version="1.0.0")

TIPOS_VALIDOS = ("esperado", "cobrado")


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
            tipo TEXT NOT NULL CHECK (tipo IN ('esperado', 'cobrado')),
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
    tipo: Literal["esperado", "cobrado"]
    monto: float
    fecha: Optional[str] = None


@app.get("/health")
def health():
    raise Exception("Fallo simulado en el health check de Arqueo")


@app.post("/arqueo/movimientos", status_code=201)
def registrar_movimiento(mov: MovimientoIn):
    fecha = mov.fecha or datetime.now(timezone.utc).isoformat()
    fecha_registro = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO movimientos (venta_id, tipo, monto, fecha, fecha_registro) "
        "VALUES (?, ?, ?, ?, ?)",
        (mov.venta_id, mov.tipo, mov.monto, fecha, fecha_registro),
    )
    conn.commit()
    mov_id = cursor.lastrowid
    conn.close()

    return {
        "id": mov_id,
        "venta_id": mov.venta_id,
        "tipo": mov.tipo,
        "monto": mov.monto,
        "fecha": fecha,
    }


@app.get("/arqueo/movimientos")
def listar_movimientos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM movimientos ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/arqueo/resumen")
def resumen_del_dia():
    """Calcula el cuadre de caja del dia actual (UTC): compara lo esperado
    (segun Ventas) contra lo realmente cobrado (segun Cobro)."""
    hoy = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM movimientos WHERE fecha LIKE ?", (f"{hoy}%",)
    ).fetchall()
    conn.close()

    esperados = [row for row in rows if row["tipo"] == "esperado"]
    cobrados = [row for row in rows if row["tipo"] == "cobrado"]

    total_esperado = round(sum(row["monto"] for row in esperados), 2)
    total_cobrado = round(sum(row["monto"] for row in cobrados), 2)
    diferencia = round(total_cobrado - total_esperado, 2)

    return {
        "fecha": hoy,
        "cantidad_ventas_esperadas": len(esperados),
        "cantidad_cobros_realizados": len(cobrados),
        "total_esperado": total_esperado,
        "total_cobrado": total_cobrado,
        "diferencia": diferencia,
        "estado": "cuadrado" if diferencia == 0 else "descuadre",
    }
