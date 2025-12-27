# Integración con Strava

Esta guía explica cómo configurar y usar la integración con Strava en Chalkin.

## Configuración

### 1. Registrar tu aplicación en Strava

1. Ve a [strava.com/settings/api](https://www.strava.com/settings/api)
2. Completa el formulario:
   - **Application Name**: Chalkin (o el nombre que prefieras)
   - **Category**: Training
   - **Club**: (opcional)
   - **Website**: Tu dominio o `http://localhost:8000` para desarrollo
   - **Authorization Callback Domain**: 
     - Desarrollo: `localhost`
     - Producción: `tudominio.com` (sin http/https)
3. Guarda el **Client ID** y el **Client Secret**

### 2. Configurar variables de entorno

Añade estas variables a tu archivo `.env`:

```env
STRAVA_CLIENT_ID=tu_client_id_aqui
STRAVA_CLIENT_SECRET=tu_client_secret_aqui
STRAVA_REDIRECT_URI=http://localhost:8000/api/strava/callback
```

Para producción, cambia la URL del callback:
```env
STRAVA_REDIRECT_URI=https://tudominio.com/api/strava/callback
```

### 3. Ejecutar migración de base de datos

```bash
cd src
alembic upgrade head
```

Esto creará la tabla `strava_connections` en tu base de datos.

## Uso

### Conectar cuenta de Strava

1. Ve a tu perfil en la aplicación
2. En la sección "🏃 Conexión con Strava", haz clic en **Conectar**
3. Serás redirigido a Strava para autorizar la aplicación
4. Después de autorizar, volverás automáticamente a tu perfil con la cuenta conectada

### Desconectar cuenta

1. En tu perfil, haz clic en **Desconectar** en la sección de Strava
2. Confirma la acción

## API Endpoints

### `GET /api/strava/connect`
Inicia el flujo OAuth2. Requiere autenticación.

### `GET /api/strava/callback`
Endpoint de callback después de la autorización. No llamar directamente.

### `GET /api/strava/status`
Obtiene el estado de la conexión del usuario actual.

**Respuesta:**
```json
{
  "connected": true,
  "athlete_id": 12345678,
  "expires_at": 1703692800,
  "is_expired": false,
  "scope": "read,activity:write"
}
```

### `DELETE /api/strava/disconnect`
Desconecta la cuenta de Strava del usuario actual.

### `POST /api/strava/refresh-token`
Renueva el token de acceso usando el refresh token. Los tokens de Strava expiran cada 6 horas.

## Modelo de datos

La tabla `strava_connections` almacena:

- `user_id`: ID del usuario (única)
- `athlete_id`: ID del atleta en Strava
- `access_token`: Token de acceso (expira en 6h)
- `refresh_token`: Token para renovar el access_token
- `expires_at`: Timestamp de expiración del access_token
- `scope`: Permisos concedidos
- `created_at` / `updated_at`: Timestamps

## Próximos pasos

Para subir entrenamientos a Strava, necesitarás:

1. **Crear endpoint de subida**: 
   - POST `/api/strava/upload` para subir archivos GPX/FIT/TCX
   
2. **Gestionar tokens expirados**:
   - Verificar `expires_at` antes de cada petición
   - Llamar automáticamente a `/api/strava/refresh-token` si está expirado
   
3. **Verificar estado de subida**:
   - Las subidas son asíncronas en Strava
   - Necesitas consultar el estado periódicamente

## Ejemplo: Subir una actividad

```python
import httpx
from datetime import datetime

async def upload_to_strava(
    access_token: str,
    file_path: str,
    activity_type: str = "Workout"
):
    """
    Sube un archivo de entrenamiento a Strava.
    
    Args:
        access_token: Token de acceso válido
        file_path: Ruta al archivo .gpx, .fit o .tcx
        activity_type: Tipo de actividad (Workout, Ride, Run, etc.)
    """
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'data_type': 'gpx',  # o 'fit', 'tcx'
                'activity_type': activity_type
            }
            
            response = await client.post(
                'https://www.strava.com/api/v3/uploads',
                headers={'Authorization': f'Bearer {access_token}'},
                files=files,
                data=data
            )
            
            return response.json()

# Verificar estado de la subida
async def check_upload_status(access_token: str, upload_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'https://www.strava.com/api/v3/uploads/{upload_id}',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        return response.json()
```

## Límites de la API

- **Usuarios**: Hasta 1,000 atletas conectados por defecto
- **Rate limits**: 
  - 100 peticiones cada 15 minutos
  - 1,000 peticiones al día

## Recursos

- [Documentación oficial de Strava API](https://developers.strava.com/docs/getting-started/)
- [Referencia de OAuth](https://developers.strava.com/docs/authentication/)
- [Guía de subida de actividades](https://developers.strava.com/docs/uploads/)
- [Video tutorial (YouTube)](https://www.youtube.com/watch?v=w6KG1xyPOeM)

## Notas de seguridad

⚠️ **IMPORTANTE**:
- Nunca expongas el `STRAVA_CLIENT_SECRET` en el frontend
- Los tokens se almacenan en la base de datos; asegúrate de que esté protegida
- En producción, usa HTTPS para todas las comunicaciones
- Considera cifrar los tokens en la base de datos para mayor seguridad
