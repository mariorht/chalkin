# Chalkin Sense JS SDK — procedencia

Esta carpeta contiene una copia **vendorizada** del SDK JavaScript del protocolo BLE de
Chalkin Sense. No se edita aquí: se copia tal cual desde el repositorio de origen.

- Repositorio: https://github.com/mariorht/chalkin_sense
- Release/tag: `fw-v1.0.0` (commit `f81b8aea9a79e1b050f369be7ab0bcc66e634b90`)
- Ruta original: `sdk/js/`
- Versión de protocolo: `PROTOCOL_VERSION = "1.0.0"` (congelada)
- Licencia: **GPL-3.0** (compatible con la AGPL-3.0 de Chalkin)

Archivos copiados: `index.js`, `protocol.js`, `metrics.js`, `client.js`.
Los tests y scripts de Node del SDK original no se copian (no se sirven en estáticos).

## Actualizar el SDK

```bash
# Copiar los ficheros runtime desde el tag deseado
TAG=fw-v1.0.0
DST=src/app/static/sdk/js
for f in index.js protocol.js metrics.js client.js; do
  git -C ../chalkin_sense show "$TAG:sdk/js/$f" > "$DST/$f"
done
```

Comprueba que `PROTOCOL_VERSION` coincide con la versión que espera la app y actualiza
este documento (tag y commit).
