# Dar de alta el programa en Microsoft (una sola vez)

Necesario para el botón **«Conectar con Outlook»**. Microsoft ya no deja que los programas lean el correo
con usuario y contraseña; hay que registrar el programa y que la usuaria lo autorice con su cuenta.

Lo hace **quien instala el programa**, una sola vez. Tarda unos 10 minutos. La usuaria no tiene que hacer nada
de esto.

## Pasos

1. Entra en <https://entra.microsoft.com> con **tu** cuenta de Microsoft (puede ser personal: @outlook.com,
   @hotmail.com...).
   - Si dice que tu cuenta no tiene acceso o que necesitas un «inquilino/directorio», crea antes una cuenta
     gratuita de Azure en <https://azure.microsoft.com/free> (puede pedir una tarjeta para verificar la
     identidad; el registro de aplicaciones es gratis) y vuelve a este paso.
2. Menú izquierdo: **Aplicaciones → Registros de aplicaciones → + Nuevo registro**.
   - **Nombre:** `Asistente de Procura`
   - **Tipos de cuenta compatibles:** *«Cuentas en cualquier directorio organizativo (cualquier inquilino de
     Microsoft Entra ID: multiinquilino) y cuentas Microsoft personales (como Skype o Xbox)»*.
     ⚠️ Esta opción es importante: si se elige otra, no funcionará con @outlook.com / @hotmail.com.
   - **URI de redirección:** déjalo vacío.
   - Pulsa **Registrar**.
3. En la página que aparece, copia el **«Id. de aplicación (cliente)»** (tiene la forma
   `1a2b3c4d-....-....-....-............`). **Este es el dato que hay que pasar.**
4. Menú izquierdo de la aplicación: **Autenticación** → abajo del todo, **«Permitir flujos de clientes
   públicos» → Sí** → **Guardar**.
5. Menú izquierdo: **Permisos de API → + Agregar un permiso → Microsoft Graph → Permisos delegados**. Busca y
   marca:
   - `IMAP.AccessAsUser.All`
   - `offline_access`

   Pulsa **Agregar permisos**. (No hace falta «conceder consentimiento de administrador».)

## Qué hacer con el identificador

- **Lo normal:** pásalo en la conversación con Claude y se incluye en el programa (`CLIENT_ID_POR_DEFECTO` en
  `app/microsoft.py`). La siguiente versión ya lo lleva y la usuaria solo tiene que pulsar «Conectar con Outlook».
- **Para probar ya, sin esperar a otra versión:** en el programa, *Ajustes → Correo → Forma de conectar: Cuenta
  de Microsoft → Avanzado* → pegar el identificador → *Guardar ajustes*.

El identificador no es secreto (no permite leer ningún correo por sí solo): cada persona tiene que iniciar
sesión con su cuenta y aceptar.

## Si al conectar sale un error

| Mensaje | Qué pasa | Solución |
|---|---|---|
| «...not a valid application identifier» | Identificador mal copiado | Copiarlo de nuevo (paso 3) |
| «...must be 'client_assertion' or 'client_secret'» / «AADSTS7000218» | Falta el paso 4 | Activar «Permitir flujos de clientes públicos» |
| «...not configured for personal accounts» / «unauthorized_client» | Tipo de cuenta mal elegido en el paso 2 | En *Autenticación* (o *Manifiesto*) cambiar a «cuentas organizativas y personales» |
| «...administrador...» / «AADSTS65001» | El correo es de una organización (despacho, Colegio) que no deja autorizar programas | Pedir al administrador del correo que lo autorice |
| «AUTHENTICATE failed» al comprobar el correo | El acceso IMAP está desactivado en la cuenta | Outlook.com: *Configuración → Correo → Reenvío e IMAP → Permitir que los dispositivos y las aplicaciones usen IMAP*. Microsoft 365: el administrador debe activar IMAP para el buzón |
