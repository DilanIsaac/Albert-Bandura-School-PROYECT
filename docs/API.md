# Documentación de la API

La API usa Flask + Flask-SQLAlchemy y responde con JSON. Servidor local: `http://127.0.0.1:7002`.

| Método | Ruta | Descripción | JSON de entrada |
|---|---|---|---|
| GET | `/representatives` | Listar registros | No requiere |
| GET | `/representative/1` | Consultar por ID | No requiere |
| POST | `/representative` | Crear registro | `{"first_name":"Ana","last_name":"Lopez","identification_number":"1723456789","phone":"0991112222","email":"ana@ejemplo.com","address":"Quito"}` |
| PUT | `/representative/1` | Modificar registro | `{"first_name":"Ana","last_name":"Lopez","identification_number":"1723456789","phone":"0991112222","email":"ana@ejemplo.com","address":"Quito"}` |
| DELETE | `/representative/1` | Eliminar registro | No requiere |
| GET | `/students` | Listar registros | No requiere |
| GET | `/student/1` | Consultar por ID | No requiere |
| POST | `/student` | Crear registro | `{"representative_id":1,"enrollment_number":"EST-001","first_name":"Pedro","last_name":"Lopez","grade_level":"Primero"}` |
| PUT | `/student/1` | Modificar registro | `{"representative_id":1,"enrollment_number":"EST-001","first_name":"Pedro","last_name":"Lopez","grade_level":"Primero"}` |
| DELETE | `/student/1` | Eliminar registro | No requiere |
| GET | `/payments` | Listar registros | No requiere |
| GET | `/payment/1` | Consultar por ID | No requiere |
| POST | `/payment` | Crear registro | `{"student_id":1,"billing_month":"2026-11-01","amount":60,"payment_method":"cash"}` |
| PUT | `/payment/1` | Modificar registro | `{"status":"voided"}` |
| DELETE | `/payment/1` | Eliminar registro | No requiere |
| GET | `/invoices` | Listar registros | No requiere |
| GET | `/invoice/1` | Consultar por ID | No requiere |
| POST | `/invoice` | Crear registro | `{"payment_id":1}` |
| PUT | `/invoice/1` | Modificar registro | `{"issue_date":"2026-11-23"}` |
| DELETE | `/invoice/1` | Eliminar registro | No requiere |
| GET | `/invoice_details` | Lista detallada para la GUI | No requiere |
| GET | `/invoice_report` | JOIN de cuatro tablas | No requiere |
| GET | `/reports/monthly` | Recaudacion mensual sin pagos anulados | No requiere |
| GET | `/reports/overview` | Contadores globales | No requiere |
| GET | `/invoice/1/xlsx` | Descarga una factura Excel | No requiere |
| GET | `/invoice/1/xml` | Descarga una factura XML | No requiere |

## Códigos de respuesta

- `200`: consulta o modificación correcta.
- `201`: registro creado.
- `400`: datos inválidos o restricción de integridad.
- `401`: clave no indicada o incorrecta (solo si `SCHOOL_API_KEY` está configurada).
- `404`: elemento inexistente.

## Flujo de pago y factura

La petición `POST /payment` valida estudiante, periodo, monto y método de pago. Si los datos son correctos, crea el pago y su factura `FAC-<id>` dentro de una única transacción de SQLAlchemy. Si la transacción falla, se revierte para evitar registros parciales.

## Reportes

`GET /reports/monthly` agrupa pagos `completed` por mensualidad, cuenta registros y suma montos. Los pagos `voided` no se incluyen. `GET /invoice_report` relaciona facturas, pagos, estudiantes y representantes.

## Comprobantes

Los endpoints XLSX/XML generan archivos **internos de práctica**, no facturas tributarias oficiales del SRI.