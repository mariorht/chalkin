# Superliga (ligas / competiciones)

Chalkin soporta eventos de liga tipo Superliga del Boulder Up: un evento en un
gimnasio concreto que dura varias semanas y en el que cada bloque completado
suma puntos según su dificultad.

## Cómo funciona

- **Evento**: un `Competition` está atado a un gimnasio y tiene fecha de inicio
  y fin. Las semanas se derivan del calendario (semana 1 empieza en `start_date`,
  cada 7 días), así que no hay que definir cada semana a mano.
- **Puntos**: se definen **por grado** (`CompetitionPoint`). En Boulder Up los
  grados son colores, así que cada color vale lo que el admin decida.
- **Marcar un bloque**: al registrar un bloque, si la sesión es en el gimnasio
  del evento y la fecha cae dentro del evento, aparece un toggle "Superliga".
  Al marcarlo, el ascent guarda `competition_id`.
- **Participación**: es implícita. En cuanto marcas un bloque de liga, entras en
  la clasificación. Cualquier participante puede ver la clasificación completa
  (no solo amigos).
- **Puntuación**: un bloque puntúa **una vez por (usuario, grado, día)**. Repetir
  el mismo bloque el mismo día no vuelve a sumar. Proyectos e intentos no
  puntúan.

## API

| Método | Ruta | Quién | Descripción |
| --- | --- | --- | --- |
| GET | `/api/competitions` | auth (opcional) | Lista eventos (borradores solo admin) |
| GET | `/api/competitions/running?gym_id=` | auth | Evento activo hoy en ese gimnasio (o `null`) |
| POST | `/api/competitions` | admin | Crear evento con sus puntos |
| GET | `/api/competitions/{id}` | auth (opcional) | Detalle con puntos |
| PATCH | `/api/competitions/{id}` | admin | Editar fechas/nombre/estado |
| PUT | `/api/competitions/{id}/points` | admin | Reemplazar tabla de puntos |
| DELETE | `/api/competitions/{id}` | admin | Borrar evento |
| GET | `/api/competitions/{id}/leaderboard` | participante | Clasificación total y por semanas |

## Páginas

- `/competitions`: lista de ligas.
- `/competitions/{id}`: detalle con puntos por color y clasificación por semanas.

## Cerrar entrenamientos abiertos (cron)

Las actividades que se quedan abiertas para siempre se cierran con
`src/close_stale_sessions.py`. En el servidor, añadir al crontab de root:

```cron
0 4 * * * docker compose -f /root/chalkin/docker-compose.prod.yml exec -T api python close_stale_sessions.py >> /root/daily_backups/close_stale.log 2>&1
```
