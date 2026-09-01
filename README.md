# Farmacia - Sistema de Ventas, Cobro y Arqueo (Microservicios)

Proyecto académico (TA1) que implementa un flujo CI/CD para un caso de negocio de farmacia,
compuesto por 3 microservicios en Python (FastAPI) con base de datos SQLite independiente
cada uno.

## Arquitectura

```
ventas (8000) --POST--> cobro (8001)
      |
      +--------POST--> arqueo (8002)
```

- **ventas**: registra la venta (producto, cantidad, precio) y notifica a `cobro` y `arqueo`.
- **cobro**: registra el pago asociado a cada venta.
- **arqueo**: acumula los movimientos del día y expone el cuadre de caja (`/arqueo/resumen`).

Cada servicio tiene su propia base de datos SQLite (patrón *database-per-service*).

## Ejecutar localmente con Docker Compose

```bash
docker compose build
docker compose up -d
```

- Ventas: http://localhost:8000/docs
- Cobro: http://localhost:8001/docs
- Arqueo: http://localhost:8002/docs

Probar el flujo completo:

```bash
curl -X POST http://localhost:8000/ventas \
  -H "Content-Type: application/json" \
  -d '{"producto": "Paracetamol 500mg", "cantidad": 2, "precio_unitario": 5.50}'

curl http://localhost:8001/cobros
curl http://localhost:8002/arqueo/resumen
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
