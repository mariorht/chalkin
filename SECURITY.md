# Chalkin — Checklist de seguridad

Rama de trabajo: `security/hardening`.

Revisión de seguridad de la aplicación (código, plantillas y despliegue). Cada
elemento indica severidad y estado. Marca `[x]` cuando esté corregido y
verificado.

---

## Crítico

- [x] **C1. Stored XSS generalizado por `innerHTML`**
  Campos controlados por el usuario (`username`, `title`, `subtitle`, `notes`,
  `gym_name`, `gym_location`, notas de ejercicios) se insertaban sin escapar vía
  `innerHTML` en:
  `templates/sessions.html`, `templates/feed.html`,
  `templates/user-profile.html`, `templates/stats.html`,
  `templates/session-detail.html`, `templates/friends.html`,
  `templates/dashboard.html`, `templates/gyms.html`, `templates/gym-new.html`,
  `templates/gym-edit.html`, `templates/session-new.html`,
  `templates/admin.html`, `js/app-shell.js`.
  Como el JWT vive en `localStorage`, un XSS exfiltra el token → toma de cuenta.
  _Fix aplicado: helper global `escapeHtml()` en `js/app-shell.js` y escapado en
  todos los puntos (texto y atributos). Pendiente añadir CSP (ver M3)._

- [x] **C2. XSS vía `profile_picture`**
  `UserUpdate.profile_picture` (`schemas/user.py`) permitía fijar una URL
  arbitraria que luego se inyectaba en `src="${...}"` sin escapar.
  _Fix aplicado: eliminado `profile_picture` de `UserUpdate` (solo se fija por
  upload) + escapado en `src`. Test: `test_update_profile_cannot_set_profile_picture`._

- [x] **C3. Subida de ficheros insegura**
  `routers/auth.py` validaba el tipo solo por el header `Content-Type`
  (falsificable) y tomaba la extensión del nombre sin allowlist, sin límite de
  tamaño. Permitía subir `.html`/`.svg` y servirlos inline desde
  `/data/uploads` → XSS almacenado.
  _Fix aplicado: detección por magic bytes, extensión derivada del tipo real,
  Content-Type declarado debe coincidir, límite `max_file_size` y cabecera
  `X-Content-Type-Options: nosniff` en `/data/uploads`. Tests:
  `test_upload_rejects_disguised_html`, `test_upload_rejects_type_mismatch`._

## Alto

- [x] **A1. `SECRET_KEY` JWT por defecto/vacía**
  `core/config.py` usaba una clave de ejemplo y `docker-compose.prod.yml` pasa
  `${SECRET_KEY}` (vacía si no se define) → tokens falsificables.
  _Fix aplicado: validador que impide arrancar si `DEBUG=false` y `SECRET_KEY`
  es vacía o placeholder. Tests: `tests/test_security.py`._

- [x] **A2. CSRF en OAuth de Strava**
  `state=current_user.id` predecible y el callback no validaba un nonce firmado.
  _Fix aplicado: `state` firmado con HMAC-SHA256 y expiración (10 min) vía
  `create_oauth_state`/`verify_oauth_state`; el callback lo verifica. Tests:
  `tests/test_security.py`._

## Medio

- [x] **M1. Logs filtran tokens de Strava** — `print(response.text)` imprimía
  `access_token`/`refresh_token`. _Fix: eliminados los prints; ahora se usa
  `logging` con mensajes sin secretos._
- [x] **M2. CORS abierto** — `allow_origins=["*"]` con `allow_credentials=True`.
  _Fix: lista blanca vía `CORS_ORIGINS` y `allow_credentials=False` (se usa
  Bearer, no cookies)._
- [x] **M3. Sin cabeceras de seguridad** — _Fix: middleware añade
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy` y CSP
  (`frame-ancestors 'none'; base-uri 'self'; object-src 'none'`); nginx añade
  HSTS. **Pendiente**: `script-src` estricto (requiere quitar los `<script>`
  inline o usar nonces; hoy el CSP no bloquea XSS inline)._
- [x] **M4. Sin rate limiting** en `/api/auth/login`. _Fix: limitador en memoria
  (10 fallos / 15 min por email+IP), se resetea al acertar. Tests en
  `tests/test_auth.py`._
- [ ] **M5. Gym/Grades sin autorización** — cualquier usuario autenticado puede
  editar/borrar cualquier gym y sus grades (`routers/gyms.py`,
  `routers/grades.py`). **Requiere decisión de producto** (modelo de propiedad).
- [ ] **M6. Cambio de contraseña sin verificar la actual** — `PATCH /auth/me`
  no pide la contraseña actual y no actualiza `password_changed_at`.
  **Requiere decisión**: exigir la actual e invalidar sesiones se nota en la UX.
- [x] **M7. Tokens OAuth de Strava en texto plano**. _Fix: cifrados con Fernet
  (clave derivada de `SECRET_KEY`, o `TOKEN_ENCRYPTION_KEY` si se define), con
  fallback a texto plano para las conexiones existentes. Tests en
  `tests/test_security.py`._

## Bajo

- [x] **B1. Endpoint de prueba `/api/strava/svg-to-gpx`** público y con fuga de
  errores (`str(e)`). _Fix: eliminado._
- [x] **B2. `detail=str(e)`** en el callback/errores de Strava. _Fix: mensajes
  genéricos + `logging` server-side._
- [x] **B3. Enumeración de usuarios por timing** en login. _Fix: verificación
  bcrypt dummy cuando el email no existe._
- [ ] **B4. Tokens de invitación en texto plano** (`models/invitation.py`);
  hashear como los de reset.
- [ ] **B5. `get_user_profile`** expone sesiones de cualquier usuario a
  cualquier autenticado (`routers/social.py`).
- [ ] **B6. Dockerfile** corre como root y usaba `--reload` en producción.
  _Parcial: `--reload` quitado del `Dockerfile` (sigue en `docker-compose.yml`
  para dev). **Pendiente** ejecutar como usuario no root: requiere un `chown`
  único del volumen `chalkin_data` existente, o la app no podrá escribir la BD._
- [x] **B7. `sessions.py`** podía lanzar 500 si la sesión del ejercicio no
  existe. _Fix: comprobación de `session` nula._
- [x] **B8. Política de contraseñas débil** (mínimo 6 caracteres). _Fix: mínimo
  8 en schemas y formularios._
- [x] **B9. Bounds de dependencias antiguos**. _Fix: `python-jose>=3.4.0`,
  `python-multipart>=0.0.18`._
