# SVG to GPX Converter para Strava

Esta funcionalidad convierte el logo de Chalkin (o cualquier forma SVG) en un
archivo GPX que se puede subir a Strava. Esto permite que las actividades de
escalada en boulder muestren el logo en el mapa de Strava en lugar de un solo
punto que se ve mal con mucho zoom.

## Arquitectura

### Archivos principales:

1. **`app/utils/svg_parser.py`**: Utilidades para parsear SVG paths y convertirlos a puntos GPS.
2. **`app/routers/strava.py`**: Al subir una sesión, genera el GPX con forma de logo
   (`upload_session_to_strava`). El SVG usado es
   `app/static/icons/logoChalkin_invertido_simple.svg`; si falla, se usa un punto simple.

## Cómo funciona

1. **Parseo del SVG**: Lee los comandos del path SVG (M, L, C, Q, Z, etc.)
2. **Conversión a puntos**: Convierte el path en una lista de coordenadas (x, y)
3. **Normalización**: Escala y centra los puntos
4. **Conversión GPS**: Transforma las coordenadas SVG a latitud/longitud
5. **Generación GPX**: Crea un archivo GPX válido con los puntos distribuidos en el tiempo

## Personalización del logo

El logo usado está en `app/static/icons/logoChalkin_invertido_simple.svg`.
Para ajustarlo o simplificarlo:

1. Extraer los paths principales del SVG (los SVG complejos pueden tener miles de puntos).
2. Simplificar la forma si es necesario.
3. Reemplazar el contenido del SVG simplificado.

### Extraer paths de un SVG:

```python
from app.utils.svg_parser import extract_svg_paths

paths = extract_svg_paths('src/app/static/icons/logoChalkin.svg')
for i, path in enumerate(paths):
    print(f"Path {i}: {path[:100]}...")  # Mostrar primeros 100 chars
```

## Consejos

- **Tamaño del logo**: Usa `scale_meters` entre 50-200m para que sea visible pero no demasiado grande.
- **Número de puntos**: 150-300 puntos suele ser suficiente.
- **Coordenadas**: el gimnasio debe tener latitud/longitud configuradas para generar el GPX.

## Limitaciones

- El parser SVG es simplificado y puede no manejar todos los comandos SVG complejos.
- Los paths con muchas curvas bezier se simplifican.
- El logo debe ser relativamente simple (< 1000 puntos idealmente).
