# Sistema de Invitaciones - Chalkin

## Resumen

Se ha implementado un sistema de registro por invitación para controlar el crecimiento de usuarios en la plataforma.

## Características

- **Registro restringido**: Solo se pueden registrar nuevos usuarios con un link de invitación válido
- **Generación de invitaciones**: Los usuarios autenticados pueden generar links de invitación desde su página de perfil
- **Validez temporal**: Cada invitación es válida por 24 horas
- **Un solo uso**: Cada invitación solo puede ser usada una vez
- **Tracking completo**: Se registra quién creó cada invitación y quién la usó

## Cambios Realizados

### Backend

1. **Nuevo modelo: Invitation** (`src/app/models/invitation.py`)
   - Token único de invitación
   - Referencia al usuario creador
   - Fecha de expiración (24 horas)
   - Estado de uso y tracking

2. **Nueva migración**: `008_add_invitations.py`
   - Crea la tabla `invitations` en la base de datos

3. **Nuevos schemas** (`src/app/schemas/invitation.py`)
   - `InvitationCreate`: Para crear invitaciones
   - `InvitationResponse`: Respuesta con datos de invitación
   - `InvitationLink`: Link de invitación para compartir

4. **Nuevo router** (`src/app/routers/invitations.py`)
   - `POST /api/invitations/generate`: Genera nueva invitación
   - `GET /api/invitations/validate/{token}`: Valida un token
   - `GET /api/invitations/my-invitations`: Lista invitaciones del usuario

5. **Modificación del registro** (`src/app/routers/auth.py`)
   - Ahora requiere `invitation_token` en el registro
   - Valida que la invitación sea válida, no usada y no expirada
   - Marca la invitación como usada tras registro exitoso

6. **Schema UserCreate actualizado**
   - Añadido campo opcional `invitation_token`

### Frontend

1. **Página de Perfil** (`profile.html`)
   - Nueva sección "Invitar Amigos" debajo del botón de Strava
   - Botón para generar link de invitación
   - Input para copiar el link generado
   - Funciones JS: `generateInvitation()` y `copyInvitationLink()`

2. **Página de Registro** (`register.html`)
   - Mensaje de "Registro Restringido" cuando no hay token
   - Validación automática del token de invitación en la URL
   - Formulario deshabilitado sin token válido
   - Envío del token al backend durante el registro

## Uso

### Para generar una invitación

1. Ir a la página de perfil (mientras estás autenticado)
2. Scroll hasta la sección "Invitar Amigos"
3. Clic en "Generar Link de Invitación"
4. Copiar el link generado
5. Compartir con la persona que quieres invitar

### Para registrarse con invitación

1. Recibir el link de invitación (ej: `https://chalkin.app/register?invitation=ABC123...`)
2. Abrir el link en el navegador
3. Completar el formulario de registro
4. El sistema validará automáticamente la invitación

## Migraciones de Base de Datos

Para aplicar la nueva migración en producción:

```bash
# Desde el directorio src/
alembic upgrade head
```

O si usas Docker:

```bash
docker-compose exec app alembic upgrade head
```

## Seguridad

- Los tokens de invitación son generados con `secrets.token_urlsafe(32)` (alta entropía)
- Las invitaciones expiran automáticamente después de 24 horas
- Cada invitación solo puede usarse una vez
- Se valida la invitación antes de permitir el registro

## Consideraciones Futuras

Posibles mejoras que se podrían implementar:

- Dashboard de administrador para gestionar invitaciones
- Límite de invitaciones por usuario
- Invitaciones ilimitadas para usuarios premium
- Estadísticas de conversión de invitaciones
- Notificaciones cuando alguien usa tu invitación
