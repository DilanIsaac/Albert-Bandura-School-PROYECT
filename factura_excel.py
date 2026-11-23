"""Crea un .xlsx sencillo usando solo bibliotecas incluidas en Python.

Un archivo XLSX es un conjunto de archivos XML dentro de un ZIP.
No se necesita instalar openpyxl ni otros paquetes para esta exportacion.
"""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape


def crear_excel(factura):
    filas = []

    def celda(letra, fila, valor, estilo=0, numerico=False):
        if numerico:
            return f'<c r="{letra}{fila}" s="{estilo}"><v>{float(valor):.2f}</v></c>'
        texto = escape(str(valor if valor is not None else ""))
        return (f'<c r="{letra}{fila}" s="{estilo}" t="inlineStr">'
                f'<is><t>{texto}</t></is></c>')

    def fila(numero, elementos):
        filas.append(f'<row r="{numero}">' + ''.join(elementos) + '</row>')

    fila(1, [celda("A", 1, "ALBERT BANDURA SCHOOL", 2)])
    fila(2, [celda("A", 2, "COMPROBANTE INTERNO DE PAGO", 1)])
    fila(4, [celda("A", 4, "Factura N.", 1), celda("B", 4, factura["invoice_number"])])
    fila(5, [celda("A", 5, "Fecha de emision", 1), celda("B", 5, factura["issue_date"])])
    fila(7, [celda("A", 7, "REPRESENTANTE", 1)])
    fila(8, [celda("A", 8, "Nombre"), celda("B", 8, factura["rep_first_name"] + " " + factura["rep_last_name"])])
    fila(9, [celda("A", 9, "Identificacion"), celda("B", 9, factura["identification_number"])])
    fila(11, [celda("A", 11, "ESTUDIANTE", 1)])
    fila(12, [celda("A", 12, "Nombre"), celda("B", 12, factura["student_first_name"] + " " + factura["student_last_name"])])
    fila(13, [celda("A", 13, "Matricula"), celda("B", 13, factura["enrollment_number"])])
    fila(14, [celda("A", 14, "Curso"), celda("B", 14, factura["grade_level"])])
    fila(16, [celda("A", 16, "DETALLE DE PAGO", 1)])
    fila(17, [celda("A", 17, "Periodo"), celda("B", 17, factura["billing_month"])])
    fila(18, [celda("A", 18, "Fecha de pago"), celda("B", 18, factura["payment_date"])])
    fila(19, [celda("A", 19, "Metodo"), celda("B", 19, factura["payment_method"])])
    fila(20, [celda("A", 20, "Estado"), celda("B", 20, factura["status"])])
    fila(22, [celda("A", 22, "Concepto", 1), celda("D", 22, "Valor (USD)", 1)])
    fila(23, [celda("A", 23, "Pension mensual"), celda("D", 23, factura["subtotal"], 3, True)])
    fila(25, [celda("C", 25, "Subtotal", 1), celda("D", 25, factura["subtotal"], 3, True)])
    fila(26, [celda("C", 26, "Impuestos", 1), celda("D", 26, factura["tax"], 3, True)])
    fila(27, [celda("C", 27, "TOTAL", 1), celda("D", 27, factura["total"], 4, True)])
    fila(30, [celda("A", 30, "Documento interno de demostracion. No sustituye una factura electronica autorizada por el SRI.", 5)])

    hoja = ('<?xml version="1.0" encoding="utf-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
            '<cols><col min="1" max="1" width="23" customWidth="1"/>'
            '<col min="2" max="2" width="38" customWidth="1"/>'
            '<col min="3" max="3" width="17" customWidth="1"/>'
            '<col min="4" max="4" width="19" customWidth="1"/></cols>'
            '<sheetData>' + ''.join(filas) + '</sheetData>'
            '<mergeCells count="4"><mergeCell ref="A1:D1"/><mergeCell ref="A2:D2"/>'
            '<mergeCell ref="A30:D30"/><mergeCell ref="A23:C23"/></mergeCells>'
            '<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>'
            '</worksheet>')
    estilos = '''<?xml version="1.0" encoding="utf-8"?>
    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <numFmts count="1"><numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00"/></numFmts>
    <fonts count="3"><font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FF294C54"/><name val="Calibri"/></font>
    <font><b/><sz val="16"/><color rgb="FF294C54"/><name val="Calibri"/></font></fonts>
    <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
    <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
    <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
    <cellXfs count="6"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="164" fontId="1" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
    </styleSheet>'''
    libro = '''<?xml version="1.0" encoding="utf-8"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets><sheet name="Factura" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    relaciones_libro = '''<?xml version="1.0" encoding="utf-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    </Relationships>'''
    raiz_rels = '''<?xml version="1.0" encoding="utf-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
    </Relationships>'''
    content_types = '''<?xml version="1.0" encoding="utf-8"?>
    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
    <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
    </Types>'''
    salida = BytesIO()
    with ZipFile(salida, "w", ZIP_DEFLATED) as archivo:
        for nombre, contenido in {
            "[Content_Types].xml": content_types,
            "_rels/.rels": raiz_rels,
            "xl/workbook.xml": libro,
            "xl/_rels/workbook.xml.rels": relaciones_libro,
            "xl/styles.xml": estilos,
            "xl/worksheets/sheet1.xml": hoja,
        }.items():
            archivo.writestr(nombre, contenido)
    return salida.getvalue()
