// Asistente de Procura — interfaz (sin dependencias)
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const vista = $("#vista");
const PROVEEDORES = {
  gmail: { host: "imap.gmail.com", nombre: "Gmail" },
  outlook: { host: "outlook.office365.com", nombre: "Outlook / Hotmail / Microsoft 365" },
  otro: { host: "", nombre: "Otro" },
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const CATEGORIAS = {
  notificacion_resolucion: "Resolución", senalamiento: "Señalamiento", aviso_lexnet: "Aviso LexNET",
  escrito_contrario: "Escrito de contrario", email_abogado: "Correo de abogado", email_cliente: "Correo de cliente",
  provision_factura: "Provisión / factura", colegio_administrativo: "Colegio / administrativo", publicidad: "Publicidad", otro: "Otro",
};
const CLASES = { actuacion: "Actuación", recurso: "Plazo para recurrir", senalamiento: "Señalamiento" };
const COMPUTOS = { habiles: "días hábiles", naturales: "días naturales", meses: "meses", fecha_fija: "fecha fija" };
const ROLES = { abogado: "Abogado/a", cliente: "Cliente", procurador: "Procurador/a", juzgado: "Juzgado", otro: "Otro" };

async function api(ruta, opciones = {}) {
  const o = { ...opciones };
  if (o.body && !(o.body instanceof FormData)) {
    o.headers = { "Content-Type": "application/json" };
    o.body = JSON.stringify(o.body);
  }
  const r = await fetch(ruta, o);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch {}
    avisar(msg);
    throw new Error(msg);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}

function avisar(texto) {
  const a = $("#aviso");
  a.textContent = texto;
  a.classList.remove("oculto");
  clearTimeout(avisar.t);
  avisar.t = setTimeout(() => a.classList.add("oculto"), 3500);
}

// ---------- fechas
const hoyISO = () => new Date().toLocaleDateString("sv");
function fechaCorta(iso) {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? iso + "T12:00" : iso);
  return d.toLocaleDateString("es-ES", { weekday: "short", day: "numeric", month: "short" });
}
function fechaHora(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-ES", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
function diasHasta(iso) {
  const a = new Date(hoyISO() + "T12:00"), b = new Date(iso.slice(0, 10) + "T12:00");
  return Math.round((b - a) / 86400000);
}
function chipVencimiento(p) {
  if (p.completado) return `<span class="chip ok">Hecho</span>`;
  const d = diasHasta(p.vencimiento);
  if (d < 0) return `<span class="chip vencido">Vencido hace ${-d} d</span>`;
  if (d === 0) return `<span class="chip vencido">Vence HOY</span>`;
  if (d === 1) return `<span class="chip pronto">Mañana</span>`;
  if (d <= 3) return `<span class="chip pronto">En ${d} días</span>`;
  return `<span class="chip">En ${d} días</span>`;
}
const procTexto = (x) => [x.tipo_proc || x.tipo, x.numero].filter(Boolean).join(" ") || "Sin procedimiento";

// ---------- modal
function abrirModal(html) { $("#modal-caja").innerHTML = html; $("#modal").classList.remove("oculto"); }
function cerrarModal() { $("#modal").classList.add("oculto"); }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") cerrarModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarModal(); });

// ---------- navegación
const VISTAS = {};
async function ir() {
  const [v, id] = (location.hash.slice(1) || "hoy").split("/");
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("activo", a.dataset.v === v));
  vista.innerHTML = `<p class="vacio">Cargando…</p>`;
  try { await (VISTAS[v] || VISTAS.hoy)(id); } catch (e) { vista.innerHTML = `<p class="vacio">No se pudo cargar: ${esc(e.message)}</p>`; }
}
window.addEventListener("hashchange", ir);

// ================================================================ HOY
VISTAS.hoy = async () => {
  const r = await api("/api/resumen");
  const hoy = r.plazos.filter((p) => diasHasta(p.vencimiento) <= 0);
  const pronto = r.plazos.filter((p) => diasHasta(p.vencimiento) > 0);
  const saludo = new Date().getHours() < 14 ? "Buenos días" : new Date().getHours() < 21 ? "Buenas tardes" : "Buenas noches";
  vista.innerHTML = `
    <div class="cabecera">
      <div><h1>${saludo}</h1><div class="suave">${new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</div></div>
      <div class="botones">
        <button onclick="subirArchivos()">Subir documentos</button>
        <button class="principal" onclick="revisarCorreo(this)">Revisar correo ahora</button>
      </div>
    </div>
    ${!r.configurado ? `<div class="tarjeta accion" style="margin-bottom:14px">Falta poner la clave de la IA. Ve a <a href="#ajustes">Ajustes</a>.</div>` : ""}
    <div class="rejilla">
      <div class="tarjeta"><div class="cifra ${hoy.length ? "rojo" : ""}">${hoy.length}</div>Plazos que vencen hoy o vencidos</div>
      <div class="tarjeta"><div class="cifra ${pronto.length ? "ambar" : ""}">${pronto.length}</div>Plazos en los próximos 7 días</div>
      <div class="tarjeta"><div class="cifra">${r.no_leidos.length}</div>Documentos sin revisar</div>
    </div>
    <h2>Plazos urgentes</h2>
    <div class="lista">${r.plazos.length ? r.plazos.map(htmlPlazo).join("") : `<div class="vacio">Nada que venza esta semana 🎉</div>`}</div>
    <h2>Novedades sin revisar</h2>
    <div class="lista">${r.no_leidos.length ? r.no_leidos.map(htmlDocCorto).join("") : `<div class="vacio">Todo revisado.</div>`}</div>
    <h2>Añadir documentos</h2>
    <div class="zona-subir" id="zona">Arrastra aquí los PDF descargados de LexNET, o <a href="#" onclick="subirArchivos();return false">elígelos</a>.</div>`;
  prepararZonaSubir($("#zona"));
};

function htmlDocCorto(d) {
  const estado = d.estado === "pendiente" ? `<span class="chip azul">Leyendo…</span>` : d.estado === "error" ? `<span class="chip alta">Error</span>` : "";
  return `<div class="item nuevo" onclick="location.hash='bandeja/${d.id}'">
    <div class="cuerpo"><div class="titulo">${esc(d.titulo || d.asunto_email || "Documento")}</div>
    <div class="linea">${esc(CATEGORIAS[d.categoria] || "")}</div></div>
    <div class="lado">${estado} ${d.urgencia ? `<span class="chip ${esc(d.urgencia)}">${esc(d.urgencia)}</span>` : ""}<br><small>${fechaHora(d.recibido_en)}</small></div></div>`;
}

function htmlPlazo(p) {
  return `<div class="item plazo ${p.completado ? "hecho" : ""}">
    <input type="checkbox" ${p.completado ? "checked" : ""} title="Marcar como hecho" onclick="event.stopPropagation(); marcarPlazo(${p.id}, this.checked)">
    <div class="fecha">${fechaCorta(p.vencimiento)}${p.hora ? ` <small>${esc(p.hora)}</small>` : ""}<small>${chipVencimiento(p)}</small></div>
    <div class="cuerpo" onclick="editarPlazo(${p.id})" style="cursor:pointer">
      <div class="titulo descr">${esc(p.descripcion)}</div>
      <div class="linea">${esc(CLASES[p.clase] || "")} · ${esc(procTexto(p))}${p.juzgado ? " · " + esc(p.juzgado) : ""}${p.cliente ? " · " + esc(p.cliente) : ""}</div>
    </div>
    <div class="lado">${p.asunto_id ? `<a href="#asuntos/${p.asunto_id}">Ver asunto</a>` : ""}</div>
  </div>`;
}

async function marcarPlazo(id, hecho) {
  await api(`/api/plazos/${id}`, { method: "PATCH", body: { completado: hecho ? 1 : 0 } });
  avisar(hecho ? "Plazo marcado como hecho" : "Plazo reabierto");
  actualizarContadores();
  ir();
}

async function revisarCorreo(btn) {
  btn.disabled = true; btn.textContent = "Revisando…";
  try {
    const r = await api("/api/correo/revisar", { method: "POST" });
    avisar(r.ocupado ? "Ya se estaba revisando el correo" : r.nuevos ? `${r.nuevos} correo(s) nuevo(s). La IA los está leyendo…` : "No hay correos nuevos");
  } finally { btn.disabled = false; btn.textContent = "Revisar correo ahora"; ir(); }
}

// ---------- subir
function subirArchivos() { $("#selector-archivos").click(); }
$("#selector-archivos").addEventListener("change", (e) => { enviarArchivos(e.target.files); e.target.value = ""; });
function prepararZonaSubir(zona) {
  zona.addEventListener("dragover", (e) => { e.preventDefault(); zona.classList.add("encima"); });
  zona.addEventListener("dragleave", () => zona.classList.remove("encima"));
  zona.addEventListener("drop", (e) => { e.preventDefault(); zona.classList.remove("encima"); enviarArchivos(e.dataTransfer.files); });
}
async function enviarArchivos(files) {
  if (!files.length) return;
  const fd = new FormData();
  [...files].forEach((f) => fd.append("archivos", f));
  await api("/api/subir", { method: "POST", body: fd });
  avisar(`${files.length} documento(s) subido(s). La IA los está leyendo…`);
  setTimeout(ir, 800);
}

// ================================================================ BANDEJA
VISTAS.bandeja = async (id) => {
  if (id) return verDocumento(id);
  const q = VISTAS.bandeja.q || "", cat = VISTAS.bandeja.cat || "";
  const docs = await api(`/api/documentos?q=${encodeURIComponent(q)}&categoria=${cat}`);
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Bandeja</h1><div class="suave">Todo lo que ha llegado, ya leído y clasificado por la IA.</div></div>
      <div class="botones"><button onclick="abrirPegarTexto()">Pegar texto</button><button class="principal" onclick="subirArchivos()">Subir documentos</button></div></div>
    <div class="fila" style="margin-bottom:14px">
      <input id="buscar" placeholder="Buscar (nombre, nº de autos, texto…)" value="${esc(q)}">
      <select id="filtro-cat"><option value="">Todas las categorías</option>
        ${Object.entries(CATEGORIAS).map(([k, v]) => `<option value="${k}" ${k === cat ? "selected" : ""}>${v}</option>`).join("")}</select>
    </div>
    <div class="lista">${docs.length ? docs.map((d) => `
      <div class="item ${d.leido ? "" : "nuevo"}" onclick="location.hash='bandeja/${d.id}'">
        <div class="cuerpo"><div class="titulo">${esc(d.titulo || d.asunto_email || "Documento")}</div>
          <div class="linea">${esc([CATEGORIAS[d.categoria], d.numero, d.juzgado].filter(Boolean).join(" · "))}</div>
          <div class="linea">${esc(d.resumen || d.error || (d.estado === "pendiente" ? "La IA lo está leyendo…" : ""))}</div></div>
        <div class="lado">${d.estado === "error" ? `<span class="chip alta">Error</span>` : d.estado === "pendiente" ? `<span class="chip azul">Leyendo…</span>` : d.urgencia ? `<span class="chip ${esc(d.urgencia)}">${esc(d.urgencia)}</span>` : ""}
          <br><small>${fechaHora(d.recibido_en)}</small></div>
      </div>`).join("") : `<div class="vacio">No hay documentos.</div>`}</div>`;
  let t;
  $("#buscar").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { VISTAS.bandeja.q = e.target.value; ir(); }, 400); });
  $("#filtro-cat").addEventListener("change", (e) => { VISTAS.bandeja.cat = e.target.value; ir(); });
};

function abrirPegarTexto() {
  abrirModal(`<h3>Pegar texto de una notificación o correo</h3>
    <textarea id="pegado" style="min-height:240px" placeholder="Pega aquí el texto…"></textarea>
    <label>Fecha de recepción</label><input type="datetime-local" id="pegado-fecha" value="${new Date().toISOString().slice(0, 16)}">
    <div class="botones" style="margin-top:14px"><button class="principal" onclick="enviarPegado()">Analizar</button><button onclick="cerrarModal()">Cancelar</button></div>`);
}
async function enviarPegado() {
  const fd = new FormData();
  fd.append("texto", $("#pegado").value);
  fd.append("recibido_en", $("#pegado-fecha").value);
  await api("/api/subir", { method: "POST", body: fd });
  cerrarModal(); avisar("La IA lo está leyendo…"); setTimeout(ir, 800);
}

async function verDocumento(id) {
  const d = await api(`/api/documentos/${id}`);
  if (!d.leido && d.estado === "procesado") { api(`/api/documentos/${id}`, { method: "PATCH", body: { leido: 1 } }).then(actualizarContadores); }
  const a = d.asunto;
  vista.innerHTML = `
    <p><a href="#bandeja">← Volver a la bandeja</a></p>
    <div class="cabecera"><div>
      <h1>${esc(d.titulo || d.asunto_email || "Documento")}</h1>
      <div>${d.categoria ? `<span class="chip azul">${esc(CATEGORIAS[d.categoria] || d.categoria)}</span>` : ""}
        ${d.urgencia ? `<span class="chip ${esc(d.urgencia)}">Urgencia ${esc(d.urgencia)}</span>` : ""}
        <span class="suave"> Recibido ${fechaHora(d.recibido_en)}</span></div></div>
      <div class="botones">
        <button onclick="location.hash='asistente'; setTimeout(()=>prepararAsistente(${d.asunto_id || "null"}, 'escrito', ${d.id}), 50)">Redactar escrito</button>
        <button onclick="location.hash='asistente'; setTimeout(()=>prepararAsistente(${d.asunto_id || "null"}, 'email', ${d.id}), 50)">Correo al abogado</button>
        <button onclick="marcarNoLeido(${d.id})">Marcar como no leído</button>
      </div></div>
    ${d.estado === "pendiente" ? `<div class="tarjeta">La IA está leyendo este documento… <button class="mini" onclick="ir()">Actualizar</button></div>` : ""}
    ${d.estado === "error" ? `<div class="tarjeta accion"><b>No se pudo analizar:</b> ${esc(d.error)} <button class="mini" onclick="reprocesar(${d.id})">Reintentar</button></div>` : ""}
    <div class="detalle">
      ${d.resumen ? `<div class="tarjeta"><h3>Qué dice</h3><p style="margin:0">${esc(d.resumen)}</p></div>` : ""}
      ${d.accion ? `<div class="accion"><b>Qué hay que hacer:</b> ${esc(d.accion)}</div>` : ""}
      ${d.plazos.length ? `<div><h2>Plazos detectados</h2><div class="lista">${d.plazos.map(htmlPlazo).join("")}</div>
        <small>Las fechas las calcula el programa con los festivos de Ajustes. Revísalas: pincha en un plazo para corregirlo.</small></div>` : ""}
      <div class="tarjeta">
        <h3>Procedimiento</h3>
        ${a ? `
          <div class="campo"><span>Órgano</span><span>${esc(a.juzgado)}</span></div>
          <div class="campo"><span>Procedimiento</span><span>${esc(procTexto(a))}</span></div>
          <div class="campo"><span>NIG</span><span>${esc(a.nig)}</span></div>
          <div class="campo"><span>Nuestra parte</span><span>${esc(a.cliente)}</span></div>
          <div class="campo"><span>Contrario</span><span>${esc(a.contrario)}</span></div>
          ${d.abogado ? `<div class="campo"><span>Abogado/a</span><span>${esc(d.abogado.nombre)} ${d.abogado.email ? `· <a href="mailto:${esc(d.abogado.email)}">${esc(d.abogado.email)}</a>` : ""}</span></div>` : ""}
          <p><a href="#asuntos/${a.id}">Ver todo el asunto →</a></p>` : `<p class="suave">No se ha asociado a ningún asunto.</p>`}
      </div>
      <div class="tarjeta">
        <h3>Origen</h3>
        ${d.remitente ? `<div class="campo"><span>De</span><span>${esc(d.remitente)}</span></div>` : ""}
        ${d.asunto_email ? `<div class="campo"><span>Asunto</span><span>${esc(d.asunto_email)}</span></div>` : ""}
        <div class="campo"><span>Archivos</span><span>${d.archivos.map((f) => `<a href="/api/archivo/${encodeURI(f)}" target="_blank">${esc(f.split("/").pop())}</a>`).join("<br>") || "—"}</span></div>
        <details style="margin-top:8px"><summary>Ver texto completo</summary><pre class="texto">${esc(d.texto)}</pre></details>
      </div>
      <div class="botones"><button onclick="reprocesar(${d.id})">Volver a analizar con la IA</button>
        <button class="peligro" onclick="borrarDocumento(${d.id})">Borrar documento</button></div>
    </div>`;
}
async function marcarNoLeido(id) { await api(`/api/documentos/${id}`, { method: "PATCH", body: { leido: 0 } }); actualizarContadores(); avisar("Marcado como no leído"); }
async function reprocesar(id) {
  if (!confirm("Se volverá a analizar y se sustituirán los plazos pendientes que se crearon desde este documento. ¿Seguir?")) return;
  await api(`/api/documentos/${id}/reprocesar`, { method: "POST" }); avisar("Analizando de nuevo…"); setTimeout(ir, 800);
}
async function borrarDocumento(id) {
  if (!confirm("¿Borrar este documento y sus plazos?")) return;
  await api(`/api/documentos/${id}`, { method: "DELETE" }); location.hash = "bandeja";
}

// ================================================================ PLAZOS
VISTAS.plazos = async () => {
  const verHechos = VISTAS.plazos.hechos;
  const lista = await api(`/api/plazos?completados=${!!verHechos}`);
  const grupos = verHechos ? [["Completados", lista]] : [
    ["Vencidos", lista.filter((p) => diasHasta(p.vencimiento) < 0), "rojo"],
    ["Hoy", lista.filter((p) => diasHasta(p.vencimiento) === 0), "rojo"],
    ["Próximos 7 días", lista.filter((p) => diasHasta(p.vencimiento) > 0 && diasHasta(p.vencimiento) <= 7)],
    ["Más adelante", lista.filter((p) => diasHasta(p.vencimiento) > 7)],
  ];
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Plazos</h1><div class="suave">Marca la casilla cuando esté hecho.</div></div>
      <div class="botones"><a class="boton" href="/api/plazos.ics" title="Para importar en Outlook, Google Calendar o Aranzadi Fusión">Exportar a calendario</a><button onclick="abrirCalculadora()">Calculadora de plazos</button>
        <button onclick="VISTAS.plazos.hechos=${!verHechos}; ir()">${verHechos ? "Ver pendientes" : "Ver completados"}</button>
        <button class="principal" onclick="editarPlazo()">Nuevo plazo</button></div></div>
    ${grupos.map(([t, ps, c]) => ps.length ? `<div class="grupo-titulo ${c || ""}">${t} (${ps.length})</div><div class="lista">${ps.map(htmlPlazo).join("")}</div>` : "").join("")
      || `<div class="vacio">No hay plazos ${verHechos ? "completados" : "pendientes"}.</div>`}`;
};

async function editarPlazo(id) {
  const p = id ? (await api(`/api/plazos?completados=false`)).concat(await api(`/api/plazos?completados=true`)).find((x) => x.id === id) : { clase: "actuacion", computo: "habiles", recepcion: hoyISO() };
  const asuntos = await api("/api/asuntos");
  abrirModal(`<h3>${id ? "Editar plazo" : "Nuevo plazo"}</h3>
    <label>Descripción</label><input id="p-desc" value="${esc(p.descripcion)}">
    <div class="fila">
      <div><label>Tipo</label><select id="p-clase">${Object.entries(CLASES).map(([k, v]) => `<option value="${k}" ${k === p.clase ? "selected" : ""}>${v}</option>`).join("")}</select></div>
      <div><label>Asunto</label><select id="p-asunto"><option value="">—</option>${asuntos.map((a) => `<option value="${a.id}" ${a.id === p.asunto_id ? "selected" : ""}>${esc(procTexto(a))} · ${esc(a.cliente || "")}</option>`).join("")}</select></div>
    </div>
    <div class="fila">
      <div><label>Cómputo</label><select id="p-computo">${Object.entries(COMPUTOS).map(([k, v]) => `<option value="${k}" ${k === p.computo ? "selected" : ""}>${v}</option>`).join("")}</select></div>
      <div class="solo-dias"><label>Nº de días / meses</label><input type="number" min="1" id="p-dias" value="${esc(p.dias ?? "")}"></div>
      <div class="solo-dias"><label>Fecha de recepción</label><input type="date" id="p-recepcion" value="${esc((p.recepcion || "").slice(0, 10))}"></div>
      <div class="solo-fija"><label>Fecha</label><input type="date" id="p-venc" value="${esc(p.vencimiento || "")}"></div>
      <div class="solo-fija"><label>Hora</label><input type="time" id="p-hora" value="${esc(p.hora || "")}"></div>
    </div>
    <label class="check solo-dias"><input type="checkbox" id="p-urgente" ${p.urgente ? "checked" : ""}> Agosto y Navidad cuentan como hábiles (instrucción penal, urgentes)</label>
    ${p.explicacion ? `<p class="suave" style="font-size:.9rem">${esc(p.explicacion)}</p>` : ""}
    <label>Notas</label><textarea id="p-notas">${esc(p.notas || "")}</textarea>
    <div class="botones" style="margin-top:14px"><button class="principal" onclick="guardarPlazo(${id || "null"})">Guardar</button>
      <button onclick="cerrarModal()">Cancelar</button>${id ? `<button class="peligro" onclick="borrarPlazo(${id})">Borrar</button>` : ""}</div>`);
  const alternar = () => {
    const fija = $("#p-computo").value === "fecha_fija";
    document.querySelectorAll(".solo-dias").forEach((e) => e.classList.toggle("oculto", fija));
    document.querySelectorAll(".solo-fija").forEach((e) => e.classList.toggle("oculto", !fija));
  };
  $("#p-computo").addEventListener("change", alternar); alternar();
}
async function guardarPlazo(id) {
  const computo = $("#p-computo").value;
  const body = { descripcion: $("#p-desc").value, clase: $("#p-clase").value, asunto_id: +$("#p-asunto").value || null, computo, notas: $("#p-notas").value };
  if (computo === "fecha_fija") Object.assign(body, { vencimiento: $("#p-venc").value, hora: $("#p-hora").value || null });
  else Object.assign(body, { dias: +$("#p-dias").value, recepcion: $("#p-recepcion").value, urgente: $("#p-urgente").checked });
  await api(id ? `/api/plazos/${id}` : "/api/plazos", { method: id ? "PATCH" : "POST", body });
  cerrarModal(); avisar("Plazo guardado"); actualizarContadores(); ir();
}
async function borrarPlazo(id) {
  if (!confirm("¿Borrar este plazo?")) return;
  await api(`/api/plazos/${id}`, { method: "DELETE" }); cerrarModal(); actualizarContadores(); ir();
}

function abrirCalculadora() {
  abrirModal(`<h3>Calculadora de plazos</h3>
    <div class="fila">
      <div><label>Recibido en LexNET el</label><input type="date" id="k-fecha" value="${hoyISO()}"></div>
      <div><label>Plazo</label><input type="number" id="k-dias" value="5" min="1"></div>
      <div><label>Cómputo</label><select id="k-computo"><option value="habiles">días hábiles</option><option value="naturales">días naturales</option><option value="meses">meses</option></select></div>
    </div>
    <label class="check"><input type="checkbox" id="k-urgente"> Agosto y Navidad hábiles</label>
    <div id="k-res" class="tarjeta" style="margin-top:14px"></div>
    <div class="botones" style="margin-top:14px"><button onclick="cerrarModal()">Cerrar</button></div>`);
  const calc = async () => {
    const r = await api("/api/calcular", { method: "POST", body: { recepcion: $("#k-fecha").value, dias: +$("#k-dias").value || 1, computo: $("#k-computo").value, urgente: $("#k-urgente").checked } });
    $("#k-res").innerHTML = `<div class="cifra">${new Date(r.vencimiento + "T12:00").toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" })}</div>
      <div>Día de gracia: hasta las 15:00 del ${fechaCorta(r.dia_gracia)}</div><p class="suave">${esc(r.explicacion)}</p>`;
  };
  ["#k-fecha", "#k-dias", "#k-computo", "#k-urgente"].forEach((s) => $(s).addEventListener("input", calc));
  calc();
}

// ================================================================ ASUNTOS
VISTAS.asuntos = async (id) => {
  if (id) return verAsunto(id);
  const lista = await api("/api/asuntos");
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Asuntos</h1><div class="suave">Se crean solos al llegar notificaciones. Pincha para ver el historial.</div></div>
      <div class="botones"><input id="buscar-asunto" placeholder="Buscar…" style="width:220px"><button class="principal" onclick="editarAsunto()">Nuevo asunto</button></div></div>
    <table><thead><tr><th>Procedimiento</th><th>Órgano</th><th>Nuestra parte</th><th>Abogado/a</th><th>Próximo plazo</th></tr></thead>
    <tbody>${lista.map((a) => `<tr class="clic" data-texto="${esc([a.numero, a.juzgado, a.cliente, a.contrario, a.abogado, a.nig].join(" ").toLowerCase())}" onclick="location.hash='asuntos/${a.id}'">
      <td><b>${esc(procTexto(a))}</b><br><small>${esc(a.materia || "")}</small></td><td>${esc(a.juzgado)}</td>
      <td>${esc(a.cliente)}<br><small>contra ${esc(a.contrario || "—")}</small></td><td>${esc(a.abogado || "—")}</td>
      <td>${a.proximo_plazo ? chipVencimiento({ vencimiento: a.proximo_plazo }) : "—"}</td></tr>`).join("")
      || `<tr><td colspan="5" class="vacio">Aún no hay asuntos.</td></tr>`}</tbody></table>`;
  $("#buscar-asunto").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll("tbody tr[data-texto]").forEach((tr) => tr.classList.toggle("oculto", !tr.dataset.texto.includes(q)));
  });
};

async function verAsunto(id) {
  const a = await api(`/api/asuntos/${id}`);
  vista.innerHTML = `
    <p><a href="#asuntos">← Todos los asuntos</a></p>
    <div class="cabecera"><div><h1>${esc(procTexto(a))}</h1><div class="suave">${esc(a.juzgado)}</div></div>
      <div class="botones"><button onclick="location.hash='asistente'; setTimeout(()=>prepararAsistente(${a.id}), 50)">Preguntar a la IA sobre este asunto</button>
        <button onclick="editarAsunto(${a.id})">Editar</button></div></div>
    <div class="detalle">
      <div class="tarjeta">
        <div class="campo"><span>Nuestra parte</span><span>${esc(a.cliente)}</span></div>
        <div class="campo"><span>Contrario</span><span>${esc(a.contrario)}</span></div>
        <div class="campo"><span>Materia</span><span>${esc(a.materia)}</span></div>
        <div class="campo"><span>Jurisdicción</span><span>${esc(a.jurisdiccion)}</span></div>
        <div class="campo"><span>NIG</span><span>${esc(a.nig)}</span></div>
        <div class="campo"><span>Abogado/a</span><span>${a.abogado ? `${esc(a.abogado.nombre)}${a.abogado.email ? ` · <a href="mailto:${esc(a.abogado.email)}">${esc(a.abogado.email)}</a>` : ""}${a.abogado.telefono ? ` · <a href="tel:${esc(a.abogado.telefono)}">${esc(a.abogado.telefono)}</a>` : ""}` : "—"}</span></div>
        ${a.notas ? `<div class="campo"><span>Notas</span><span style="white-space:pre-wrap">${esc(a.notas)}</span></div>` : ""}
      </div>
      <div><h2>Plazos</h2><div class="lista">${a.plazos.map(htmlPlazo).join("") || `<div class="vacio">Sin plazos.</div>`}</div></div>
      <div><h2>Historial</h2><div class="lista">${a.documentos.map((d) => `
        <div class="item" onclick="location.hash='bandeja/${d.id}'"><div class="cuerpo"><div class="titulo">${esc(d.titulo || "Documento")}</div>
        <div class="linea">${esc(d.resumen || "")}</div></div><div class="lado"><small>${fechaHora(d.recibido_en)}</small></div></div>`).join("") || `<div class="vacio">Sin documentos.</div>`}</div></div>
    </div>`;
}

async function editarAsunto(id) {
  const a = id ? await api(`/api/asuntos/${id}`) : {};
  const contactos = await api("/api/contactos");
  const campo = (k, t) => `<div><label>${t}</label><input id="a-${k}" value="${esc(a[k] || "")}"></div>`;
  abrirModal(`<h3>${id ? "Editar asunto" : "Nuevo asunto"}</h3>
    ${campo("juzgado", "Órgano judicial")}
    <div class="fila">${campo("tipo", "Tipo de procedimiento")}${campo("numero", "Número")}${campo("nig", "NIG")}</div>
    <div class="fila">${campo("cliente", "Nuestra parte")}${campo("contrario", "Contrario")}</div>
    <div class="fila">${campo("materia", "Materia")}
      <div><label>Abogado/a</label><select id="a-abogado_id"><option value="">—</option>${contactos.filter((c) => c.rol === "abogado").map((c) => `<option value="${c.id}" ${c.id === a.abogado_id ? "selected" : ""}>${esc(c.nombre)}</option>`).join("")}</select></div></div>
    <label>Notas</label><textarea id="a-notas">${esc(a.notas || "")}</textarea>
    ${id ? `<label class="check"><input type="checkbox" id="a-archivado" ${a.archivado ? "checked" : ""}> Asunto terminado (archivar)</label>` : ""}
    <div class="botones" style="margin-top:14px"><button class="principal" onclick="guardarAsunto(${id || "null"})">Guardar</button><button onclick="cerrarModal()">Cancelar</button></div>`);
}
async function guardarAsunto(id) {
  const body = {};
  ["juzgado", "tipo", "numero", "nig", "cliente", "contrario", "materia", "notas"].forEach((k) => (body[k] = $(`#a-${k}`).value || null));
  body.abogado_id = +$("#a-abogado_id").value || null;
  if (id) body.archivado = $("#a-archivado").checked ? 1 : 0;
  const r = await api(id ? `/api/asuntos/${id}` : "/api/asuntos", { method: id ? "PATCH" : "POST", body });
  cerrarModal(); avisar("Asunto guardado");
  location.hash = `asuntos/${id || r.id}`; ir();
}

// ================================================================ CONTACTOS
VISTAS.contactos = async () => {
  const lista = await api("/api/contactos");
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Contactos</h1><div class="suave">Abogados y clientes. Se añaden solos al leer notificaciones y correos.</div></div>
      <div class="botones"><input id="buscar-contacto" placeholder="Buscar…" style="width:220px"><button class="principal" onclick="editarContacto()">Nuevo contacto</button></div></div>
    <table><thead><tr><th>Nombre</th><th>Tipo</th><th>Correo</th><th>Teléfono</th><th>Despacho</th></tr></thead>
    <tbody>${lista.map((c) => `<tr class="clic" data-texto="${esc([c.nombre, c.email, c.despacho, c.telefono].join(" ").toLowerCase())}" onclick="editarContacto(${c.id})">
      <td><b>${esc(c.nombre)}</b>${c.n_asuntos ? `<br><small>${c.n_asuntos} asunto(s)</small>` : ""}</td><td>${esc(ROLES[c.rol] || c.rol)}</td>
      <td>${c.email ? `<a href="mailto:${esc(c.email)}" onclick="event.stopPropagation()">${esc(c.email)}</a>` : ""}</td>
      <td>${c.telefono ? `<a href="tel:${esc(c.telefono)}" onclick="event.stopPropagation()">${esc(c.telefono)}</a>` : ""}</td><td>${esc(c.despacho)}</td></tr>`).join("")
      || `<tr><td colspan="5" class="vacio">Aún no hay contactos.</td></tr>`}</tbody></table>`;
  $("#buscar-contacto").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll("tbody tr[data-texto]").forEach((tr) => tr.classList.toggle("oculto", !tr.dataset.texto.includes(q)));
  });
};

async function editarContacto(id) {
  const c = id ? (await api("/api/contactos")).find((x) => x.id === id) : { rol: "abogado" };
  const campo = (k, t, tipo = "text") => `<div><label>${t}</label><input type="${tipo}" id="c-${k}" value="${esc(c[k] || "")}"></div>`;
  abrirModal(`<h3>${id ? "Editar contacto" : "Nuevo contacto"}</h3>
    ${campo("nombre", "Nombre")}
    <div class="fila"><div><label>Tipo</label><select id="c-rol">${Object.entries(ROLES).map(([k, v]) => `<option value="${k}" ${k === c.rol ? "selected" : ""}>${v}</option>`).join("")}</select></div>
      ${campo("despacho", "Despacho")}</div>
    <div class="fila">${campo("email", "Correo", "email")}${campo("telefono", "Teléfono", "tel")}</div>
    <label>Notas</label><textarea id="c-notas">${esc(c.notas || "")}</textarea>
    <div class="botones" style="margin-top:14px"><button class="principal" onclick="guardarContacto(${id || "null"})">Guardar</button>
      <button onclick="cerrarModal()">Cancelar</button>${id ? `<button class="peligro" onclick="borrarContacto(${id})">Borrar</button>` : ""}</div>`);
}
async function guardarContacto(id) {
  const body = {};
  ["nombre", "rol", "despacho", "email", "telefono", "notas"].forEach((k) => (body[k] = $(`#c-${k}`).value || null));
  await api(id ? `/api/contactos/${id}` : "/api/contactos", { method: id ? "PATCH" : "POST", body });
  cerrarModal(); avisar("Contacto guardado"); ir();
}
async function borrarContacto(id) {
  if (!confirm("¿Borrar este contacto?")) return;
  await api(`/api/contactos/${id}`, { method: "DELETE" }); cerrarModal(); ir();
}

// ================================================================ ASISTENTE
const chat = { mensajes: [], asunto_id: null, escribiendo: false };
const ATAJOS = [
  ["Escrito de trámite", "Redáctame un escrito de trámite para "],
  ["Resumir en llano", "Explícame en lenguaje llano qué dice la última resolución de este asunto y qué hay que hacer."],
  ["Correo al abogado", "Redacta un correo al abogado comunicándole la última resolución notificada, con un resumen breve, el plazo y lo que necesito de él."],
  ["Correo al cliente", "Redacta un correo sencillo para el cliente explicándole la última novedad de su asunto, sin tecnicismos."],
  ["Solicitar copias", "Redacta un escrito solicitando copia de "],
  ["Personación", "Redacta un escrito de personación en nombre de "],
];

VISTAS.asistente = async () => {
  const asuntos = await api("/api/asuntos");
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Asistente</h1><div class="suave">Pídele escritos, correos o que te explique una resolución.</div></div>
      <div class="botones"><button onclick="chat.mensajes=[]; pintarChat()">Nueva conversación</button></div></div>
    <label>Asunto (la IA leerá sus documentos)</label>
    <select id="chat-asunto"><option value="">— Ninguno —</option>${asuntos.map((a) => `<option value="${a.id}" ${a.id === chat.asunto_id ? "selected" : ""}>${esc(procTexto(a))} · ${esc(a.cliente || "")} · ${esc(a.juzgado || "")}</option>`).join("")}</select>
    <div class="atajos">${ATAJOS.map(([t, p], i) => `<button class="mini" onclick="usarAtajo(${i})">${t}</button>`).join("")}</div>
    <div class="chat" id="chat"></div>
    <div class="caja-chat"><textarea id="chat-texto" placeholder="Escribe aquí… (Ctrl+Intro para enviar)"></textarea>
      <button class="principal" id="chat-enviar" onclick="enviarChat()">Enviar</button></div>`;
  $("#chat-asunto").addEventListener("change", (e) => (chat.asunto_id = +e.target.value || null));
  $("#chat-texto").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) enviarChat(); });
  pintarChat();
};

function usarAtajo(i) { const t = $("#chat-texto"); t.value = ATAJOS[i][1]; t.focus(); }

async function prepararAsistente(asuntoId, tipo, docId) {
  chat.asunto_id = asuntoId; chat.mensajes = [];
  await VISTAS.asistente();
  const d = docId ? await api(`/api/documentos/${docId}`) : null;
  const ref = d ? `el documento «${d.titulo || d.asunto_email}» recibido el ${fechaHora(d.recibido_en)}` : "la última resolución";
  if (tipo === "email") $("#chat-texto").value = `Redacta un correo al abogado${d?.abogado ? ` (${d.abogado.nombre})` : ""} comunicándole ${ref}: resumen breve, plazo si lo hay y qué necesito de él.`;
  else if (tipo === "escrito") $("#chat-texto").value = `A la vista de ${ref}, redáctame el escrito que corresponda presentar.`;
  if (d && !asuntoId) $("#chat-texto").value += `\n\nTexto del documento:\n${d.texto}`;
  $("#chat-texto").focus();
}

function pintarChat() {
  const el = $("#chat");
  if (!el) return;
  el.innerHTML = chat.mensajes.map((m, i) => `<div class="msg ${m.role}">${esc(m.content)}${m.role === "assistant" && !(chat.escribiendo && i === chat.mensajes.length - 1) ? `
    <div class="acciones"><button class="mini" onclick="copiar(${i})">Copiar</button><button class="mini" onclick="aWord(${i})">Descargar Word</button>
    ${/^\s*asunto:/i.test(m.content) ? `<button class="mini" onclick="abrirCorreo(${i})">Abrir en el correo</button>` : ""}</div>` : ""}</div>`).join("")
    || `<div class="vacio">Elige un asunto (opcional) y escribe lo que necesitas, o usa un atajo.</div>`;
  el.lastElementChild?.scrollIntoView({ block: "end" });
}

async function enviarChat() {
  const t = $("#chat-texto"), texto = t.value.trim();
  if (!texto || chat.escribiendo) return;
  chat.mensajes.push({ role: "user", content: texto }, { role: "assistant", content: "" });
  t.value = ""; chat.escribiendo = true; $("#chat-enviar").disabled = true; pintarChat();
  const ultimo = chat.mensajes[chat.mensajes.length - 1];
  try {
    const r = await fetch("/api/asistente", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensajes: chat.mensajes.slice(0, -1), asunto_id: chat.asunto_id }) });
    const lector = r.body.getReader(), dec = new TextDecoder();
    let pintado = 0;
    for (;;) {
      const { done, value } = await lector.read();
      if (done) break;
      ultimo.content += dec.decode(value, { stream: true });
      if (Date.now() - pintado > 120) { pintarChat(); pintado = Date.now(); }
    }
  } catch (e) { ultimo.content += `\n[Error: ${e.message}]`; }
  chat.escribiendo = false; if ($("#chat-enviar")) $("#chat-enviar").disabled = false; pintarChat();
}

function copiar(i) { navigator.clipboard.writeText(chat.mensajes[i].content).then(() => avisar("Copiado")); }
async function aWord(i) {
  const r = await api("/api/word", { method: "POST", body: { texto: chat.mensajes[i].content, nombre: `escrito_${hoyISO()}` } });
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: `escrito_${hoyISO()}.docx` });
  a.click(); URL.revokeObjectURL(url);
}
async function abrirCorreo(i) {
  const texto = chat.mensajes[i].content.trim();
  const [primera, ...resto] = texto.split("\n");
  const asunto = primera.replace(/^\s*asunto:\s*/i, "");
  let para = "";
  if (chat.asunto_id) { const a = await api(`/api/asuntos/${chat.asunto_id}`); para = a.abogado?.email || ""; }
  location.href = `mailto:${encodeURIComponent(para)}?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(resto.join("\n").trim())}`;
}

// ================================================================ BIENVENIDA
VISTAS.bienvenida = async () => {
  const c = await api("/api/ajustes");
  const prov = c.imap_host.includes("gmail") ? "gmail" : c.imap_host.includes("office365") || c.imap_host.includes("outlook") ? "outlook" : c.imap_host ? "otro" : "gmail";
  vista.innerHTML = `
    <div class="cabecera"><div><h1>¡Bienvenida!</h1><div class="suave">Unos pocos datos y listo. Se guardan solo en este ordenador.</div></div></div>
    <div class="pasos">
      <div class="tarjeta paso"><h3>Tus datos</h3>
        <div class="fila">
          <div><label>Tu nombre, tal como sale en las notificaciones</label><input id="b-nombre" value="${esc(c.nombre_procuradora)}" placeholder="MARÍA GARCÍA LÓPEZ"></div>
          <div><label>Ciudad</label><input id="b-ciudad" value="${esc(c.ciudad)}"></div>
        </div></div>
      <div class="tarjeta paso"><h3>Clave de la inteligencia artificial</h3>
        <label>Clave (empieza por sk-ant-)</label><input type="password" id="b-clave" value="${esc(c.anthropic_api_key)}" autocomplete="off">
        <div class="botones" style="margin-top:8px"><button onclick="probarIA('b-clave', 'b-ia-res')">Comprobar clave</button><span id="b-ia-res"></span></div>
        <div class="ayuda">Si no te la han dado ya: entra en <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>,
          crea una cuenta, añade saldo en <i>Billing</i> y crea una clave en <i>API Keys</i>. Cópiala y pégala aquí.</div></div>
      <div class="tarjeta paso"><h3>Tu correo</h3>
        <div class="fila">
          <div><label>¿Qué correo usas?</label><select id="b-prov">${Object.entries(PROVEEDORES).map(([k, v]) => `<option value="${k}" ${k === prov ? "selected" : ""}>${v.nombre}</option>`).join("")}</select></div>
          <div><label>Dirección de correo</label><input type="email" id="b-usuario" value="${esc(c.imap_usuario)}" placeholder="nombre@gmail.com"></div>
        </div>
        <div class="fila oculto" id="b-otro"><div><label>Servidor IMAP (te lo dice tu proveedor)</label><input id="b-host" value="${esc(c.imap_host)}"></div></div>
        <div id="b-con-clave">
          <label>Contraseña de aplicación</label><input type="password" id="b-pass" value="${esc(c.imap_password)}" autocomplete="off">
          <div class="botones" style="margin-top:8px"><button onclick="probarCorreoBienvenida()">Comprobar correo</button><span id="b-correo-res"></span></div>
        </div>
        <div id="b-ms" class="oculto"></div>
        <div class="ayuda" id="b-ayuda-correo"></div></div>
      <div class="tarjeta paso"><h3>Últimos detalles</h3>
        <label class="check"><input type="checkbox" id="b-arranque" ${c.arrancar_con_el_ordenador ? "checked" : ""}> Abrir el asistente al encender el ordenador (recomendado, así no se pierde ningún aviso)</label>
        <p class="suave">Los festivos de la Comunitat Valenciana y de València de 2026 ya vienen puestos. Revísalos en <i>Ajustes</i> y añade los de cada año.</p>
        <button class="principal" onclick="terminarBienvenida()">Empezar a usarlo</button></div>
    </div>`;
  const ayudaCorreo = () => {
    const p = $("#b-prov").value;
    $("#b-otro").classList.toggle("oculto", p !== "otro");
    $("#b-con-clave").classList.toggle("oculto", p === "outlook");
    $("#b-ms").classList.toggle("oculto", p !== "outlook");
    $("#b-usuario").closest("div").classList.toggle("oculto", p === "outlook");
    if (p === "outlook") pintarMicrosoft("b-ms");
    $("#b-ayuda-correo").innerHTML = p === "gmail"
      ? `Gmail no deja usar la contraseña normal. Hay que crear una <b>contraseña de aplicación</b>:<ol>
          <li>Entra en <a href="https://myaccount.google.com/signinoptions/two-step-verification" target="_blank">Verificación en dos pasos</a> y actívala si no lo está.</li>
          <li>Entra en <a href="https://myaccount.google.com/apppasswords" target="_blank">Contraseñas de aplicación</a>, escribe «Asistente» y pulsa <i>Crear</i>.</li>
          <li>Copia las 16 letras que salen y pégalas arriba.</li></ol>`
      : p === "outlook"
      ? `Pulsa <b>Conectar con Outlook</b>. Saldrá un código: ábrelo en la página de Microsoft, escribe el código,
         entra con tu correo y contraseña de siempre y pulsa <i>Aceptar</i>. No hace falta crear ninguna contraseña.`
      : `Pide a tu proveedor de correo el «servidor IMAP» y una contraseña para programas.`;
  };
  $("#b-prov").addEventListener("change", ayudaCorreo); ayudaCorreo();
};

function datosCorreoBienvenida() {
  const p = $("#b-prov").value;
  return { imap_host: p === "otro" ? $("#b-host").value.trim() : PROVEEDORES[p].host, imap_puerto: 993,
    imap_usuario: $("#b-usuario").value.trim(), imap_password: $("#b-pass").value.replace(/\s/g, "") };
}
async function probarIA(campo, salida) {
  const res = $("#" + salida);
  res.innerHTML = "Comprobando…";
  try {
    const r = await fetch("/api/probar/ia", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ anthropic_api_key: $("#" + campo).value.trim() }) });
    res.innerHTML = r.ok ? `<span class="ok-texto">✓ La clave funciona</span>` : `<span class="error-texto">${esc((await r.json()).detail)}</span>`;
  } catch { res.innerHTML = `<span class="error-texto">No se pudo comprobar.</span>`; }
}
async function probarCorreo(datos, salida) {
  const res = $("#" + salida);
  res.innerHTML = "Conectando…";
  try {
    const r = await fetch("/api/probar/correo", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });
    const j = await r.json();
    res.innerHTML = r.ok ? `<span class="ok-texto">✓ Conectado (${j.mensajes} correos en la bandeja)</span>` : `<span class="error-texto">${esc(j.detail)}</span>`;
    return r.ok;
  } catch { res.innerHTML = `<span class="error-texto">No se pudo comprobar.</span>`; return false; }
}
const probarCorreoBienvenida = () => probarCorreo(datosCorreoBienvenida(), "b-correo-res");

async function terminarBienvenida() {
  const correo = datosCorreoBienvenida();
  if ($("#b-prov").value === "outlook") {
    const ms = await api("/api/microsoft/estado");
    Object.assign(correo, { imap_auth: "microsoft", imap_host: "outlook.office365.com", imap_usuario: ms.usuario || "", imap_password: "" });
    correo.listo = ms.estado === "conectado";
  } else {
    correo.imap_auth = "password";
    correo.listo = !!(correo.imap_host && correo.imap_usuario && correo.imap_password);
  }
  const listo = correo.listo; delete correo.listo;
  const body = { nombre_procuradora: $("#b-nombre").value.trim(), ciudad: $("#b-ciudad").value.trim(),
    anthropic_api_key: $("#b-clave").value.trim(), ...correo,
    correo_activo: listo,
    arrancar_con_el_ordenador: $("#b-arranque").checked, bienvenida_hecha: true };
  if (!body.nombre_procuradora) return avisar("Falta tu nombre");
  if (!body.anthropic_api_key) return avisar("Falta la clave de la inteligencia artificial");
  await api("/api/ajustes", { method: "PUT", body });
  if ("Notification" in window && Notification.permission === "default") await Notification.requestPermission();
  avisar(body.correo_activo ? "¡Listo! Voy a mirar tu correo…" : "¡Listo! (El correo lo puedes configurar luego en Ajustes)");
  location.hash = "hoy";
}

// ---------- conexión con Microsoft (Outlook)
let sondeoMicrosoft;
async function pintarMicrosoft(id) {
  const el = $("#" + id);
  if (!el) return;
  const e = await api("/api/microsoft/estado");
  clearTimeout(sondeoMicrosoft);
  if (e.estado === "conectado") {
    el.innerHTML = `<p class="ok-texto">✓ Outlook conectado: ${esc(e.usuario)}</p>
      <div class="botones"><button onclick="probarCorreo({imap_auth:'microsoft'}, '${id}-res')">Comprobar correo</button>
      <button class="peligro" onclick="desconectarMicrosoft('${id}')">Desconectar</button><span id="${id}-res"></span></div>`;
  } else if (e.estado === "esperando") {
    el.innerHTML = `<div class="tarjeta" style="text-align:center">
      <p style="margin:0">1. Copia este código:</p>
      <div class="cifra" style="letter-spacing:.15em; margin:6px 0">${esc(e.codigo)}</div>
      <button class="mini" onclick="navigator.clipboard.writeText('${esc(e.codigo)}').then(()=>avisar('Código copiado'))">Copiar código</button>
      <p>2. <a href="${esc(e.url)}" target="_blank"><b>Abre la página de Microsoft</b></a>, pega el código, entra con tu cuenta y pulsa <i>Aceptar</i>.</p>
      <p class="suave">Esperando a que termines en la página de Microsoft…</p></div>`;
    sondeoMicrosoft = setTimeout(() => pintarMicrosoft(id), 3000);
  } else {
    el.innerHTML = `${e.error ? `<p class="error-texto">${esc(e.error)}</p>` : ""}
      <button class="principal" onclick="conectarMicrosoft('${id}')">Conectar con Outlook</button>`;
  }
}
async function conectarMicrosoft(id) {
  try {
    const r = await api("/api/microsoft/iniciar", { method: "POST" });
    window.open(r.url, "_blank");
  } catch { return; }
  pintarMicrosoft(id);
}
async function desconectarMicrosoft(id) {
  if (!confirm("¿Desconectar la cuenta de Outlook? Dejará de revisarse el correo.")) return;
  await api("/api/microsoft/desconectar", { method: "POST" });
  pintarMicrosoft(id);
}

async function cerrarPrograma() {
  if (!confirm("Si cierras el programa no se revisará el correo ni recibirás avisos hasta que lo vuelvas a abrir. ¿Cerrar?")) return;
  await fetch("/api/salir", { method: "POST" });
  document.body.innerHTML = `<main style="padding:40px"><h1>Programa cerrado</h1><p>Puedes cerrar esta pestaña. Para volver a abrirlo, haz doble clic en <b>AsistenteProcura</b>.</p></main>`;
}

// ================================================================ AJUSTES
VISTAS.ajustes = async () => {
  const c = await api("/api/ajustes");
  const campo = (k, t, tipo = "text", extra = "") => `<div><label>${t}</label><input type="${tipo}" id="s-${k}" value="${esc(c[k] ?? "")}" ${extra}></div>`;
  vista.innerHTML = `
    <div class="cabecera"><div><h1>Ajustes</h1><div class="suave">Se guardan solo en este ordenador.</div></div></div>
    <div class="detalle">
      <div class="tarjeta"><h3>Datos de la procuradora</h3>
        <div class="fila">${campo("nombre_procuradora", "Nombre completo (tal como aparece en las notificaciones)")}${campo("ciudad", "Ciudad")}</div></div>
      <div class="tarjeta"><h3>Inteligencia artificial</h3>
        ${campo("anthropic_api_key", "Clave de Anthropic (empieza por sk-ant-)", "password", 'autocomplete="off"')}
        <small>Se consigue en console.anthropic.com → API Keys. Ver el manual (README).</small>
        <div class="botones" style="margin-top:8px"><button onclick="probarIA('s-anthropic_api_key', 's-ia-res')">Comprobar clave</button><span id="s-ia-res"></span></div>
        ${campo("modelo", "Modelo")}</div>
      <div class="tarjeta"><h3>Correo</h3>
        <label class="check"><input type="checkbox" id="s-correo_activo" ${c.correo_activo ? "checked" : ""}> Revisar el correo automáticamente</label>
        <label>Forma de conectar</label>
        <select id="s-imap_auth"><option value="microsoft" ${c.imap_auth === "microsoft" ? "selected" : ""}>Cuenta de Microsoft (Outlook, Hotmail, Microsoft 365)</option>
          <option value="password" ${c.imap_auth !== "microsoft" ? "selected" : ""}>Usuario y contraseña (Gmail y otros)</option></select>
        <div id="s-ms-bloque"><div id="s-ms" style="margin-top:10px"></div>
          <details style="margin-top:10px"><summary>Avanzado</summary>${campo("ms_client_id", "Id. de aplicación de Microsoft (ver docs/MICROSOFT.md)")}</details></div>
        <div id="s-clave-bloque">
        <div class="fila">${campo("imap_host", "Servidor IMAP")}${campo("imap_puerto", "Puerto", "number")}</div>
        <div class="fila">${campo("imap_usuario", "Usuario (dirección de correo)", "email")}${campo("imap_password", "Contraseña de aplicación", "password", 'autocomplete="off"')}</div>
        <div class="botones" style="margin-top:8px"><button onclick="probarCorreo({imap_host: $('#s-imap_host').value, imap_puerto: +$('#s-imap_puerto').value, imap_usuario: $('#s-imap_usuario').value, imap_password: $('#s-imap_password').value}, 's-correo-res')">Comprobar correo</button><span id="s-correo-res"></span></div>
        </div>
        <div class="fila">${campo("imap_carpeta", "Carpeta")}${campo("revisar_cada_min", "Revisar cada (minutos)", "number")}</div>
        <small>Gmail: imap.gmail.com · Outlook/Hotmail: outlook.office365.com · Para Gmail hace falta una «contraseña de aplicación» (ver <a href="#bienvenida">bienvenida</a>).</small></div>
      <div class="tarjeta"><h3>Programa</h3>
        <label class="check"><input type="checkbox" id="s-arrancar_con_el_ordenador" ${c.arrancar_con_el_ordenador ? "checked" : ""}> Abrir al encender el ordenador</label>
        <p class="suave" id="s-info-version"></p></div>
      <div class="tarjeta"><h3>Calendario de días inhábiles</h3>
        <label class="check"><input type="checkbox" id="s-agosto_inhabil" ${c.agosto_inhabil ? "checked" : ""}> Agosto inhábil</label>
        <label class="check"><input type="checkbox" id="s-navidad_inhabil" ${c.navidad_inhabil ? "checked" : ""}> Del 24 de diciembre al 6 de enero inhábil</label>
        <label>Festivos autonómicos y locales (los nacionales ya se tienen en cuenta)</label>
        <textarea id="s-festivos" style="min-height:220px; font-family:ui-monospace,Consolas,monospace">${esc(c.festivos)}</textarea>
        <small>Una fecha por línea (AAAA-MM-DD). Añade cada año los festivos de la Comunitat y de la localidad del juzgado.</small></div>
      <div class="botones"><button class="principal" onclick="guardarAjustes()">Guardar ajustes</button></div>
    </div>`;
  const alternarAcceso = () => {
    const ms = $("#s-imap_auth").value === "microsoft";
    $("#s-ms-bloque").classList.toggle("oculto", !ms);
    $("#s-clave-bloque").classList.toggle("oculto", ms);
    if (ms) pintarMicrosoft("s-ms");
  };
  $("#s-imap_auth").addEventListener("change", alternarAcceso); alternarAcceso();
  const v = await api("/api/version");
  $("#s-info-version").innerHTML = `Versión ${esc(v.version)}. Tus datos están en: <code>${esc(v.datos)}</code> (copia esa carpeta de vez en cuando como copia de seguridad).`;
};
async function guardarAjustes() {
  const body = {};
  ["nombre_procuradora", "ciudad", "anthropic_api_key", "modelo", "imap_host", "imap_usuario", "imap_password", "imap_carpeta", "festivos", "imap_auth", "ms_client_id"].forEach((k) => (body[k] = $(`#s-${k}`).value));
  ["imap_puerto", "revisar_cada_min"].forEach((k) => (body[k] = +$(`#s-${k}`).value));
  ["correo_activo", "agosto_inhabil", "navidad_inhabil", "arrancar_con_el_ordenador"].forEach((k) => (body[k] = $(`#s-${k}`).checked));
  await api("/api/ajustes", { method: "PUT", body });
  avisar("Ajustes guardados");
  if (body.correo_activo && "Notification" in window && Notification.permission === "default") Notification.requestPermission();
}

// ================================================================ avisos en segundo plano
let ultimoAvisado = +(localStorage.getItem("ultimoAvisado") || 0);
async function actualizarContadores() {
  let r;
  try { r = await api("/api/resumen"); } catch { return; }
  $("#c-bandeja").textContent = r.no_leidos.length || "";
  $("#c-plazos").textContent = r.plazos.filter((p) => diasHasta(p.vencimiento) <= 1).length || "";
  const ec = r.correo;
  $("#estado-correo").innerHTML = !ec.activo ? "Correo automático desactivado" :
    ec.ultimo_error ? `<span style="color:var(--rojo)">Error de correo:</span> ${esc(ec.ultimo_error).slice(0, 120)}` :
    ec.revisando ? "Revisando correo…" : ec.ultima_revision ? `Correo revisado a las ${new Date(ec.ultima_revision).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}` : "";
  const nuevos = r.no_leidos.filter((d) => d.estado === "procesado" && d.id > ultimoAvisado && d.categoria !== "publicidad");
  if (nuevos.length) {
    ultimoAvisado = Math.max(...nuevos.map((d) => d.id));
    localStorage.setItem("ultimoAvisado", ultimoAvisado);
    if ("Notification" in window && Notification.permission === "granted") {
      nuevos.slice(0, 3).forEach((d) => {
        const n = new Notification(d.urgencia === "alta" ? "⚠️ Notificación urgente" : "Nueva notificación", { body: d.titulo || d.asunto_email || "", tag: "doc" + d.id });
        n.onclick = () => { window.focus(); location.hash = `bandeja/${d.id}`; };
      });
    }
    document.title = `(${r.no_leidos.length}) Asistente de Procura`;
    const v = location.hash.slice(1).split("/")[0] || "hoy";
    if (["hoy", "bandeja"].includes(v) && !location.hash.includes("/")) ir();
  } else if (!r.no_leidos.length) document.title = "Asistente de Procura";
}

if ("Notification" in window && Notification.permission === "default") {
  document.addEventListener("click", () => Notification.requestPermission(), { once: true });
}
(async () => {
  try {
    const r = await api("/api/resumen");
    if (!r.bienvenida_hecha && !location.hash.startsWith("#ajustes")) location.hash = "bienvenida";
  } catch {}
  ir();
  actualizarContadores();
  setInterval(actualizarContadores, 30000);
  try {
    const v = await api("/api/version");
    $("#version").textContent = v.version === "desarrollo" ? "" : `v${v.version.replace(/^v/, "")}`;
    if (v.nueva) {
      const a = $("#actualizacion");
      a.innerHTML = `Hay una versión nueva del programa. <a href="${esc(v.descarga)}" target="_blank">Descárgala aquí</a>, cierra este programa y abre el nuevo (tus datos se conservan).`;
      a.classList.remove("oculto");
    }
  } catch {}
})();
