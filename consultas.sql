-- Ejemplos de SQL usados dentro del proyecto.

-- Ver los representantes:
SELECT * FROM representative;

-- Buscar por cedula:
SELECT * FROM representative WHERE identification_number = '1723456789';

-- Ver estudiantes de un representante:
SELECT * FROM student WHERE representative_id = 1;

-- Listar pagos de un estudiante:
SELECT * FROM payment WHERE student_id = 1;

-- Ver la factura de un pago:
SELECT * FROM invoice WHERE payment_id = 1;

-- Consultar estudiante, representante y total de factura (JOIN):
SELECT student.first_name AS estudiante,
       representative.first_name AS representante,
       invoice.total
FROM invoice
JOIN payment ON invoice.payment_id = payment.id
JOIN student ON payment.student_id = student.id
JOIN representative ON student.representative_id = representative.id;
