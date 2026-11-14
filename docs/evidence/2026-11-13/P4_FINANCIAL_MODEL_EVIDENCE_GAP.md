# P4 — Límites para actualizar el modelo financiero

## Evidencia técnica nueva disponible

La ejecución local registrada en `P2_LOCAL_CONSUMPTION_RUN.md` mide el flujo
de los tres controles con 900 evaluaciones exitosas, consumo de CPU/RSS,
crecimiento de tablas PostgreSQL y solicitudes al simulador. La política
técnica Enterprise Trial también cuenta con migración y pruebas de límites de
14 días, 3 repositorios y 100 evaluaciones.

Esta evidencia permite reemplazar afirmaciones técnicas obsoletas que indiquen
que no existen pruebas de carga o cuotas de trial. No constituye una factura,
tarifa ni costo unitario de infraestructura.

## Información que continúa sin evidencia para recalcular dinero

No se modificaron valores de ingresos, costos, VAN, TIR, impuestos ni caja. No
hay base verificable para convertir los recursos locales observados a CLP,
porque faltan al menos:

1. exportación o factura del proveedor cloud correspondiente al período;
2. asignación documentada de costos compartidos e incrementales;
3. régimen tributario y tratamiento de IVA/renta/cotizaciones;
4. datos observados de adquisición, conversión, bajas, renovaciones y soporte;
5. condiciones comerciales aprobadas para precios, cobro y reembolsos.

Por lo tanto, los supuestos ilustrativos de costo Freemium/Trial deben seguir
rotulados como sensibilidades. `demo_non_billable` permanece como una función
demostrativa y no representa una suscripción cobrada, una factura ni ingreso
reconocido.

## Próximo cambio permitido

Al disponer de los insumos anteriores, el modelo debe separar explícitamente:

- cobros, ingresos devengados y obligaciones de servicio futuras;
- costos fijos, costos incrementales medidos y costos compartidos asignados;
- cohortes de clientes, bajas y renovaciones observadas;
- flujos de proyecto (FCFF) y flujos para socios (FCFE), con inversión,
  deuda, impuestos y capital de trabajo conciliados.

Hasta entonces, cualquier resultado de rentabilidad es un escenario de
sensibilidad y no una proyección validada.
