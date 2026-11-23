// Interfaz simple del colegio: HTML, JavaScript y peticiones a Flask.
const $ = (id) => document.getElementById(id);
let representantes = [];
let estudiantes = [];
let pagos = [];
let facturas = [];
let reportes = [];

function mensaje(texto, error = false) {
    const aviso = $("mensaje_general");
    aviso.textContent = texto;
    aviso.className = error ? "alert error" : "alert";
    window.scrollTo({top: 0, behavior: "smooth"});
}

async function peticion(ruta, opciones = {}) {
    const respuesta = await fetch(ruta, opciones);
    let datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.error || datos.message || "No se pudo completar la operación");
    return datos;
}

function headersPrivados() {
    const clave = sessionStorage.getItem("schoolApiKey");
    return clave ? {"X-API-Key": clave} : {};
}
function opcionesJson(metodo, datos) {
    return {method: metodo, headers: {"Content-Type": "application/json", ...headersPrivados()}, body: JSON.stringify(datos)};
}

function mostrarVista(nombre) {
    document.querySelectorAll(".vista").forEach(vista => vista.classList.add("hidden"));
    $("vista-" + nombre).classList.remove("hidden");
    document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.view === nombre));
    $("mensaje_general").classList.add("hidden");
    window.scrollTo(0, 0);
}

function celda(fila, contenido) {
    const td = document.createElement("td");
    td.textContent = contenido ?? "";
    fila.appendChild(td);
    return td;
}

function boton(texto, fn, peligro = false) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = peligro ? "mini-action danger" : "mini-action";
    b.textContent = texto;
    b.addEventListener("click", fn);
    return b;
}

function vacio(tabla, columnas, texto) {
    const fila = document.createElement("tr");
    const td = celda(fila, texto);
    td.colSpan = columnas;
    td.className = "empty";
    tabla.appendChild(fila);
}

function selectOpciones(id, lista, etiqueta) {
    const select = $(id);
    const anterior = select.value;
    select.replaceChildren();
    const primera = document.createElement("option");
    primera.value = "";
    primera.textContent = etiqueta;
    select.appendChild(primera);
    lista.forEach(item => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.nombre;
        select.appendChild(option);
    });
    if ([...select.options].some(o => o.value === anterior)) select.value = anterior;
}

function nombreRepresentante(id) {
    const r = representantes.find(x => x.id === id);
    return r ? r.first_name + " " + r.last_name : "ID " + id;
}

function nombreEstudiante(id) {
    const e = estudiantes.find(x => x.id === id);
    return e ? e.first_name + " " + e.last_name : "ID " + id;
}

function dinero(valor) {
    return new Intl.NumberFormat("es-EC", {style: "currency", currency: "USD"}).format(Number(valor));
}

async function actualizarDatos() {
    [representantes, estudiantes, pagos, facturas] = await Promise.all([
        peticion("/representatives"), peticion("/students"),
        peticion("/payments"), peticion("/invoice_details")
    ]);
    $("total_representantes").textContent = representantes.length;
    $("total_estudiantes").textContent = estudiantes.length;
    $("total_pagos").textContent = pagos.length;
    $("total_facturas").textContent = facturas.length;

    selectOpciones("id_representante", representantes.map(r => ({id: r.id, nombre: r.first_name + " " + r.last_name + " (" + r.identification_number + ")"})), "Selecciona un representante");
    selectOpciones("pago_estudiante", estudiantes.map(e => ({id: e.id, nombre: e.first_name + " " + e.last_name + " - " + e.enrollment_number})), "Selecciona un estudiante");
    dibujarRepresentantes();
    dibujarEstudiantes();
    dibujarPagos();
    dibujarFacturas();
    await cargarReportes();
}

function dibujarRepresentantes() {
    const tabla = $("tabla_representantes");
    tabla.replaceChildren();
    const filtro = $("buscar_rep").value.trim().toLowerCase();
    const lista = representantes.filter(r => [r.first_name, r.last_name, r.identification_number].join(" ").toLowerCase().includes(filtro));
    if (!lista.length) return vacio(tabla, 5, "No hay representantes para mostrar.");
    lista.forEach(r => {
        const fila = document.createElement("tr");
        celda(fila, r.id);
        celda(fila, r.first_name + " " + r.last_name);
        celda(fila, r.identification_number);
        celda(fila, r.phone || "—");
        const acciones = celda(fila, "");
        acciones.appendChild(boton("Editar", () => editarRepresentante(r)));
        acciones.appendChild(boton("Eliminar", () => eliminar("/representative/" + r.id, "representante"), true));
        tabla.appendChild(fila);
    });
}

function editarRepresentante(r) {
    $("rep_id").value = r.id;
    $("nombre_rep").value = r.first_name;
    $("apellido_rep").value = r.last_name;
    $("cedula_rep").value = r.identification_number;
    $("telefono_rep").value = r.phone || "";
    $("email_rep").value = r.email || "";
    $("direccion_rep").value = r.address || "";
    $("titulo_rep").textContent = "Editar representante";
    $("boton_rep").textContent = "Guardar cambios";
    $("cancelar_rep").classList.remove("hidden");
    $("form_representante").scrollIntoView({behavior: "smooth"});
}

function resetRepresentante() {
    $("form_representante").reset();
    $("rep_id").value = "";
    $("titulo_rep").textContent = "Nuevo representante";
    $("boton_rep").textContent = "Guardar representante";
    $("cancelar_rep").classList.add("hidden");
}

async function guardarRepresentante(evento) {
    evento.preventDefault();
    const id = $("rep_id").value;
    const datos = {
        first_name: $("nombre_rep").value, last_name: $("apellido_rep").value,
        identification_number: $("cedula_rep").value, phone: $("telefono_rep").value,
        email: $("email_rep").value, address: $("direccion_rep").value
    };
    try {
        await peticion(id ? "/representative/" + id : "/representative", opcionesJson(id ? "PUT" : "POST", datos));
        resetRepresentante();
        await actualizarDatos();
        mensaje(id ? "Representante actualizado." : "Representante registrado correctamente.");
    } catch (error) { mensaje(error.message, true); }
}

function dibujarEstudiantes() {
    const tabla = $("tabla_estudiantes");
    tabla.replaceChildren();
    const filtro = $("buscar_est").value.trim().toLowerCase();
    const lista = estudiantes.filter(e => [e.first_name, e.last_name, e.enrollment_number].join(" ").toLowerCase().includes(filtro));
    if (!lista.length) return vacio(tabla, 5, "No hay estudiantes para mostrar.");
    lista.forEach(e => {
        const fila = document.createElement("tr");
        celda(fila, e.enrollment_number);
        celda(fila, e.first_name + " " + e.last_name);
        celda(fila, e.grade_level);
        celda(fila, nombreRepresentante(e.representative_id));
        const acciones = celda(fila, "");
        acciones.appendChild(boton("Editar", () => editarEstudiante(e)));
        acciones.appendChild(boton("Eliminar", () => eliminar("/student/" + e.id, "estudiante"), true));
        tabla.appendChild(fila);
    });
}

function editarEstudiante(e) {
    $("est_id").value = e.id;
    $("id_representante").value = e.representative_id;
    $("matricula").value = e.enrollment_number;
    $("nombre_est").value = e.first_name;
    $("apellido_est").value = e.last_name;
    $("curso").value = e.grade_level;
    $("titulo_est").textContent = "Editar estudiante";
    $("boton_est").textContent = "Guardar cambios";
    $("cancelar_est").classList.remove("hidden");
    $("form_estudiante").scrollIntoView({behavior: "smooth"});
}

function resetEstudiante() {
    $("form_estudiante").reset();
    $("est_id").value = "";
    $("titulo_est").textContent = "Nuevo estudiante";
    $("boton_est").textContent = "Guardar estudiante";
    $("cancelar_est").classList.add("hidden");
}

async function guardarEstudiante(evento) {
    evento.preventDefault();
    const id = $("est_id").value;
    const datos = {
        representative_id: Number($("id_representante").value),
        enrollment_number: $("matricula").value,
        first_name: $("nombre_est").value,
        last_name: $("apellido_est").value,
        grade_level: $("curso").value
    };
    try {
        await peticion(id ? "/student/" + id : "/student", opcionesJson(id ? "PUT" : "POST", datos));
        resetEstudiante();
        await actualizarDatos();
        mensaje(id ? "Estudiante actualizado." : "Estudiante registrado correctamente.");
    } catch (error) { mensaje(error.message, true); }
}

async function eliminar(ruta, tipo) {
    if (!confirm("¿Quieres eliminar este " + tipo + "?")) return;
    try {
        await peticion(ruta, {method: "DELETE", headers: headersPrivados()});
        await actualizarDatos();
        mensaje("Registro eliminado.");
    } catch (error) { mensaje(error.message, true); }
}

function dibujarPagos() {
    const tabla = $("tabla_pagos");
    tabla.replaceChildren();
    if (!pagos.length) return vacio(tabla, 7, "Todavía no hay pagos registrados.");
    pagos.forEach(p => {
        const fila = document.createElement("tr");
        celda(fila, p.id);
        celda(fila, nombreEstudiante(p.student_id));
        celda(fila, p.billing_month);
        celda(fila, p.payment_date);
        celda(fila, dinero(p.amount));
        const estado = celda(fila, "");
        const marca = document.createElement("span");
        marca.className = p.status === "voided" ? "status voided" : "status";
        marca.textContent = p.status === "voided" ? "Anulado" : "Completado";
        estado.appendChild(marca);
        const acciones = celda(fila, "");
        acciones.appendChild(boton(p.status !== "voided" ? "Anular" : "Reactivar", () => cambiarEstadoPago(p.id, p.status !== "voided" ? "voided" : "completed")));
        acciones.appendChild(boton("Eliminar", () => eliminar("/payment/" + p.id, "pago y su factura"), true));
        tabla.appendChild(fila);
    });
}

async function guardarPago(evento) {
    evento.preventDefault();
    const mes = $("pago_mes").value;
    const datos = {
        student_id: Number($("pago_estudiante").value),
        billing_month: mes + "-01",
        amount: Number($("pago_monto").value),
        payment_method: $("pago_metodo").value
    };
    try {
        await peticion("/payment", opcionesJson("POST", datos));
        $("form_pago").reset();
        $("pago_mes").value = new Date().getFullYear() + "-" + String(new Date().getMonth() + 1).padStart(2, "0");
        await actualizarDatos();
        mensaje("Pago registrado. La factura ya está disponible en Facturas.");
    } catch (error) { mensaje(error.message, true); }
}

async function cambiarEstadoPago(id, nuevoEstado) {
    if (!confirm("¿Cambiar el estado de este pago?")) return;
    try {
        await peticion("/payment/" + id, opcionesJson("PUT", {status: nuevoEstado}));
        await actualizarDatos();
        mensaje("Estado del pago actualizado.");
    } catch (error) { mensaje(error.message, true); }
}

function dibujarFacturas() {
    const tabla = $("tabla_facturas");
    tabla.replaceChildren();
    if (!facturas.length) return vacio(tabla, 6, "No hay facturas. Registra un pago primero.");
    facturas.forEach(f => {
        const fila = document.createElement("tr");
        celda(fila, f.invoice_number);
        celda(fila, f.student_first_name + " " + f.student_last_name);
        celda(fila, f.rep_first_name + " " + f.rep_last_name);
        celda(fila, f.issue_date);
        celda(fila, dinero(f.total));
        const acciones = celda(fila, "");
        [["Excel", "xlsx"], ["XML", "xml"]].forEach(([texto, extension]) => {
            const enlace = document.createElement("a");
            enlace.className = "link-download";
            enlace.href = "/invoice/" + f.id + "/" + extension;
            enlace.textContent = texto;
            enlace.setAttribute("download", f.invoice_number + "." + extension);
            acciones.appendChild(enlace);
        });
        acciones.appendChild(boton("Editar fecha", () => editarFechaFactura(f)));
        acciones.appendChild(boton("Eliminar", () => eliminar("/invoice/" + f.id, "comprobante"), true));
        tabla.appendChild(fila);
    });
}

async function editarFechaFactura(f) {
    const fecha = prompt("Nueva fecha de emisión (AAAA-MM-DD):", f.issue_date.slice(0,10));
    if (fecha === null) return;
    try {
        await peticion("/invoice/" + f.id, opcionesJson("PUT", {issue_date: fecha}));
        await actualizarDatos();
        mensaje("Fecha de emisión actualizada.");
    } catch (error) { mensaje(error.message, true); }
}

async function regenerarFactura() {
    const pid = Number(prompt("ID del pago cuya factura quieres regenerar:"));
    if (!pid) return;
    try {
        await peticion("/invoice", opcionesJson("POST", {payment_id: pid}));
        await actualizarDatos();
        mensaje("Factura regenerada.");
    } catch (error) { mensaje(error.message, true); }
}

async function cargarReportes() {
    reportes = await peticion("/reports/monthly");
    const tabla = $("tabla_reportes");
    tabla.replaceChildren();
    if (!reportes.length) return vacio(tabla, 3, "Aún no hay pagos válidos.");
    reportes.forEach(r => {
        const fila = document.createElement("tr");
        celda(fila, r.month); celda(fila, r.payments); celda(fila, dinero(r.total));
        tabla.appendChild(fila);
    });
}

function descargarReporte() {
    const filas = [["Mes","Cantidad de pagos","Total USD"], ...reportes.map(r => [r.month, r.payments, r.total])];
    const csv = filas.map(f => f.join(",")).join("\r\n");
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(new Blob(["\uFEFF" + csv], {type:"text/csv;charset=utf-8"}));
    enlace.download = "recaudacion_mensual.csv";
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(enlace.href), 500);
}

document.querySelectorAll(".nav-item").forEach(b => b.addEventListener("click", () => mostrarVista(b.dataset.view)));
document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => mostrarVista(b.dataset.go)));
$("form_representante").addEventListener("submit", guardarRepresentante);
$("form_estudiante").addEventListener("submit", guardarEstudiante);
$("form_pago").addEventListener("submit", guardarPago);
$("cancelar_rep").addEventListener("click", resetRepresentante);
$("cancelar_est").addEventListener("click", resetEstudiante);
$("buscar_rep").addEventListener("input", dibujarRepresentantes);
$("buscar_est").addEventListener("input", dibujarEstudiantes);
$("descargar_reporte").addEventListener("click", descargarReporte);
$("configurar_clave").addEventListener("click", () => {
    const clave = prompt("Clave API (solo si configuraste SCHOOL_API_KEY):", sessionStorage.getItem("schoolApiKey") || "");
    if (clave !== null) { if (clave) sessionStorage.setItem("schoolApiKey", clave); else sessionStorage.removeItem("schoolApiKey"); mensaje("Configuración de clave actualizada."); }
});
$("regenerar_factura").addEventListener("click", regenerarFactura);
$("fecha_hoy").textContent = new Date().toLocaleDateString("es-EC", {day: "numeric", month: "long", year: "numeric"});
const ahora = new Date();
$("pago_mes").value = ahora.getFullYear() + "-" + String(ahora.getMonth() + 1).padStart(2, "0");
actualizarDatos().catch(error => mensaje("No fue posible conectar con Flask: " + error.message, true));
