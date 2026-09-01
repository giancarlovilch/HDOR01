# Demo del flujo Vendedor (Ventas) -> Cajera (Cobro) -> Arqueo
# Requiere que los 3 contenedores esten corriendo: docker compose up -d
#
# Muestra 2 escenarios:
#   1) Una venta cuyo cobro coincide exactamente -> arqueo "cuadrado"
#   2) Una venta cuyo cobro NO coincide (error de caja) -> arqueo "descuadre"

function Show-Titulo($texto) {
    Write-Host ""
    Write-Host "===== $texto =====" -ForegroundColor Cyan
}

function Show-Resumen {
    Write-Host "Resumen de arqueo actual:" -ForegroundColor Yellow
    Invoke-RestMethod -Uri "http://localhost:8002/arqueo/resumen" | ConvertTo-Json
}

Show-Titulo "Escenario 1: el vendedor registra una venta"

$venta1 = @{ producto = "Paracetamol 500mg"; cantidad = 2; precio_unitario = 5.50 } | ConvertTo-Json
$resultadoVenta1 = Invoke-RestMethod -Uri "http://localhost:8000/ventas" -Method Post -ContentType "application/json" -Body $venta1
Write-Host "Venta registrada (monto esperado: $($resultadoVenta1.total)):" -ForegroundColor Green
$resultadoVenta1 | ConvertTo-Json
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "Arqueo justo despues de la venta (aun no la cobraron -> debe salir 'descuadre'):" -ForegroundColor Yellow
Show-Resumen

Write-Host ""
Write-Host "Ahora la cajera cobra el monto EXACTO esperado ($($resultadoVenta1.total)):" -ForegroundColor Green
$cobro1 = @{ venta_id = $resultadoVenta1.id; monto = $resultadoVenta1.total } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/cobros" -Method Post -ContentType "application/json" -Body $cobro1 | ConvertTo-Json
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "Arqueo despues del cobro correcto (debe salir 'cuadrado'):" -ForegroundColor Yellow
Show-Resumen

Show-Titulo "Escenario 2: la cajera comete un error de cobro"

$venta2 = @{ producto = "Ibuprofeno 400mg"; cantidad = 2; precio_unitario = 10.0 } | ConvertTo-Json
$resultadoVenta2 = Invoke-RestMethod -Uri "http://localhost:8000/ventas" -Method Post -ContentType "application/json" -Body $venta2
Write-Host "Venta registrada (monto esperado: $($resultadoVenta2.total)):" -ForegroundColor Green
$resultadoVenta2 | ConvertTo-Json
Start-Sleep -Seconds 1

$montoConError = $resultadoVenta2.total - 5.0
Write-Host ""
Write-Host "La cajera cobra por error solo $montoConError en vez de $($resultadoVenta2.total):" -ForegroundColor Red
$cobro2 = @{ venta_id = $resultadoVenta2.id; monto = $montoConError } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/cobros" -Method Post -ContentType "application/json" -Body $cobro2 | ConvertTo-Json
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "Arqueo final del dia (debe mostrar 'descuadre' con diferencia -5.0):" -ForegroundColor Yellow
Show-Resumen

Show-Titulo "Fin de la demo"
