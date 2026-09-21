#!/bin/bash
# Definir rutas
BASE_DIR="/root/chalkin"
BACKUP_DIR="/root/daily_backups"
mkdir -p $BACKUP_DIR

# Nombre del archivo
FILENAME="chalkin_data_$(date +%Y%m%d_%H%M).tar.gz"

echo "Iniciando backup desde $BASE_DIR..."

# Ejecutar el backup
# Usamos el nombre del servicio 'api' definido en tu docker-compose.prod.yml
docker run --rm \
  --volumes-from $(docker compose -f $BASE_DIR/docker-compose.prod.yml ps -q api) \
  -v $BACKUP_DIR:/archive \
  alpine tar czf /archive/$FILENAME -C /app/data .

echo "Backup guardado en: $BACKUP_DIR/$FILENAME"

# Mantener solo los últimos 7 días de backups
find $BACKUP_DIR -type f -mtime +7 -name "*.tar.gz" -delete