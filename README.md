# Albert Bandura School - Final Project

Sistema academico de gestion de representantes, estudiantes, mensualidades y facturas.

**Tecnologias:** Python, Flask, Flask-SQLAlchemy, SQLite, HTML, CSS y JavaScript.

## Ejecutar desde Anaconda Prompt (Windows)

1. Descomprimir el ZIP y entrar en la carpeta que contiene `app.py`.
2. Ejecutar:

```bat
python -m pip install -r requirements.txt
python app.py
```

3. Abrir http://127.0.0.1:7002/ en el navegador.
4. La base de datos `colegio.db` se crea automaticamente si no existe.

**Si ya tenias datos:** antes de iniciar, haz una copia del viejo `colegio.db` y pega una copia en esta carpeta. `db.create_all()` no borra las tablas existentes. **Haz respaldo antes de migrar.**

## Flujo para la demostracion

1. Registrar representante (ej.: Ana Lopez).
2. Registrar estudiante y asignar el representante.
3. Registrar una mensualidad en Pagos.
4. En Facturas, descargar el archivo `.xlsx` o `.xml`.
5. En Reportes, observar la recaudacion mensual y descargar CSV.
6. Mostrar edicion, eliminacion y anulacion de registros.

## API y pruebas

- Endpoints documentados en `docs/API.md` y en `static/api_endpoints.json`.
- Coleccion importable en Postman: `docs/Albert_Bandura_Postman.json`.
- Ejecutar pruebas automaticas:

```bat
python -m unittest discover -s tests -v
```

Las pruebas deben ejecutarse en el equipo del estudiante; el equipo de generacion no tenia Flask instalado y no se deben reportar como aprobadas sin ejecutarlas.

## Proteccion de escritura opcional

Por defecto la app se ejecuta **solo en localhost** para demostracion academica. Para requerir una clave en las solicitudes POST/PUT/DELETE:

```bat
set SCHOOL_API_KEY=una-clave-larga-diferente
python app.py
```

La GUI permite introducirla mediante el boton `Clave API` (se guarda solo durante la sesion del navegador). **No publiques el servidor en Internet con esta configuracion de demostracion**; una aplicacion real necesita cuentas de usuario, sesiones seguras, HTTPS y permisos.

## Repositorio GitHub

Crear un repositorio **nuevo y publico** en github.com; luego desde esta carpeta:

```bat
git init
git add .
git commit -m "Entrega final Albert Bandura School"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/albert-bandura-school.git
git push -u origin main
```

Sustituir `TU_USUARIO` por tu usuario real y el nombre elegido. Si el repositorio remoto trae README inicial, seguir las opciones indicadas por GitHub en lugar de sobrescribir trabajo existente. No subir DB de alumnos reales, credenciales ni contrasenas. Incluir el URL final en el PDF del proyecto.

## Notas de alcance

- Exportaciones XLSX y XML: **comprobantes internos**, no facturas fiscales autorizadas por SRI.
- Eliminacion fisica de pagos o facturas: solo demostracion CRUD; para operacion real se requiere historial/auditoria y anulaciones.
- `schema.sql` conserva el esquema original; los modelos de `app.py` son su representacion ORM.
- El reporte excluye los pagos `voided` de la recaudacion.
