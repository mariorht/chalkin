# Superliga (ligas / competiciones)

Chalkin soporta eventos de liga tipo Superliga del Boulder Up: un evento en un
gimnasio concreto que dura varias semanas y en el que cada bloque completado
suma puntos según su dificultad.

## Cómo funciona

- **Evento**: un `Competition` está atado a un gimnasio y tiene fecha de inicio
  y fin. Las semanas son **naturales, de lunes a domingo**: la semana 1 va desde
  `start_date` hasta el primer domingo, y a partir de ahí cada semana va de lunes
  a domingo. La primera y la última pueden ser parciales.
- **Semanas de descanso**: el admin marca qué semanas son de descanso
  (`week_offsets`). En una semana de descanso no se pueden marcar bloques de liga
  ni puntúan.
- **Puntos**: se definen **por grado** (`CompetitionPoint`). En Boulder Up los
  grados son colores, así que cada color vale lo que el admin decida.
- **Marcar un bloque**: al registrar un bloque, si la sesión es en el gimnasio
  del evento y la fecha cae dentro del evento (y no es descanso), aparece un
  toggle "Superliga". Al marcarlo se pide el **número de bloque** (obligatorio,
  1..N) y el ascent guarda `competition_id` + `competition_block`.
- **Participación**: es implícita. En cuanto marcas un bloque de liga, entras en
  la clasificación. Cualquier participante puede ver la clasificación completa
  (no solo amigos).
- **Puntuación**: un bloque puntúa **una vez por (usuario, semana, número de
  bloque)**. Repetir el mismo bloque no vuelve a sumar, pero el mismo número en
  otra semana es otro bloque y sí puntúa. Proyectos e intentos no puntúan.
- **Desglose**: en la pestaña "Total" cada fila de la clasificación se puede
  pulsar para ver, grado a grado, cuántos bloques resolvió esa persona, qué
  números de bloque eran (`#1 #4`) y cuántos puntos aporta cada grado.

## Crear y configurar un evento (panel de administración)

1. Entra en **Administración** (`/admin`) con un usuario admin.
2. En la sección **Ligas**, pulsa **+ Nueva liga**.
3. Rellena nombre, gimnasio, descripción, fechas de inicio y fin, y estado.
4. En **Puntos por grado**, asigna puntos a cada color (el grado que dejes a 0 no
   puntúa).
5. Pulsa **Calcular semanas**, revisa las semanas generadas y **desmarca** las que
   sean de descanso.
6. Guarda. La liga aparece en la lista y, si está activa y en fecha, en el
   dashboard de los usuarios.

Se puede editar en cualquier momento (botón **Editar**) o borrar. También se
puede enlazar directamente a la edición con `/admin?edit=<id>`.

## API

| Método | Ruta | Quién | Descripción |
| --- | --- | --- | --- |
| GET | `/api/competitions` | auth (opcional) | Lista eventos (borradores solo admin) |
| GET | `/api/competitions/running?gym_id=` | auth | Evento activo hoy en ese gimnasio (o `null`) |
| POST | `/api/competitions` | admin | Crear evento con sus puntos |
| GET | `/api/competitions/{id}` | auth (opcional) | Detalle con puntos |
| PATCH | `/api/competitions/{id}` | admin | Editar fechas/nombre/estado/descansos |
| PUT | `/api/competitions/{id}/points` | admin | Reemplazar tabla de puntos |
| DELETE | `/api/competitions/{id}` | admin | Borrar evento |
| GET | `/api/competitions/{id}/leaderboard` | participante | Clasificación total y por semanas |

Ejemplo de creación por API:

```json
POST /api/competitions
{
  "gym_id": 1,
  "name": "Superliga BouldeUp",
  "start_date": "2026-09-29",
  "end_date": "2026-11-23",
  "status": "active",
  "week_offsets": [5],
  "points": [{"grade_id": 1, "points": 5}, {"grade_id": 2, "points": 10}]
}
```

Y marcar un bloque de liga al registrarlo:

```json
POST /api/sessions/{session_id}/ascents
{
  "grade_id": 5,
  "status": "send",
  "competition_id": 1,
  "competition_block": 7
}
```

`competition_block` es obligatorio cuando `competition_id` viene informado.

## Páginas

- `/competitions`: lista de ligas.
- `/competitions/{id}`: detalle con puntos por color y clasificación por semanas.
  Las semanas de descanso se marcan en rojo.
- Dashboard: sección **Ligas** con eventos **en curso**, **próximas** y
  **finalizadas**.

## Cerrar entrenamientos abiertos (cron)

Las actividades que se quedan abiertas para siempre se cierran con
`src/close_stale_sessions.py`. En el servidor, añadir al crontab de root:

```cron
0 4 * * * docker compose -f /root/chalkin/docker-compose.prod.yml exec -T api python close_stale_sessions.py >> /root/daily_backups/close_stale.log 2>&1
```
