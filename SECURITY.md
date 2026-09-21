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

- [ ] **A1. `SECRET_KEY` JWT por defecto/vacía**
  `core/config.py` usa una clave de ejemplo y `docker-compose.prod.yml` pasa
  `${SECRET_KEY}` (vacía si no se define) → tokens falsificables.
  _Fix: abortar el arranque en producción si `SECRET_KEY` es débil/ausente._

- [ ] **A2. CSRF en OAuth de Strava**
  `state=current_user.id` predecible y el callback no valida un nonce firmado
  (`routers/strava.py`). Permite vincular cuentas de Strava ajenas.
  _Fix: `state` aleatorio de un solo uso ligado al usuario._

## Medio

- [ ] **M1. Logs filtran tokens de Strava** — `print(response.text)` en
  `routers/strava.py` imprime `access_token`/`refresh_token`.
- [ ] **M2. CORS abierto** — `allow_origins=["*"]` junto a
  `allow_credentials=True` (`main.py`). _Fix: lista blanca._
- [ ] **M3. Sin cabeceras de seguridad** — faltan CSP, HSTS,
  `X-Frame-Options`/`frame-ancestors`, `X-Content-Type-Options`,
  `Referrer-Policy` (app y nginx).
- [ ] **M4. Sin rate limiting** en `/api/auth/login` (fuerza bruta).
- [ ] **M5. Gym/Grades sin autorización** — cualquier usuario autenticado puede
  editar/borrar cualquier gym y sus grades (`routers/gyms.py`,
  `routers/grades.py`).
- [ ] **M6. Cambio de contraseña sin verificar la actual** — `PATCH /auth/me`
  no pide la contraseña actual y no actualiza `password_changed_at`.
- [ ] **M7. Tokens OAuth de Strava en texto plano** en base de datos
  (`models/strava_connection.py`).

## Bajo

- [ ] **B1. Endpoint de prueba `/api/strava/svg-to-gpx`** público y con fuga de
  errores (`str(e)`); eliminar.
- [ ] **B2. `detail=str(e)`** en el callback de Strava (fuga de detalles).
- [ ] **B3. Enumeración de usuarios por timing** en login (no se ejecuta bcrypt
  si el email no existe).
- [ ] **B4. Tokens de invitación en texto plano** (`models/invitation.py`);
  hashear como los de reset.
- [ ] **B5. `get_user_profile`** expone sesiones de cualquier usuario a
  cualquier autenticado (`routers/social.py`).
- [ ] **B6. Dockerfile** corre como root y usa `--reload` también en producción.
- [ ] **B7. `sessions.py`** puede lanzar 500 si la sesión del ejercicio no
  existe (`update_exercise`/`delete_exercise`).
- [ ] **B8. Política de contraseñas débil** (mínimo 6 caracteres).
- [ ] **B9. Bounds de dependencias antiguos** (`python-jose>=3.3.0`,
  `python-multipart>=0.0.6`).
