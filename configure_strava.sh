#!/bin/bash

# Script para configurar las credenciales de Strava en el archivo .env
# Uso: ./configure_strava.sh

echo "=========================================="
echo "Configuración de Strava para Chalkin"
echo "=========================================="
echo ""

# Verificar que existe el archivo .env
if [ ! -f "src/.env" ]; then
    echo "⚠️  Archivo .env no encontrado. Creando desde .env.example..."
    cp src/.env.example src/.env
    echo "✓ Archivo .env creado"
fi

echo "Por favor, ingresa tus credenciales de Strava:"
echo "(Puedes obtenerlas en: https://www.strava.com/settings/api)"
echo ""

read -p "Client ID: " client_id
read -p "Client Secret: " client_secret
read -p "Redirect URI [http://localhost:8000/api/strava/callback]: " redirect_uri

# Si no se proporciona redirect_uri, usar el default
if [ -z "$redirect_uri" ]; then
    redirect_uri="http://localhost:8000/api/strava/callback"
fi

# Actualizar o añadir las variables en .env
env_file="src/.env"

# Función para actualizar o añadir variable
update_env_var() {
    local key=$1
    local value=$2
    local file=$3
    
    if grep -q "^${key}=" "$file"; then
        # Variable existe, actualizar
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        # Variable no existe, añadir
        echo "${key}=${value}" >> "$file"
    fi
}

update_env_var "STRAVA_CLIENT_ID" "$client_id" "$env_file"
update_env_var "STRAVA_CLIENT_SECRET" "$client_secret" "$env_file"
update_env_var "STRAVA_REDIRECT_URI" "$redirect_uri" "$env_file"

echo ""
echo "✓ Credenciales de Strava configuradas correctamente"
echo ""
echo "Siguiente paso: Ejecutar la migración de base de datos"
echo "  cd src"
echo "  alembic upgrade head"
echo ""
echo "=========================================="
