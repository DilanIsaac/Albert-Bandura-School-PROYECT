"""Albert Bandura School | Proyecto final de Bases de Datos.

API REST: Flask + Flask-SQLAlchemy (SQLite). Mantiene los endpoints
originales usados con curl, la interfaz web y las facturas XLSX/XML.
Nota: comprobantes academicos internos; no son facturas del SRI.
"""
import io
import math
import os
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from flask import Flask, jsonify, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from factura_excel import crear_excel

BASE_DIR = Path(__file__).resolve().parent
PORT = 7002
db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def sqlite_foreign_keys(connection, connection_record):
    # En SQLite se habilitan las claves foraneas por conexion.
    if connection.__class__.__module__.startswith('sqlite3'):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


class Representative(db.Model):
    __tablename__ = 'representative'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    identification_number = db.Column(db.String(20), nullable=False, unique=True)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))

    def to_dict(self):
        return {k: getattr(self, k) for k in ('id', 'first_name', 'last_name', 'identification_number', 'phone', 'email', 'address')}


class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    representative_id = db.Column(db.Integer, db.ForeignKey('representative.id'), nullable=False)
    enrollment_number = db.Column(db.String(30), unique=True, nullable=False)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    grade_level = db.Column(db.String(60), nullable=False)
    enrollment_status = db.Column(db.String(20), default='active')

    def to_dict(self):
        return {k: getattr(self, k) for k in ('id', 'representative_id', 'enrollment_number', 'first_name', 'last_name', 'grade_level', 'enrollment_status')}


class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    billing_month = db.Column(db.String(10), nullable=False)
    payment_date = db.Column(db.String(19), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default='completed')

    def to_dict(self):
        return {k: getattr(self, k) for k in ('id', 'student_id', 'billing_month', 'payment_date', 'amount', 'payment_method', 'status')}


class Invoice(db.Model):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False, unique=True)
    invoice_number = db.Column(db.String(30), nullable=False, unique=True)
    issue_date = db.Column(db.String(19), nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {k: getattr(self, k) for k in ('id', 'payment_id', 'invoice_number', 'issue_date', 'subtotal', 'tax', 'total')}


MODELOS = {'representative': Representative, 'student': Student, 'payment': Payment, 'invoice': Invoice}


def leer_json():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError('Enviar un objeto JSON valido')
    return value


def leer_texto(data, key, maximo=120, obligatorio=True):
    value = data.get(key, '')
    if not isinstance(value, str):
        raise ValueError(key + ' debe ser texto')
    value = value.strip()
    if obligatorio and not value:
        raise ValueError('Falta el campo ' + key)
    if len(value) > maximo:
        raise ValueError(key + ' es demasiado largo')
    return value


def leer_id(data, key):
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(key + ' debe ser un ID positivo')
    return value


def leer_fecha(value, key):
    if not isinstance(value, str):
        raise ValueError(key + ' debe tener formato YYYY-MM-DD')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(key + ' debe tener formato YYYY-MM-DD') from e
    if parsed.isoformat() != value:
        raise ValueError(key + ' debe tener formato YYYY-MM-DD')
    return value


def campos_representante(data):
    return dict(first_name=leer_texto(data, 'first_name', 60),
                last_name=leer_texto(data, 'last_name', 60),
                identification_number=leer_texto(data, 'identification_number', 20),
                phone=leer_texto(data, 'phone', 20, False),
                email=leer_texto(data, 'email', 120, False),
                address=leer_texto(data, 'address', 200, False))


def campos_estudiante(data):
    return dict(representative_id=leer_id(data, 'representative_id'),
                enrollment_number=leer_texto(data, 'enrollment_number', 30),
                first_name=leer_texto(data, 'first_name', 60),
                last_name=leer_texto(data, 'last_name', 60),
                grade_level=leer_texto(data, 'grade_level', 60))


def get_or_404(model, record_id):
    return db.session.get(model, record_id)


def error(error, status=400):
    return jsonify({'error': str(error)}), status


def update_fields(record, values):
    for key, value in values.items():
        setattr(record, key, value)


def transaction_error(err):
    db.session.rollback()
    return error('Violacion de integridad: registro duplicado o relacion invalida')


def invoice_detail_query():
    return (db.session.query(Invoice, Payment, Student, Representative)
            .join(Payment, Invoice.payment_id == Payment.id)
            .join(Student, Payment.student_id == Student.id)
            .join(Representative, Student.representative_id == Representative.id))


def format_detail(record):
    i, p, s, r = record
    return dict(id=i.id, invoice_number=i.invoice_number, issue_date=i.issue_date,
                subtotal=i.subtotal, tax=i.tax, total=i.total,
                payment_id=p.id, payment_date=p.payment_date, billing_month=p.billing_month,
                payment_method=p.payment_method, status=p.status,
                student_id=s.id, student_first_name=s.first_name, student_last_name=s.last_name,
                enrollment_number=s.enrollment_number, grade_level=s.grade_level,
                rep_first_name=r.first_name, rep_last_name=r.last_name,
                identification_number=r.identification_number, phone=r.phone, email=r.email)


def create_app(database_path=None):
    app = Flask(__name__)
    path = Path(database_path or os.environ.get('SCHOOL_DB_PATH') or (BASE_DIR / 'colegio.db')).resolve()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + path.as_posix()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    db.init_app(app)

    @app.before_request
    def optional_api_key():
        # Para entrega local no requiere llave. Para desplegar: set SCHOOL_API_KEY.
        # Las peticiones de solo lectura no requieren llave.
        key = os.environ.get('SCHOOL_API_KEY')
        if key and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            import hmac
            provided = request.headers.get('X-API-Key', '')
            if not hmac.compare_digest(provided, key):
                return jsonify({'error': 'Falta clave de API o es incorrecta'}), 401

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.get('/representatives')
    def representatives():
        return jsonify([r.to_dict() for r in db.session.scalars(select(Representative).order_by(Representative.id.desc()))])

    @app.get('/representative/<int:id>')
    def representative(id):
        r = get_or_404(Representative, id)
        return jsonify(r.to_dict()) if r else error('Representante no encontrado', 404)

    @app.post('/representative')
    def add_representative():
        try:
            obj = Representative(**campos_representante(leer_json()))
            db.session.add(obj); db.session.commit()
            return jsonify(obj.to_dict()), 201
        except ValueError as e: return error(e)
        except IntegrityError as e: return transaction_error(e)

    @app.put('/representative/<int:id>')
    def edit_representative(id):
        obj = get_or_404(Representative, id)
        if not obj: return error('Representante no encontrado', 404)
        try:
            update_fields(obj, campos_representante(leer_json()))
            db.session.commit(); return jsonify(obj.to_dict())
        except ValueError as e: return error(e)
        except IntegrityError as e: return transaction_error(e)

    @app.delete('/representative/<int:id>')
    def remove_representative(id):
        obj = get_or_404(Representative, id)
        if not obj: return error('Representante no encontrado', 404)
        try:
            db.session.delete(obj); db.session.commit()
            return jsonify({'message': 'Representante eliminado'})
        except IntegrityError as e: return transaction_error(e)

    @app.get('/students')
    def students():
        return jsonify([s.to_dict() for s in db.session.scalars(select(Student).order_by(Student.id.desc()))])

    @app.get('/student/<int:id>')
    def student(id):
        s = get_or_404(Student, id)
        return jsonify(s.to_dict()) if s else error('Estudiante no encontrado', 404)

    @app.post('/student')
    def add_student():
        try:
            obj = Student(**campos_estudiante(leer_json()))
            db.session.add(obj); db.session.commit()
            return jsonify(obj.to_dict()), 201
        except ValueError as e: return error(e)
        except IntegrityError as e: return transaction_error(e)

    @app.put('/student/<int:id>')
    def edit_student(id):
        obj = get_or_404(Student, id)
        if not obj: return error('Estudiante no encontrado', 404)
        try:
            update_fields(obj, campos_estudiante(leer_json()))
            db.session.commit(); return jsonify(obj.to_dict())
        except ValueError as e: return error(e)
        except IntegrityError as e: return transaction_error(e)

    @app.delete('/student/<int:id>')
    def remove_student(id):
        obj = get_or_404(Student, id)
        if not obj: return error('Estudiante no encontrado', 404)
        try:
            db.session.delete(obj); db.session.commit()
            return jsonify({'message': 'Estudiante eliminado'})
        except IntegrityError as e: return transaction_error(e)

    @app.get('/payments')
    def payments():
        return jsonify([p.to_dict() for p in db.session.scalars(select(Payment).order_by(Payment.id.desc()))])

    @app.get('/payment/<int:id>')
    def payment(id):
        p = get_or_404(Payment, id)
        return jsonify(p.to_dict()) if p else error('Pago no encontrado', 404)

    @app.post('/payment')
    def add_payment():
        try:
            d = leer_json()
            sid = leer_id(d, 'student_id')
            month = leer_fecha(d.get('billing_month'), 'billing_month')
            if not month.endswith('-01'): raise ValueError('billing_month debe ser primer dia del mes')
            amount = d.get('amount')
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                raise ValueError('amount debe ser numerico')
            amount = round(float(amount), 2)
            if not math.isfinite(amount) or amount <= 0 or amount > 999999:
                raise ValueError('El monto debe ser positivo')
            method = leer_texto(d, 'payment_method', 30)
            if method not in ('cash', 'transfer', 'card'):
                raise ValueError('Metodo: cash, transfer o card')
            if not get_or_404(Student, sid): return error('Estudiante no encontrado', 404)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            p = Payment(student_id=sid, billing_month=month, payment_date=now,
                        amount=amount, payment_method=method, status='completed')
            db.session.add(p); db.session.flush()
            # La factura se genera en la misma transaccion que el pago.
            i = Invoice(payment_id=p.id, invoice_number='FAC-' + str(p.id),
                        issue_date=now, subtotal=amount, tax=0, total=amount)
            db.session.add(i); db.session.commit()
            return jsonify(p.to_dict()), 201
        except ValueError as e: db.session.rollback(); return error(e)
        except IntegrityError as e: return transaction_error(e)

    @app.put('/payment/<int:id>')
    def edit_payment(id):
        p = get_or_404(Payment, id)
        if not p: return error('Pago no encontrado', 404)
        try:
            status = leer_json().get('status')
            if status not in ('completed', 'voided'): raise ValueError('Estado: completed o voided')
            p.status = status; db.session.commit()
            return jsonify(p.to_dict())
        except ValueError as e: return error(e)

    @app.delete('/payment/<int:id>')
    def remove_payment(id):
        p = get_or_404(Payment, id)
        if not p: return error('Pago no encontrado', 404)
        # Solo para ejercicio CRUD. En produccion conviene anular y conservar historial.
        inv = db.session.scalar(select(Invoice).where(Invoice.payment_id == id))
        if inv:
            db.session.delete(inv)
            db.session.flush()
        db.session.delete(p); db.session.commit()
        return jsonify({'message': 'Pago y factura eliminados'})

    @app.get('/invoices')
    def invoices():
        return jsonify([i.to_dict() for i in db.session.scalars(select(Invoice).order_by(Invoice.id.desc()))])

    @app.get('/invoice/<int:id>')
    def invoice(id):
        i = get_or_404(Invoice, id)
        return jsonify(i.to_dict()) if i else error('Factura no encontrada', 404)

    @app.post('/invoice')
    def regenerate_invoice():
        try:
            payment_id = leer_id(leer_json(), 'payment_id')
            p = get_or_404(Payment, payment_id)
            if not p: return error('Pago no encontrado', 404)
            if db.session.scalar(select(Invoice).where(Invoice.payment_id == payment_id)):
                return error('Este pago ya tiene factura')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            obj = Invoice(payment_id=payment_id, invoice_number='FAC-' + str(payment_id),
                          issue_date=now, subtotal=p.amount, tax=0, total=p.amount)
            db.session.add(obj); db.session.commit(); return jsonify(obj.to_dict()), 201
        except ValueError as e: return error(e)
        except IntegrityError as e: return transaction_error(e)

    @app.put('/invoice/<int:id>')
    def edit_invoice(id):
        i = get_or_404(Invoice, id)
        if not i: return error('Factura no encontrada', 404)
        try:
            i.issue_date = leer_fecha(leer_json().get('issue_date'), 'issue_date')
            db.session.commit(); return jsonify(i.to_dict())
        except ValueError as e: return error(e)

    @app.delete('/invoice/<int:id>')
    def delete_invoice(id):
        i = get_or_404(Invoice, id)
        if not i: return error('Factura no encontrada', 404)
        db.session.delete(i); db.session.commit()
        return jsonify({'message': 'Factura eliminada; puede regenerarse desde el pago'})

    @app.get('/invoice_details')
    def invoice_details():
        return jsonify([format_detail(x) for x in invoice_detail_query().order_by(Invoice.id.desc()).all()])

    @app.get('/invoice_report')
    def invoice_report():
        return jsonify([dict(invoice_number=i.invoice_number, total=i.total,
                             student_name=s.first_name, representative_name=r.first_name)
                        for i, p, s, r in invoice_detail_query().order_by(Invoice.id).all()])

    @app.get('/reports/monthly')
    def monthly_report():
        # Anulados se excluyen de recaudacion, pero no del historial de movimientos.
        rows = (db.session.query(Payment.billing_month, func.count(Payment.id), func.sum(Payment.amount))
                .filter(Payment.status == 'completed').group_by(Payment.billing_month)
                .order_by(Payment.billing_month.desc()).all())
        return jsonify([{'month': month, 'payments': count, 'total': round(float(total or 0), 2)}
                        for month, count, total in rows])

    @app.get('/reports/overview')
    def overview():
        return jsonify({'representatives': db.session.scalar(select(func.count()).select_from(Representative)),
                        'students': db.session.scalar(select(func.count()).select_from(Student)),
                        'payments': db.session.scalar(select(func.count()).select_from(Payment)),
                        'invoices': db.session.scalar(select(func.count()).select_from(Invoice))})

    def detail_for(id):
        row = invoice_detail_query().filter(Invoice.id == id).first()
        return format_detail(row) if row else None

    @app.get('/invoice/<int:id>/xlsx')
    def download_xlsx(id):
        detail = detail_for(id)
        if detail is None: return error('Factura no encontrada', 404)
        content = crear_excel(detail)
        return send_file(io.BytesIO(content), as_attachment=True,
                         download_name=detail['invoice_number'] + '.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    @app.get('/invoice/<int:id>/xml')
    def download_xml(id):
        detail = detail_for(id)
        if detail is None: return error('Factura no encontrada', 404)
        root = ET.Element('comprobante_interno', version='1.0')
        ET.SubElement(root, 'institucion').text = 'Albert Bandura School'
        ET.SubElement(root, 'advertencia').text = 'Documento interno; no es factura autorizada por el SRI'
        for field, value in detail.items():
            ET.SubElement(root, field).text = str(value if value is not None else '')
        return send_file(io.BytesIO(ET.tostring(root, encoding='utf-8', xml_declaration=True)),
                         as_attachment=True, download_name=detail['invoice_number'] + '.xml',
                         mimetype='application/xml')

    @app.get('/api/help')
    def api_help():
        return jsonify({'title': 'Albert Bandura School API',
                        'documentation': '/static/api_endpoints.json',
                        'examples': 'docs/Albert_Bandura_Postman.json'})

    # La tabla se crea si no existe; una DB previa no se elimina ni reinicia.
    with app.app_context():
        db.create_all()
    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=PORT)
