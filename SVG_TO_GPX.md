# SVG to GPX Converter para Strava

Esta funcionalidad convierte el logo de Chalkin (o cualquier forma SVG) en un archivo GPX que se puede subir a Strava. Esto permite que las actividades de escalada en boulder muestren el logo en el mapa de Strava en lugar de un solo punto que se ve mal con mucho zoom.

## Arquitectura

### Archivos principales:

1. **`app/utils/svg_parser.py`**: Utilidades para parsear SVG paths y convertirlos a puntos GPS
2. **`app/routers/strava.py`**: Endpoint `/api/strava/svg-to-gpx` para probar la conversión
3. **`test_svg_to_gpx.py`**: Script de prueba para generar archivos GPX localmente

## Cómo funciona

1. **Parseo del SVG**: Lee los comandos del path SVG (M, L, C, Q, Z, etc.)
2. **Conversión a puntos**: Convierte el path en una lista de coordenadas (x, y)
3. **Normalización**: Escala y centra los puntos
4. **Conversión GPS**: Transforma las coordenadas SVG a latitud/longitud
5. **Generación GPX**: Crea un archivo GPX válido con los puntos distribuidos en el tiempo

## Uso

### Endpoint de prueba

El endpoint `/api/strava/svg-to-gpx` permite probar la conversión:

```bash
# Descargar GPX con configuración por defecto (Madrid)
curl http://localhost:8000/api/strava/svg-to-gpx -o test.gpx

# Con parámetros personalizados
curl "http://localhost:8000/api/strava/svg-to-gpx?center_lat=40.416775&center_lon=-3.703790&scale_meters=150&num_points=300" -o test.gpx

# Usar forma de prueba simple
curl "http://localhost:8000/api/strava/svg-to-gpx?use_logo=false" -o test.gpx
```

### Parámetros del endpoint:

- `center_lat` (float): Latitud del centro (default: 40.416775 - Madrid)
- `center_lon` (float): Longitud del centro (default: -3.703790 - Madrid)
- `scale_meters` (float): Tamaño de la forma en metros (default: 100)
- `num_points` (int): Número de puntos GPS a generar (default: 200)
- `use_logo` (bool): Usar logo de Chalkin o forma simple de prueba (default: true)

### Script de prueba local

```bash
cd src
python test_svg_to_gpx.py
```

Esto generará dos archivos:
- `test_triangle.gpx`: Forma triangular simple
- `test_logo.gpx`: Logo de Chalkin simplificado

### Visualizar los GPX

Puedes subir los archivos GPX generados a:
- https://www.gpsvisualizer.com/map_input
- https://www.gpxsee.org/
- Google Earth
- Cualquier aplicación de mapas que soporte GPX

## Personalización del logo

El logo simplificado está definido en `app/utils/svg_parser.py` como `CHALKIN_LOGO_SIMPLIFIED`.

Para usar el logo real completo del archivo `static/icons/logoChalkin.svg`, necesitarás:

1. Extraer los paths principales del SVG
2. Simplificar la forma si es necesario (los SVG complejos pueden tener miles de puntos)
3. Actualizar la constante `CHALKIN_LOGO_SIMPLIFIED` con el path extraído

### Extraer paths del SVG completo:

```python
from app.utils.svg_parser import extract_svg_paths

paths = extract_svg_paths('src/app/static/icons/logoChalkin.svg')
for i, path in enumerate(paths):
    print(f"Path {i}: {path[:100]}...")  # Mostrar primeros 100 chars
```

## Integración con subida a Strava

Una vez que estés satisfecho con cómo se ve el logo en el mapa, puedes integrar esta funcionalidad en el endpoint de subida a Strava:

1. Modificar `upload_session_to_strava()` en `strava.py`
2. En lugar de generar un GPX de 2 puntos, usar las funciones del logo:

```python
from app.utils.svg_parser import svg_to_points, scale_and_center_points, CHALKIN_LOGO_SIMPLIFIED

# En lugar de generate_gpx_file()...
points = svg_to_points(CHALKIN_LOGO_SIMPLIFIED, num_points=200)
gps_points = scale_and_center_points(
    points, 
    session.gym.latitude, 
    session.gym.longitude, 
    scale_meters=100
)
gpx_content = generate_gpx_from_points(
    gps_points,
    start_datetime,
    duration,
    activity_name,
    activity_description
)
```

## Consejos

- **Tamaño del logo**: Usa `scale_meters` entre 50-200m para que sea visible pero no demasiado grande
- **Número de puntos**: 150-300 puntos suele ser suficiente. Más puntos = más detalle pero archivo más grande
- **Prueba primero**: Usa el endpoint de prueba y visualiza el GPX antes de integrarlo con Strava
- **Coordenadas**: Asegúrate de que el gimnasio tenga latitud/longitud configuradas correctamente

## Limitaciones

- El parser SVG es simplificado y puede no manejar todos los comandos SVG complejos
- Los paths con muchas curvas bezier se simplifican
- El logo debe ser relativamente simple (< 1000 puntos idealmente)

## TODO

- [ ] Extraer y simplificar el logo real de logoChalkin.svg
- [ ] Integrar con el endpoint de subida a Strava
- [ ] Agregar opción en el frontend para elegir entre "punto simple" o "logo"
- [ ] Permitir al usuario ajustar el tamaño del logo
- [ ] Cachear los puntos del logo para no recalcular cada vez
