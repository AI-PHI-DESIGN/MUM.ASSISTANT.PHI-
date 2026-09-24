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

## 1. Instalación (una sola vez)

1. **Instalar Python** desde <https://www.python.org/downloads/>.
   En Windows, en la primera pantalla del instalador, **marcar la casilla «Add python.exe to PATH»**.
2. **Descargar este programa**: en GitHub, botón verde **Code → Download ZIP**. Descomprimirlo en una carpeta
   fija, por ejemplo `Documentos\Asistente de Procura`.
3. Hacer doble clic en **`Iniciar Asistente (Windows).bat`** (o en `Iniciar Asistente (Mac).command` en un Mac).
   La primera vez tarda un par de minutos en instalarse. Después se abre el navegador solo.
   - Windows puede mostrar «Windows protegió su PC»: pulsar *Más información → Ejecutar de todas formas*.
   - **No cierre la ventana negra** mientras use el programa. Si la cierra, el programa se para.
4. Truco: clic derecho sobre el `.bat` → *Enviar a → Escritorio (crear acceso directo)* para tenerlo a mano.

## 2. Configuración (pestaña «Ajustes»)

### Nombre
Ponga su nombre **tal como aparece en las notificaciones** (p. ej. «MARÍA GARCÍA LÓPEZ»). Así la IA sabe cuál es
«nuestra parte» en cada procedimiento.

### Clave de la IA (Anthropic)
1. Entrar en <https://console.anthropic.com> y crear una cuenta.
2. En *Billing*, añadir saldo (con 10–20 € hay para bastante tiempo; se paga por uso).
3. En *API Keys → Create Key*, copiar la clave (empieza por `sk-ant-`) y pegarla en Ajustes.

Coste orientativo: unos céntimos por notificación analizada y por escrito redactado.

### Correo
Hay que marcar «Revisar el correo automáticamente» y rellenar:

| Correo | Servidor IMAP | Puerto |
|---|---|---|
| Gmail | `imap.gmail.com` | 993 |
| Outlook / Hotmail / Microsoft 365 | `outlook.office365.com` | 993 |
| Otro (del despacho, Colegio...) | lo indica su proveedor | 993 |

- **Gmail:** no vale la contraseña normal. Hay que activar la verificación en dos pasos y crear una
  **contraseña de aplicación** en <https://myaccount.google.com/apppasswords>; se pega esa (16 letras).
- **Outlook / Microsoft 365:** Microsoft bloquea este tipo de acceso en muchas cuentas. Si da error, lo más fácil
  es **reenviar automáticamente** el correo a una cuenta de Gmail y conectar esa.
- El programa **no marca los correos como leídos** ni los borra: solo los lee.
- La primera vez solo mira los correos de los **últimos 7 días**.

### Festivos
Los nacionales ya van incluidos. Hay que añadir **cada año** los autonómicos y locales (vienen de ejemplo los
de la Comunitat Valenciana y València de 2026, que **hay que revisar** con el calendario oficial del Colegio).
Si un asunto es de un juzgado de otra localidad con otro festivo local, conviene añadirlo también.

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

- Todos los datos (base de datos, PDFs, ajustes) se guardan **solo en este ordenador**, en la carpeta `data`.
  El programa solo es accesible desde este mismo ordenador.
- Para analizar documentos y redactar, el texto se envía a la IA de **Anthropic (Claude)**. Según sus condiciones
  comerciales, los datos enviados por la API **no se usan para entrenar** sus modelos. Aun así, conviene
  valorarlo desde el punto de vista del secreto profesional y la protección de datos.
- Las contraseñas se guardan en `data/config.json` en este ordenador: **proteja el ordenador con contraseña**.

## 5. Copias de seguridad

Copie la carpeta **`data`** (por ejemplo a un disco externo o a OneDrive) de vez en cuando. Ahí está todo.

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
- Cómo se ha hecho y cómo repetirlo: [`docs/COMO_SE_HIZO.md`](docs/COMO_SE_HIZO.md).
