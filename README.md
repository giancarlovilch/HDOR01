# Farmacia - Sistema de Ventas, Cobro y Arqueo (Microservicios)

Proyecto académico (TA1) que implementa un flujo CI/CD para un caso de negocio de farmacia,
compuesto por 3 microservicios en Python (FastAPI) con base de datos SQLite independiente
cada uno.

## Arquitectura

```
ventas (8000) --POST /arqueo/movimientos {tipo: "esperado"}--> arqueo (8002)
cobro  (8001) --POST /arqueo/movimientos {tipo: "cobrado"} --> arqueo (8002)
```

- **ventas**: el vendedor registra la venta (producto, cantidad, precio) y le avisa a
  `arqueo` cuánto se **espera** cobrar por esa venta.
- **cobro**: la cajera registra, de forma **independiente**, el pago que realmente recibió
  por una venta, y le avisa a `arqueo` cuánto se **cobró** en la realidad.
- **arqueo**: acumula ambos tipos de movimiento y en `/arqueo/resumen` calcula
  `diferencia = total_cobrado - total_esperado`, indicando si el día está `"cuadrado"`
  o en `"descuadre"`.

`ventas` y `cobro` no se llaman entre sí directamente — son acciones de personas distintas
(vendedor vs. cajera) que solo se reconcilian en `arqueo`, igual que en un arqueo de caja real.

Cada servicio tiene su propia base de datos SQLite (patrón *database-per-service*).

## Ejecutar localmente con Docker Compose

```bash
docker compose build
docker compose up -d
```

- Ventas: http://localhost:8000/docs
- Cobro: http://localhost:8001/docs
- Arqueo: http://localhost:8002/docs

Probar el flujo completo (venta -> cobro -> arqueo):

```bash
# 1. El vendedor registra la venta
curl -X POST http://localhost:8000/ventas \
  -H "Content-Type: application/json" \
  -d '{"producto": "Paracetamol 500mg", "cantidad": 2, "precio_unitario": 5.50}'

# 2. La cajera cobra por separado (usa el "id" devuelto arriba como venta_id)
curl -X POST http://localhost:8001/cobros \
  -H "Content-Type: application/json" \
  -d '{"venta_id": 1, "monto": 11.0}'

# 3. El arqueo compara ambos y dice si cuadra
curl http://localhost:8002/arqueo/resumen
```

También hay un script `demo.ps1` (PowerShell) que automatiza dos escenarios completos:
uno donde el cobro coincide (`"estado": "cuadrado"`) y otro donde la cajera cobra de menos
(`"estado": "descuadre"`).

```powershell
.\demo.ps1
```

## Ejecutar las pruebas de un servicio

```bash
cd ventas   # o cobro / arqueo
pip install -r requirements-dev.txt
pytest -v
```

## Pipeline CI/CD

El workflow `.github/workflows/ci-cd.yml` corre automáticamente en cada push/PR a `main`
con 3 etapas:

1. **Compilación**: instala dependencias y verifica la sintaxis de cada servicio.
2. **Pruebas automatizadas**: ejecuta `pytest` para cada microservicio.
3. **Despliegue real en contenedores Docker**: construye las 3 imágenes, levanta los
   contenedores con `docker compose`, valida los health checks y ejecuta una prueba de
   humo end-to-end (venta → cobro → arqueo) sobre contenedores reales.
