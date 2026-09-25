# Integración de Chalkin Sense en Chalkin

Documento de diseño. **No contiene código de implementación**: describe la arquitectura,
el modelo de datos, los flujos de usuario y el plan por fases para integrar el dinamómetro
BLE [Chalkin Sense](../chalkin_sense) en la aplicación web de Chalkin.

> Estado: propuesta / borrador.
> El protocolo BLE de Chalkin Sense aún no está congelado (`chalkin_sense/docs/protocolo-ble.md`),
> por lo que este diseño aísla deliberadamente todo lo específico del dispositivo.

---

## 1. Objetivo

Permitir que un usuario de Chalkin use el sensor **Chalkin Sense** para medir fuerza de
tracción (Peak Force, RFD, TUT) y **guardar esas mediciones dentro de la aplicación**,
en dos contextos:

1. **Entrenamiento**: mediciones ligadas a una sesión de escalada y, opcionalmente, a un
   ejercicio concreto (`SessionExercise`: fingerboard, campus, pullups...).
2. **Prueba / laboratorio**: mediciones **fuera de cualquier entrenamiento**, para
   verificar el sensor, calibrarlo o hacer tests puntuales sin asociarlos a una sesión.

El cliente de prueba actual (`chalkin_sense/app/index.html`) es un visor Web Bluetooth
sin persistencia. Esta integración **reutiliza su lógica BLE** y añade persistencia y
contexto de dominio.

---

## 2. Restricciones y decisiones de alto nivel

### 2.1 Dónde vive cada cosa

| Capa | Responsabilidad |
| :--- | :--- |
| **Navegador (frontend)** | Web Bluetooth: conectar, recibir frames, calcular métricas, mostrar gráfica. Es el **único** sitio donde puede ejecutarse BLE. |
| **Backend (FastAPI)** | Persistir mediciones, agruparlas, exponerlas vía API y servirlas en las vistas. **No habla BLE.** |
| **Dispositivo** | Muestrear el ADS1220, aplicar tara/calibración (NVS), emitir frames batched y responder a comandos de control. |

No se contempla (en esta fase) un *gateway* BLE en servidor (p. ej. `bleak`): el sensor se
conecta directamente al navegador del usuario.

### 2.2 Restricciones del navegador

- Web Bluetooth requiere **contexto seguro**: `https://` o `http://localhost`.
  En producción hay que confirmar que Nginx sirve TLS (`nginx/ssl/`). Sin HTTPS la
  funcionalidad no puede siquiera invocarse.
- Navegadores soportados: Chrome / Edge de escritorio y Chrome en Android.
  **No** funciona en iOS/Safari ni en Firefox.
- Por lo anterior, siempre debe existir un **modo degradado**: registrar una medición
  a mano (peak/RFD/TUT) sin sensor.

### 2.3 Abstracción del protocolo

Los UUIDs y el formato de trama viven hoy en `chalkin_sense/app/index.html`. En Chalkin
se encapsulan en un módulo `SenseClient` (JS) para que un cambio de protocolo no afecte
a las páginas. El backend nunca conoce el formato binario: solo recibe métricas ya
calculadas (y, opcionalmente, series temporales).

### 2.4 Licencias

- Chalkin: **AGPL-3.0**. Chalkin Sense firmware/software: **GPL-3.0**.
  AGPL-3.0 y GPL-3.0 son compatibles; puede reutilizarse el cliente BLE citando autoría.
- El hardware de Chalkin Sense es CERN-OHL-S-2.0 (no afecta al software).

---

## 3. Arquitectura propuesta

```
┌──────────────────────────────────────────────────────────────────────────┐
│ NAVEGADOR (Chalkin)                                                       │
│                                                                           │
│  Página /sense (laboratorio)          Página /sessions/{id} (entreno)    │
│        │                                        │                         │
│        └──────────────┬─────────────────────────┘                         │
│                       ▼                                                   │
│            SenseClient (static/js/chalkin-sense.js)                       │
│            ├── connect() / disconnect()                                   │
│            ├── parseFrame()      (seq, ts, kg)                            │
│            ├── métricas: peak, RFD, TUT                                   │
│            └── eventos: onSample, onPull, onStatus, onError               │
│                       │                                                   │
│                       ▼ fetch (JWT)                                       │
└───────────────────────┼───────────────────────────────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────────────────────────────┐
│ BACKEND (FastAPI)                                                          │
│  /api/measurements ............ mediciones sueltas (test/lab)             │
│  /api/sessions/{id}/measurements   mediciones de entrenamiento            │
│  /api/sessions/{id}/exercises/{eid}/measurements  (opcional)             │
│                                                                            │
│  Modelo ForceMeasurement ──► Session (nullable)                            │
│                          └─► SessionExercise (nullable)                   │
└───────────────────────────────────────────────────────────────────────────┘
                        │ BLE (directo, fuera del backend)
                        ▼
                 [ Chalkin Sense (ESP32-C3 + ADS1220) ]
```

---

## 4. Modelo de dominio

### 4.1 Entidad central: `ForceMeasurement`

Representa **un pull / una medición**. Es la unidad que el sensor produce y el usuario
quiere guardar.

Campos propuestos:

| Campo | Tipo | Notas |
| :--- | :--- | :--- |
| `id` | int PK | |
| `user_id` | FK users | **Obligatorio**. Toda medición tiene dueño. |
| `session_id` | FK sessions, nullable | `NULL` ⇒ medición de prueba/laboratorio. |
| `exercise_id` | FK session_exercises, nullable | Solo si se midió dentro de un ejercicio. |
| `context` | enum/str | `training` \| `test` \| `calibration`. Derivado o explícito. |
| `source` | str | `sense` \| `manual`. |
| `peak_force_kg` | float | Métrica principal. |
| `rfd_kg_s` | float | Tasa de desarrollo de fuerza (primeros 100–200 ms). |
| `tut_s` | float | Tiempo bajo tensión. |
| `avg_force_kg` | float, nullable | Media del pull. |
| `duration_ms` | int, nullable | Duración del pull. |
| `sample_count` | int, nullable | Nº de muestras agregadas. |
| `labeled_as` | str, nullable | Etiqueta libre: "MMS 20mm", "test batería"... |
| `notes` | text, nullable | |
| `raw_samples` | text/JSON, nullable | Serie opcional (ver 4.3). |
| `device_name` | str, nullable | p. ej. "ChalkinSense". |
| `firmware_version` | str, nullable | Snapshot informativo. |
| `calibration_factor` | float, nullable | Coeficiente usado, por trazabilidad. |
| `measured_at` | datetime | Timestamp del dispositivo/real. |
| `created_at` | datetime | |

### 4.2 Agrupación opcional: `SenseTest`

Para el **modo laboratorio** conviene agrupar varias mediciones sueltas en una "prueba"
con nombre (p. ej. "Comprobación de sensor 2026-09-21"): batería de pulls, verificación
tras calibración, comparación de agarres, etc.

| Campo | Tipo |
| :--- | :--- |
| `id` | int PK |
| `user_id` | FK users |
| `name` | str |
| `notes` | text, nullable |
| `created_at` | datetime |

`ForceMeasurement` añadiría `test_id` (FK nullable). Decisión abierta (ver §10):
si merece la pena la entidad de agrupación desde el principio o se pospone.

### 4.3 ¿Guardar muestras crudas?

Tres opciones:

1. **Solo resumen** (peak/RFD/TUT/avg): ligero, suficiente para el MVP.
2. **Resumen + serie reducida**: guardar la curva completa pero *downsampleada* (p. ej.
   ~50 puntos por pull) en `raw_samples` (JSON en la misma fila). Buen equilibrio.
3. **Serie completa** en tabla/archivo aparte: máximo detalle (reanálisis, nuevas
   métricas), pero mucho volumen (175–330 SPS).

Recomendación: **opción 2** por defecto; opción 3 más adelante si aparecen features de
análisis de curvas de fuerza/fatiga. En modo laboratorio puede habilitarse la 3.

### 4.4 Relaciones

- `User 1─N ForceMeasurement`
- `Session 1─N ForceMeasurement` (solo `context=training`)
- `SessionExercise 1─N ForceMeasurement` (opcional)
- `User 1─N SenseTest 1─N ForceMeasurement` (solo `context=test`)

Las mediciones de laboratorio **no** deben aparecer en stats de entrenamiento ni en el
feed social; se filtran por `context`.

---

## 5. Modo prueba de sensores ("laboratorio")

Requisito explícito: poder **probar el sensor sin que sea un entrenamiento**.

### 5.1 Concepto

Una página independiente **`/sense`** ("Chalkin Sense · Laboratorio") que funciona sin
sesión de escalada y sin gimnasio. Su propósito:

- **Verificar que el dispositivo responde** (conexión BLE, streaming, batería).
- **Calibrar / tarar** y ver la calibración actual (`TARA`, `CAL`, `GETCAL`).
- **Hacer pulls de prueba** y ver métricas en vivo (gráfica tipo osciloscopio).
- **Guardar** las mediciones como `context=test`, opcionalmente agrupadas en un `SenseTest`.
- **Descartar** mediciones que no interesan (botón "no guardar").

Esta página es esencialmente la evolución del cliente actual
(`chalkin_sense/app/index.html`), con estética Chalkin (`app-shell.css`, `AppShell`) y
persistencia.

### 5.2 Diferencias frente al modo entrenamiento

| Aspecto | `/sense` (laboratorio) | Dentro de `/sessions/{id}` |
| :--- | :--- | :--- |
| Sesión | No requerida | Requerida |
| Gimnasio | No | Sí (el de la sesión) |
| Contexto guardado | `test` | `training` |
| Agrupación | `SenseTest` opcional | `SessionExercise` opcional |
| Aparece en stats/feed | No | Sí |
| Objetivo | Diagnóstico / calibración / test | Registro de entrenamiento |
| Curvas crudas | Probable | Probablemente no |

### 5.3 Flujo de "promoción"

Un pull guardado en laboratorio puede **promoverse** a un entrenamiento: desde la
medición, acción "Asociar a sesión…" que rellena `session_id`/`exercise_id` y cambia
`context` a `training`. Esto evita tener que repetir el pull si el usuario decide
después que sí contaba.

### 5.4 Casos de uso del laboratorio

- "¿Está bien calibrado?" → `GETCAL` + pull conocido.
- "¿El sensor está roto?" → mirar ruido en reposo, respuesta a `SIM_PULL`.
- "Quiero medir mi máximo" → test puntual sin crear sesión de gimnasio.
- "Comparar agarres en fingerboard" → batería de pulls etiquetados en un `SenseTest`.

---

## 6. Protocolo BLE (resumen operativo)

Tomado de `chalkin_sense/docs/protocolo-ble.md`. **Solo el frontend lo conoce.**

- Servicio: `8f3a2b1e-5c4a-4d6e-9f20-4a1b2c3d4e5f`
- Fuerza (NOTIFY): `...4e60`, frames *batched* little-endian:
  `uint16 seq · uint8 count · count × (uint32 ts_ms + float32 kg)`
- Control (WRITE/READ/NOTIFY): `...4e61`, comandos ASCII terminados en `\n`:
  `TARA`, `CAL <kg>`, `GETCAL`, `STATS`, `RESET`, `SIM_PULL`, `SIM_AUTO <0|1>`.
- El cliente usa el **timestamp de cada muestra** (no el de llegada) y el `seq` para
  detectar pérdidas. No asume tasa fija.

`SenseClient` expone `version`/feature-detection para tolerar cambios de protocolo y
degradar con elegancia si el firmware cambia.

---

## 7. Backend: componentes

### 7.1 Archivos nuevos (mismo patrón que `SessionExercise`)

- `src/app/models/force_measurement.py` (+ `sense_test.py` si se aprueba §4.2)
- `src/app/schemas/force_measurement.py`
- `src/app/routers/measurements.py` (o extender `sessions.py`, ver §7.3)
- Migración Alembic `012_add_force_measurements.py` (la última existente es `011_hash_invitation_tokens.py`)

Y editar:

- `src/app/models/__init__.py` (registrar el modelo)
- `src/app/models/session.py` (relación `measurements`)
- `src/app/models/session_exercise.py` (relación opcional)
- `src/app/main.py` (registrar router + servir `/sense`)

### 7.2 Endpoints propuestos

**Mediciones de entrenamiento** (anidadas, como `exercises`):

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| POST | `/api/sessions/{id}/measurements` | Crear medición en sesión. |
| GET | `/api/sessions/{id}/measurements` | Listar (propia o de amigo). |
| PATCH | `/api/measurements/{id}` | Editar etiqueta/notas/ejercicio. |
| DELETE | `/api/measurements/{id}` | Borrar. |

**Mediciones de laboratorio**:

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| POST | `/api/measurements` | Crear medición `context=test`. |
| GET | `/api/measurements?context=test` | Listar las del usuario. |
| POST | `/api/measurements/{id}/promote` | Asociar a sesión/ejercicio. |
| POST/GET | `/api/sense-tests` | Agrupaciones de laboratorio (si §4.2). |

Todos requieren `get_current_user`; se aplican las mismas reglas de visibilidad que en
`sessions.py` (propias o de amigos) para el contexto `training`.

### 7.3 ¿Router propio o dentro de `sessions.py`?

- `measurements.py` propio: más limpio, ya que hay endpoints de laboratorio fuera de sesión.
- Los anidados bajo `/sessions/{id}/...` pueden registrarse en el mismo router con prefijo.

Recomendación: **router propio** `measurements.py`, registrado en `main.py`, con rutas
tanto anidadas como sueltas.

---

## 8. Frontend: componentes

### 8.1 Módulo reutilizable `static/js/chalkin-sense.js`

Extraído de `chalkin_sense/app/index.html`, generalizado:

- `SenseClient.connect()` / `disconnect()`
- Parser de frames y detección de pérdidas
- Cálculo de métricas (mismas reglas que el firmware)
- API de eventos: `onSample`, `onPullEnd`, `onStatus`, `onCommand`
- `sendCommand(cmd)`, helpers `calibrate(kg)`, `tare()`, `getCalibration()`
- Sin DOM ni `fetch`: la UI y la persistencia quedan fuera (testable y reutilizable).

### 8.2 Páginas

| Página | Ruta | Rol |
| :--- | :--- | :--- |
| Laboratorio | `/sense` | Modo prueba fuera de entrenamiento. Nueva plantilla `templates/sense.html`. |
| Detalle de sesión | `/sessions/{id}` | Botón "Conectar Chalkin Sense" en la sección de ejercicios (`session-detail.html:1010+`). |
| Historial | `/sense/history` (opcional) | Lista de `SenseTest` y mediciones de laboratorio. |

### 8.3 UI de laboratorio (qué reutilizar)

Del cliente actual se conservan: indicadores (fuerza, pico, RFD, TUT), gráfica en
`<canvas>`, panel de log, controles de calibración y comandos de simulación. Se añade:

- Botones **Guardar pull** / **Descartar**.
- Selector de `SenseTest` (o "sin agrupar").
- Aviso claro de compatibilidad de navegador y de contexto seguro.
- Estética con `app-shell.css` + `AppShell.init()`.

### 8.4 Flujo en entrenamiento

1. En la sesión, sección ejercicios → "Conectar Chalkin Sense" (abre panel o navega a la vista embebida).
2. Al terminar un pull, se muestra pico/RFD/TUT y un botón "Guardar en esta sesión".
3. Se asocia al ejercicio seleccionado (fingerboard/campus/…) o queda a nivel de sesión.
4. Todo va con `context=training`.

---

## 9. Seguridad, privacidad y límites

- Las mediciones son datos del usuario; las de `context=test` **nunca** se publican en
  feed/ranking.
- Validar rangos en los schemas (p. ej. `peak_force_kg >= 0`, `tut_s >= 0`) para evitar
  datos absurdos (manual o sensor sin calibrar).
- Limitar el tamaño de `raw_samples` en servidor (p. ej. máx. N puntos) para no inflar la BD.
- Las mediciones importadas manualmente se marcan `source=manual` (trazabilidad).
- Sin cambios de autenticación: se reutiliza JWT y `get_current_user`.

---

## 10. Decisiones abiertas

1. **Agrupación `SenseTest`**: ¿entidad propia desde el inicio o simples `ForceMeasurement`
   con `context=test` y `labeled_as`? (Recomendado: empezar sin `SenseTest`, añadir después.)
2. **Series crudas**: ¿guardar en la fila (JSON) o tabla aparte? (Recomendado: JSON reducido.)
3. **Promoción de test → entrenamiento**: ¿solo vía `session_id`, o también reasignar
   ejercicio? (Recomendado: ambos.)
4. **Stats**: ¿incluir métricas de fuerza (mejor peak, evolución de RFD) en `/stats`?
   ¿Solo `context=training`? (Recomendado: sí, solo training, en fase posterior.)
5. **HTTPS**: confirmar TLS en `docker-compose.prod.yml` + `nginx/`; sin él, el modo sensor
   no es utilizable en producción.
6. **Vincular repos**: ¿copiar `chalkin-sense.js` a Chalkin, o consumir el repo
   `chalkin_sense` como submódulo para compartir el protocolo?

---

## 11. Plan de implementación por fases

**Fase 0 — Fundaciones (este documento)**
- Rama `feat/chalkin-sense-integration`, diseño acordado, decisiones de §10 resueltas.

**Fase 1 — Backend**
- Modelo `ForceMeasurement` (+ migración 012), schemas, endpoints CRUD y `promote`.
- Tests de API (patrón de `tests/`).

**Fase 2 — Cliente BLE**
- Extraer y generalizar `SenseClient` en `static/js/chalkin-sense.js`.
- Tests manuales contra el firmware en modo simulación (`esp32-c3-sim`, `SIM_PULL`).

**Fase 3 — Modo laboratorio (`/sense`)**
- Plantilla `sense.html` + `AppShell`; conectar, ver métricas, calibrar, guardar/descartar.
- Guardado como `context=test`; historial básico.

**Fase 4 — Integración en entrenamiento**
- Botón en `session-detail.html`, asociación a ejercicio, `context=training`.

**Fase 5 — Extras**
- Modo manual (sin sensor), promoción test→entreno, métricas en `/stats`, curvas crudas.

---

## 12. Criterios de aceptación

- Se puede **conectar** al Chalkin Sense desde Chalkin (Chrome, contexto seguro) y ver
  fuerza en vivo.
- Se puede **guardar un pull** en una sesión de entrenamiento y verlo en el detalle.
- Se puede **probar el sensor sin sesión** en `/sense` y guardar/descartar el resultado.
- Las mediciones de laboratorio **no** contaminan stats ni feed.
- El backend funciona igual si el sensor no está (modo manual).
