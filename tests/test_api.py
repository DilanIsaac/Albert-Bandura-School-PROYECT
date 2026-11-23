"""Pruebas basicas de la API Flask del colegio."""

import os
import tempfile
import unittest

import app as proyecto


class PruebasAPI(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.aplicacion = proyecto.create_app(os.path.join(self.temporal.name, "pruebas.db"))
        self.aplicacion.config["TESTING"] = True
        self.cliente = self.aplicacion.test_client()

    def tearDown(self):
        with self.aplicacion.app_context():
            proyecto.db.session.remove()
            proyecto.db.engine.dispose()
        self.temporal.cleanup()

    def agregar_representante(self):
        return self.cliente.post("/representative", json={
            "first_name": "Ana", "last_name": "Lopez",
            "identification_number": "1723456789"
        })

    def agregar_estudiante(self, representante_id):
        return self.cliente.post("/student", json={
            "representative_id": representante_id, "enrollment_number": "EST-001",
            "first_name": "Pedro", "last_name": "Lopez", "grade_level": "Primero"
        })

    def test_01_crear_representante(self):
        self.assertEqual(self.agregar_representante().status_code, 201)

    def test_02_listar_representantes(self):
        self.agregar_representante()
        self.assertEqual(len(self.cliente.get("/representatives").json), 1)

    def test_03_buscar_representante(self):
        numero = self.agregar_representante().json["id"]
        self.assertEqual(self.cliente.get(f"/representative/{numero}").json["first_name"], "Ana")

    def test_04_cedula_no_repetida(self):
        self.agregar_representante()
        self.assertEqual(self.agregar_representante().status_code, 400)

    def test_05_modificar_representante(self):
        numero = self.agregar_representante().json["id"]
        respuesta = self.cliente.put(f"/representative/{numero}", json={
            "first_name": "Ana", "last_name": "Lopez",
            "identification_number": "1723456789", "phone": "0991112222"
        })
        self.assertEqual(respuesta.json["phone"], "0991112222")

    def test_06_eliminar_representante(self):
        numero = self.agregar_representante().json["id"]
        self.cliente.delete(f"/representative/{numero}")
        self.assertEqual(self.cliente.get(f"/representative/{numero}").status_code, 404)

    def test_07_crear_estudiante(self):
        representante = self.agregar_representante().json["id"]
        self.assertEqual(self.agregar_estudiante(representante).status_code, 201)

    def test_08_llave_foranea(self):
        self.assertEqual(self.agregar_estudiante(999).status_code, 400)

    def test_09_modificar_estudiante(self):
        representante = self.agregar_representante().json["id"]
        numero = self.agregar_estudiante(representante).json["id"]
        respuesta = self.cliente.put(f"/student/{numero}", json={
            "representative_id": representante, "enrollment_number": "EST-001",
            "first_name": "Pedro", "last_name": "Lopez", "grade_level": "Segundo"
        })
        self.assertEqual(respuesta.json["grade_level"], "Segundo")

    def test_10_eliminar_estudiante(self):
        representante = self.agregar_representante().json["id"]
        numero = self.agregar_estudiante(representante).json["id"]
        self.assertEqual(self.cliente.delete(f"/student/{numero}").status_code, 200)

    def test_11_pago_y_factura(self):
        representante = self.agregar_representante().json["id"]
        estudiante = self.agregar_estudiante(representante).json["id"]
        pago = self.cliente.post("/payment", json={
            "student_id": estudiante, "billing_month": "2026-11-01",
            "amount": 60, "payment_method": "cash"
        })
        self.assertEqual(pago.status_code, 201)
        self.assertEqual(self.cliente.get("/invoices").json[0]["total"], 60)

    def test_12_actualizar_estado_pago(self):
        representante = self.agregar_representante().json["id"]
        estudiante = self.agregar_estudiante(representante).json["id"]
        pago = self.cliente.post("/payment", json={
            "student_id": estudiante, "billing_month": "2026-11-01",
            "amount": 60, "payment_method": "cash"
        }).json
        respuesta = self.cliente.put(f"/payment/{pago['id']}", json={"status": "voided"})
        self.assertEqual(respuesta.json["status"], "voided")

    def test_13_join_factura(self):
        representante = self.agregar_representante().json["id"]
        estudiante = self.agregar_estudiante(representante).json["id"]
        self.cliente.post("/payment", json={
            "student_id": estudiante, "billing_month": "2026-11-01",
            "amount": 60, "payment_method": "cash"
        })
        filas = self.cliente.get("/invoice_report").json
        self.assertEqual(filas[0]["representative_name"], "Ana")

    def test_14_gui_se_abre(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Albert Bandura School", respuesta.data)

    def test_15_gui_tiene_formularios(self):
        pagina = self.cliente.get("/").data
        for nombre in (b'form_representante', b'form_estudiante', b'form_pago',
                       b'tabla_facturas', b'/static/estilos.css'):
            self.assertIn(nombre, pagina)

    def test_16_gui_carga_archivos(self):
        self.assertEqual(self.cliente.get('/static/interfaz.js').status_code, 200)
        self.assertEqual(self.cliente.get('/static/estilos.css').status_code, 200)

    def test_17_exportar_excel(self):
        from io import BytesIO
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        self.cliente.post('/payment', json={
            'student_id': sid, 'billing_month': '2026-11-01',
            'amount': 60, 'payment_method': 'cash'
        })
        respuesta = self.cliente.get('/invoice/1/xlsx')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment', respuesta.headers['Content-Disposition'])
        with ZipFile(BytesIO(respuesta.data)) as archivo:
            self.assertIsNone(archivo.testzip())
            hoja = ET.fromstring(archivo.read('xl/worksheets/sheet1.xml'))
            texto = ''.join(hoja.itertext())
            self.assertIn('Pedro', texto)
            self.assertIn('Ana', texto)
            self.assertIn('FAC-1', texto)

    def test_18_exportar_xml(self):
        from xml.etree import ElementTree as ET
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        self.cliente.post('/payment', json={
            'student_id': sid, 'billing_month': '2026-11-01',
            'amount': 60, 'payment_method': 'cash'
        })
        respuesta = self.cliente.get('/invoice/1/xml')
        self.assertEqual(respuesta.status_code, 200)
        raiz = ET.fromstring(respuesta.data)
        self.assertEqual(raiz.findtext('invoice_number'), 'FAC-1')
        self.assertEqual(raiz.findtext('student_first_name'), 'Pedro')

    def test_19_exportacion_inexistente(self):
        self.assertEqual(self.cliente.get('/invoice/999/xlsx').status_code, 404)
        self.assertEqual(self.cliente.get('/invoice/999/xml').status_code, 404)

    def test_20_validar_campos_obligatorios(self):
        self.assertEqual(self.cliente.post('/representative', json={'first_name': 'Ana'}).status_code, 400)
        self.assertEqual(self.cliente.post('/student', json={}).status_code, 400)
        self.assertEqual(self.cliente.post('/representative', data='not json').status_code, 400)

    def test_21_validar_monto_pago(self):
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        datos = {'student_id': sid, 'billing_month': '2026-11-01', 'amount': -5, 'payment_method': 'cash'}
        self.assertEqual(self.cliente.post('/payment', json=datos).status_code, 400)
        datos['amount'] = 60
        datos['billing_month'] = '2026-11-35'
        self.assertEqual(self.cliente.post('/payment', json=datos).status_code, 400)

    def test_22_eliminar_pago_elimina_factura(self):
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        pago = self.cliente.post('/payment', json={
            'student_id': sid, 'billing_month': '2026-11-01', 'amount': 60, 'payment_method': 'cash'
        }).json
        self.assertEqual(self.cliente.delete(f'/payment/{pago["id"]}').status_code, 200)
        self.assertEqual(len(self.cliente.get('/invoices').json), 0)

    def test_23_editar_y_regenerar_factura(self):
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        pago = self.cliente.post('/payment', json={
            'student_id': sid, 'billing_month': '2026-11-01', 'amount': 60, 'payment_method': 'cash'
        }).json
        factura_id = self.cliente.get('/invoices').json[0]['id']
        self.assertEqual(self.cliente.put(f'/invoice/{factura_id}', json={'issue_date': '2026-11-23'}).status_code, 200)
        self.assertEqual(self.cliente.delete(f'/invoice/{factura_id}').status_code, 200)
        self.assertEqual(self.cliente.post('/invoice', json={'payment_id': pago['id']}).status_code, 201)
        self.assertEqual(len(self.cliente.get('/invoices').json), 1)
    def test_24_reporte_mensual(self):
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        self.cliente.post('/payment', json={'student_id': sid, 'billing_month': '2026-11-01', 'amount': 60, 'payment_method': 'cash'})
        filas = self.cliente.get('/reports/monthly').json
        self.assertEqual(filas[0]['total'], 60)
        self.assertEqual(filas[0]['payments'], 1)

    def test_25_reporte_excluye_anulados(self):
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        pago = self.cliente.post('/payment', json={'student_id': sid, 'billing_month': '2026-11-01', 'amount': 60, 'payment_method': 'cash'}).json
        self.cliente.put('/payment/' + str(pago['id']), json={'status': 'voided'})
        self.assertEqual(self.cliente.get('/reports/monthly').json, [])

    def test_26_ui_reporte_disponible(self):
        page = self.cliente.get('/').data
        self.assertIn(b'vista-reportes', page)
        self.assertIn(b'regenerar_factura', page)

    def test_27_autenticacion_si_se_configura(self):
        anterior = os.environ.get('SCHOOL_API_KEY')
        try:
            os.environ['SCHOOL_API_KEY'] = 'clave-prueba-123'
            datos = {'first_name':'Ana','last_name':'Lopez','identification_number':'1723456789'}
            self.assertEqual(self.cliente.post('/representative', json=datos).status_code, 401)
            respuesta = self.cliente.post('/representative', json=datos, headers={'X-API-Key':'clave-prueba-123'})
            self.assertEqual(respuesta.status_code, 201)
        finally:
            if anterior is None: os.environ.pop('SCHOOL_API_KEY', None)
            else: os.environ['SCHOOL_API_KEY'] = anterior

    def test_28_pago_y_factura_misma_transaccion(self):
        rid = self.agregar_representante().json['id']
        sid = self.agregar_estudiante(rid).json['id']
        pago = self.cliente.post('/payment', json={'student_id':sid,'billing_month':'2026-11-01','amount':60,'payment_method':'cash'})
        self.assertEqual(pago.status_code,201)
        self.assertEqual(len(self.cliente.get('/invoices').json),1)
        self.assertEqual(self.cliente.get('/invoices').json[0]['payment_id'],pago.json['id'])



if __name__ == "__main__":
    unittest.main()
