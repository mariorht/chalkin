#!/bin/bash

# Nombre del entorno virtual
VENV_DIR="venv"

# Verificar que existe el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ El entorno virtual no existe. Ejecuta primero ./setup_venv.sh"
    exit 1
fi

# Activar el entorno virtual
echo "Activando entorno virtual..."
source $VENV_DIR/bin/activate

# Lanzar la aplicación
echo "🚀 Iniciando servidor en http://localhost:8001"
echo "   Docs: http://localhost:8001/docs"
echo "   ReDoc: http://localhost:8001/redoc"
echo ""
cd src
../venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
