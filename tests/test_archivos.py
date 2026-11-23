"""Pruebas de esquema SQL y Excel sin depender de Flask."""
import sqlite3
import unittest
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from factura_excel import crear_excel

CARPETA = Path(__file__).resolve().parent.parent


class PruebaArchivos(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript((CARPETA / "schema.sql").read_text(encoding="utf-8"))
        self.db.execute("INSERT INTO representative (first_name,last_name,identification_number) VALUES (?,?,?)", ("Ana", "Lopez", "1723456789"))
        self.db.execute("INSERT INTO student (representative_id,enrollment_number,first_name,last_name,grade_level) VALUES (?,?,?,?,?)", (1, "EST-001", "Pedro", "Lopez", "Primero"))
        self.db.execute("INSERT INTO payment (student_id,billing_month,payment_date,amount,payment_method) VALUES (?,?,?,?,?)", (1, "2026-11-01", "2026-11-23", 60, "cash"))
        self.db.execute("INSERT INTO invoice (payment_id,invoice_number,issue_date,subtotal,tax,total) VALUES (?,?,?,?,?,?)", (1, "FAC-1", "2026-11-23", 60, 0, 60))

    def tearDown(self):
        self.db.close()

    def factura(self):
        campos = ['id','invoice_number','issue_date','subtotal','tax','total','payment_id',
                  'payment_date','billing_month','payment_method','status','student_id',
                  'student_first_name','student_last_name','enrollment_number','grade_level',
                  'rep_first_name','rep_last_name','identification_number','phone','email']
        datos = (1, 'FAC-1', '2026-11-23', 60, 0, 60, 1, '2026-11-23', '2026-11-01',
                 'cash', 'completed', 1, 'Pedro', 'Lopez', 'EST-001', 'Primero',
                 'Ana', 'Lopez', '1723456789', '', '')
        return dict(zip(campos, datos))

    def test_01_cuatro_tablas(self):
        nombres = {t[0] for t in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'representative','student','payment','invoice'} <= nombres)

    def test_02_llaves_foraneas(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO student (representative_id,enrollment_number,first_name,last_name,grade_level) VALUES (?,?,?,?,?)", (999,'E2','Ana','Perez','Segundo'))

    def test_03_join_de_cuatro_tablas(self):
        datos = self.db.execute('''SELECT r.first_name,s.first_name,i.total FROM invoice i
            JOIN payment p ON i.payment_id=p.id JOIN student s ON p.student_id=s.id
            JOIN representative r ON s.representative_id=r.id''').fetchone()
        self.assertEqual(datos, ('Ana','Pedro',60))

    def test_04_excel_es_xlsx_valido(self):
        contenido = crear_excel(self.factura())
        with ZipFile(BytesIO(contenido)) as archivo:
            self.assertIsNone(archivo.testzip())
            ET.fromstring(archivo.read('xl/workbook.xml'))
            ET.fromstring(archivo.read('xl/styles.xml'))
            self.assertIn('xl/worksheets/sheet1.xml', archivo.namelist())

    def test_05_excel_contiene_factura_y_total(self):
        contenido = crear_excel(self.factura())
        with ZipFile(BytesIO(contenido)) as archivo:
            texto = ''.join(ET.fromstring(archivo.read('xl/worksheets/sheet1.xml')).itertext())
        for parte in ('FAC-1','Pedro','Ana','60.00','EST-001'):
            self.assertIn(parte, texto)


if __name__ == '__main__':
    unittest.main()
