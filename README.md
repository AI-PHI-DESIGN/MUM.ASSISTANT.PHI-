# Asistente de Procura

Programa para el ordenador de una procuradora de los Tribunales. Se abre en el navegador, pero funciona
en su propio ordenador y guarda los datos allí.

**Qué hace:**

- **Lee el correo** cada pocos minutos y **avisa** cuando llega algo nuevo (notificaciones de LexNET, correos de
  abogados o de clientes...).
- La IA **lee cada notificación**, la **clasifica** (resolución, señalamiento, correo de abogado...), hace un
  **resumen en lenguaje llano** y explica **qué hay que hacer**.
- **Calcula los plazos** con los días inhábiles: fines de semana, festivos, agosto, Navidad y el día de gracia.
  La IA solo dice cuántos días son; la fecha la calcula el programa, que no se equivoca con el calendario.
- Agrupa todo por **asuntos** (nº de procedimiento / NIG) y guarda los **contactos** de abogados y clientes.
- **Asistente de redacción:** escritos de trámite con su formato habitual, correos al abogado o al cliente,
  explicaciones de resoluciones. Se pueden descargar en Word o abrir directamente en el correo.
- **Exporta los plazos a un calendario** (.ics) que se puede importar en Outlook, Google Calendar u otros programas.

> ⚠️ Es una **ayuda**, no sustituye su criterio. Hay que revisar siempre los plazos y los escritos antes de
> usarlos, sobre todo al principio.

---

## 1. Instalación: descargar y abrir

**Guía de inicio con capturas (PDF, para la usuaria):**
<https://github.com/AI-PHI-DESIGN/MUM.ASSISTANT.PHI-/releases/latest/download/Guia_Asistente_de_Procura.pdf>

**Descargar la última versión:**

- **Windows:** <https://github.com/AI-PHI-DESIGN/MUM.ASSISTANT.PHI-/releases/latest/download/AsistenteProcura.exe>
- **Mac:** <https://github.com/AI-PHI-DESIGN/MUM.ASSISTANT.PHI-/releases/latest/download/AsistenteProcura-Mac.zip>

No hace falta instalar nada más.

1. Guardar el archivo en una carpeta fija (por ejemplo, *Documentos*) y hacer **doble clic**.
   - Windows puede avisar con «Windows protegió su PC»: pulsar **Más información → Ejecutar de todas formas**
     (sale porque el programa no está firmado por una empresa; es normal).
   - Mac: descomprimir el zip, clic derecho sobre *AsistenteProcura* → **Abrir** → **Abrir**.
2. Se abre el navegador con la **pantalla de bienvenida**. Rellenar los datos (ver apartado 2) y pulsar
   **Empezar a usarlo**.
3. A partir de ahí el programa **se abre solo al encender el ordenador** y revisa el correo en segundo plano.
   Si llega algo importante y no está abierto en el navegador, se abre solo.
   Para abrirlo a mano, doble clic en el archivo otra vez.
4. **Cerrar programa** (abajo a la izquierda) lo apaga del todo. Mientras esté cerrado no revisa el correo.

**Actualizar:** cuando haya una versión nueva aparece un aviso arriba con el enlace. Descargarla, cerrar el
programa y sustituir el archivo antiguo por el nuevo. Los datos se conservan.

## 2. Datos que pide la bienvenida (se pueden cambiar luego en «Ajustes»)

### Nombre
Su nombre **tal como aparece en las notificaciones** (p. ej. «MARÍA GARCÍA LÓPEZ»). Así la IA sabe cuál es
«nuestra parte» en cada procedimiento.

### Clave de la IA (Anthropic)
1. Entrar en <https://console.anthropic.com> y crear una cuenta.
2. En *Billing*, añadir saldo (con 10–20 € hay para bastante tiempo; se paga por uso).
3. En *API Keys → Create Key*, copiar la clave (empieza por `sk-ant-`) y pegarla. Botón **Comprobar clave**.

Coste orientativo: unos céntimos por notificación analizada y por escrito redactado.
(Esto lo puede hacer otra persona y darle la clave ya creada.)

### Correo
Elegir el tipo de correo, escribir la dirección y la contraseña, y pulsar **Comprobar correo**.

- **Gmail:** no vale la contraseña normal. Hay que activar la verificación en dos pasos y crear una
  **contraseña de aplicación** en <https://myaccount.google.com/apppasswords> (la pantalla lo explica paso a paso).
- **Outlook / Hotmail / Microsoft 365:** pulsar **Conectar con Outlook**. Sale un código; se abre la página de
  Microsoft, se escribe el código, se entra con la cuenta de siempre y se pulsa *Aceptar*. No hay que crear
  ninguna contraseña. (El programa ya está dado de alta en Microsoft; detalles en [docs/MICROSOFT.md](docs/MICROSOFT.md).)
- El programa **no marca los correos como leídos** ni los borra: solo los lee.
- La primera vez solo mira los correos de los **últimos 7 días**.

### Festivos (en «Ajustes»)
Los nacionales ya van incluidos. Hay que añadir **cada año** los autonómicos y locales (vienen de ejemplo los
de la Comunitat Valenciana y València de 2026, que **hay que revisar** con el calendario oficial del Colegio).

## 3. Uso diario

- **Hoy:** plazos que vencen y novedades sin revisar.
- **Bandeja:** todo lo recibido. Al pinchar en un documento se ve el resumen, qué hay que hacer, los plazos, el
  procedimiento y el PDF original. Botones para **redactar el escrito** o el **correo al abogado**.
- **Subir documentos:** también se pueden **arrastrar los PDF descargados de LexNET**. El programa saca la fecha
  de recepción del propio nombre del archivo (`..._20260923105724_001_...` → 23/09/2026 10:57).
- **Plazos:** marcar la casilla cuando esté hecho. Pinchando en un plazo se puede corregir (días, fecha de
  recepción, si corre en agosto...) y la fecha se vuelve a calcular. Incluye una **calculadora de plazos**.
- **Asuntos** y **Contactos:** se crean solos; se pueden editar, añadir notas o asignar el abogado.
- **Asistente:** elegir el asunto (así la IA lee sus notificaciones) y pedir lo que haga falta.

### Cómo calcula los plazos
1. Si se recibe en día inhábil, cuenta como recibida el siguiente hábil.
2. Notificación a procurador (art. 151.2 LEC): se tiene por hecha el **día hábil siguiente** a la recepción.
3. El plazo empieza a contar el día hábil siguiente a la notificación.
4. Inhábiles: sábados, domingos, festivos, 24 y 31 de diciembre, **agosto** y **24 dic–6 ene** (estos dos se
   pueden desactivar en Ajustes; y en cada plazo se puede marcar que corra en agosto, p. ej. instrucción penal).
5. **Día de gracia** (art. 135.5 LEC): hasta las 15:00 del día hábil siguiente al vencimiento.

## 4. Privacidad y secreto profesional

- Todos los datos (base de datos, PDFs, ajustes) se guardan **solo en este ordenador**, en la carpeta
  `Documentos/Asistente de Procura`.
  El programa solo es accesible desde este mismo ordenador.
- Para analizar documentos y redactar, el texto se envía a la IA de **Anthropic (Claude)**. Según sus condiciones
  comerciales, los datos enviados por la API **no se usan para entrenar** sus modelos. Aun así, conviene
  valorarlo desde el punto de vista del secreto profesional y la protección de datos.
- Las contraseñas se guardan en `data/config.json` en este ordenador: **proteja el ordenador con contraseña**.

## 5. Copias de seguridad

Copie la carpeta **`Documentos/Asistente de Procura`** (por ejemplo a un disco externo o a OneDrive) de vez en
cuando. Ahí está todo. Si algo falla, el archivo `registro.log` de esa carpeta ayuda a saber qué pasó.

## 6. Aranzadi Fusión

Aranzadi Fusión (Thomson Reuters) no tiene, que se sepa, una conexión pública (API) para que otros programas
lean o escriban sus expedientes. Opciones para que convivan:

- **Plazos → Fusión / Outlook:** botón *Plazos → Exportar a calendario* (archivo `.ics`). Si su Fusión sincroniza
  la agenda con Outlook, se importa ahí y aparecen en ambos.
- **Avisos de Fusión → este programa:** si Fusión le envía avisos por correo, este programa los lee y los clasifica.
- **Contactos / expedientes de Fusión → este programa:** si Fusión permite exportar a Excel/CSV, se puede añadir
  una importación (hace falta un ejemplo del archivo exportado).

---

## Para quien mantenga el programa

- Código en `app/` (Python + FastAPI + SQLite), interfaz en `static/` (HTML/JS sin dependencias).
- Pruebas: `python -m pip install -r requirements.txt pytest httpx && python -m pytest`
- Ejecutar desde el código: `python -m app` (o los lanzadores `Iniciar Asistente (...)`); los datos van a `data/`.
- **Publicar una versión nueva:** basta con subir los cambios a la rama principal. GitHub Actions
  (`.github/workflows/instalables.yml`) pasa las pruebas, genera el `.exe` y la `.app` con PyInstaller,
  comprueba que arrancan y los publica en *Releases*. El programa avisa solo de que hay versión nueva.
- Cómo se ha hecho y cómo repetirlo: [`docs/COMO_SE_HIZO.md`](docs/COMO_SE_HIZO.md).
