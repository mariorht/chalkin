# Chalkin - Boulder Climbing Tracker 🧗

[![Run Tests](https://github.com/mariorht/chalkin/actions/workflows/run-tests.yml/badge.svg)](https://github.com/mariorht/chalkin/actions/workflows/run-tests.yml)
[![Deploy](https://github.com/mariorht/chalkin/actions/workflows/deploy.yml/badge.svg)](https://github.com/mariorht/chalkin/actions/workflows/deploy.yml)

Track your climbing sessions, log boulder ascents, and monitor your progress. Like Strava, but for climbers.

## Features

- 🏠 **Multi-gym support** - Track across different climbing gyms with maps
- 🎨 **Flexible grading** - Colors, V-scale, Font scale, or custom
- 📊 **Progress tracking** - Weekly stats, grade distribution, PRs
- 👥 **Social features** - Follow friends, activity feed, friend requests
- 🗺️ **Map integration** - Locate gyms with OpenStreetMap
- 📱 **Web interface** - Full frontend included (no React needed!)

---

## Project Structure

```plaintext
.
├── README.md                # Project documentation
├── docker-compose.yml       # Docker Compose configuration
├── src/
│   ├── Dockerfile           # Docker configuration for the backend
│   ├── alembic/             # Database migrations
│   │   ├── versions/        # Migration files
│   │   │   ├── 001_initial.py
│   │   │   └── 002_add_friendships.py
│   │   └── env.py           # Alembic config
│   ├── app/
│   │   ├── main.py          # FastAPI server entry point
│   │   ├── database.py      # Database connection
│   │   ├── core/            # Config, security, dependencies
│   │   ├── db/              # Database setup
│   │   ├── models/          # SQLAlchemy models
│   │   │   ├── user.py      # User model
│   │   │   ├── gym.py       # Gym model
│   │   │   ├── grade.py     # Grade model
│   │   │   ├── session.py   # Session model
│   │   │   ├── ascent.py    # Ascent model
│   │   │   └── friendship.py # Friendship model
│   │   ├── routers/         # API endpoints
│   │   │   ├── auth.py      # Authentication
│   │   │   ├── gyms.py      # Gym CRUD
│   │   │   ├── grades.py    # Grade management
│   │   │   ├── sessions.py  # Session management
│   │   │   ├── ascents.py   # Ascent logging
│   │   │   ├── stats.py     # Statistics
│   │   │   └── social.py    # Friends & activity feed
│   │   ├── schemas/         # Pydantic schemas
│   │   └── static/          # Static files and HTML templates
│   │       └── templates/   # Frontend pages
│   │           ├── index.html
│   │           ├── login.html
│   │           ├── register.html
│   │           ├── dashboard.html
│   │           ├── gym-new.html
│   │           ├── gym-edit.html
│   │           ├── gyms.html
│   │           ├── session-new.html
│   │           ├── session-detail.html
│   │           ├── sessions.html
│   │           ├── friends.html
│   │           └── feed.html
│   └── requirements.txt     # Python dependencies
├── tests/                   # Test suite (69 tests)
├── run_tests.sh             # Script to run tests
├── setup_venv.sh            # Script to setup virtual environment
└── start_venv.sh            # Script to run with venv
```

---

## Quick Start

### 1. Setup Environment

```bash
cd src

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Unix/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (especially SECRET_KEY for production!)
```

### 3. Database Migration

```bash
# Run migrations to create database
alembic upgrade head
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload
```

Visit:
- **API Docs**: http://localhost:8000/docs
- **Web App**: http://localhost:8000

---

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Get profile

### Gyms
- `GET /api/gyms` - List gyms
- `POST /api/gyms` - Create gym
- `GET /api/gyms/{id}` - Get gym with grades
- `GET /api/gyms/{id}/grades` - Get gym's grade scale

### Sessions (Check-in)
- `GET /api/sessions` - List my sessions
- `POST /api/sessions` - Start session (check-in)
- `GET /api/sessions/{id}` - Get session with ascents
- `POST /api/sessions/{id}/end` - End session

### Ascents (The core action!)
- `POST /api/sessions/{id}/ascents` - Log a boulder
- `PATCH /api/ascents/{id}` - Update ascent
- `DELETE /api/ascents/{id}` - Remove ascent

### Stats (The Strava magic 🪄)
- `GET /api/stats/me` - Full statistics
- `GET /api/stats/summary` - Quick dashboard summary

### Social 👥
- `GET /api/social/users/search` - Search users
- `POST /api/social/friends/request/{user_id}` - Send friend request
- `GET /api/social/friends/requests` - Get pending requests
- `POST /api/social/friends/requests/{id}/accept` - Accept request
- `POST /api/social/friends/requests/{id}/reject` - Reject request
- `GET /api/social/friends` - List friends
- `GET /api/social/feed` - Activity feed

---

## Database Migrations

Using Alembic for version control:

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# See current version
alembic current

# See history
alembic history
```

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_sessions.py -v
```

Or use the provided script:

```bash
./run_tests.sh
```

---

## Grading System

The `relative_difficulty` field (0-15) allows comparing grades across gyms:

| relative_difficulty | V-Scale | Font | Colors (typical) |
|---------------------|---------|------|------------------|
| 1-2                 | V0-V1   | 4-5  | Green/Yellow     |
| 3-4                 | V2-V3   | 5+-6A| Blue             |
| 5-6                 | V4-V5   | 6B-6C| Red              |
| 7-8                 | V6-V7   | 7A   | Black            |
| 9-10                | V8-V9   | 7B-7C| White/Pink       |
| 11+                 | V10+    | 8A+  | Pro circuit      |

---

## Running with Docker

1. **Prerequisites:**
   - Ensure **Docker** and **Docker Compose** are installed.

2. **Use the `start_docker.sh` Script:**

   ```bash
   ./start_docker.sh
   ```

3. **Access the Application:**

   Open your browser at `http://localhost:8001`.

4. **Stop the Project:**

   ```bash
   docker-compose down
   ```

---

## Technologies Used

- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Database:** SQLite (swappable to PostgreSQL)
- **Auth:** JWT with passlib/bcrypt
- **Containerization:** Docker and Docker Compose
- **Tests:** pytest

---

## 🚀 Deployment Guide

### Archivos de configuración

| Archivo | Propósito | ¿En Git? |
|---------|-----------|----------|
| `docker-compose.yml` | Desarrollo local con Docker | ✅ Sí |
| `docker-compose.prod.yml` | Producción con Nginx | ✅ Sí |
| `nginx/nginx.conf` | Configuración reverse proxy | ✅ Sí |
| `.env.example` | Plantilla de variables | ✅ Sí |
| `.env` | Variables reales (secretos) | ❌ No |
| `nginx/ssl/` | Certificados SSL | ❌ No |

### Variables de entorno

| Variable | Descripción | Default | ¿Obligatoria en prod? |
|----------|-------------|---------|----------------------|
| `SECRET_KEY` | Clave para firmar JWT | - | ⚠️ **SÍ** |
| `DEBUG` | Modo debug | `true` | No (usar `false`) |
| `DATABASE_URL` | URL de la BD | `sqlite:///./chalkin.db` | No |
| `ALGORITHM` | Algoritmo JWT | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración token | `10080` (1 semana) | No |
| `APP_NAME` | Nombre app | `Chalkin` | No |
| `APP_VERSION` | Versión | `0.1.0` | No |

---

## 🖥️ Desarrollo Local (Docker)

Para desarrollo rápido con hot-reload:

```bash
# 1. Clonar y entrar
git clone https://github.com/tu-usuario/chalkin.git
cd chalkin

# 2. (Opcional) Crear .env o usar defaults
cp .env.example .env

# 3. Arrancar
docker-compose up -d --build

# 4. Crear tablas
docker-compose exec api alembic upgrade head

# 5. Ver logs
docker-compose logs -f
```

**Acceso:** http://localhost:8001

---

## 🌐 Producción (VPS/Cloud)

### Flujo de trabajo completo

```
┌─────────────────────────────────────────────────────────────┐
│  TU MÁQUINA LOCAL                                           │
│  ─────────────────                                          │
│  1. Desarrollas código                                      │
│  2. git commit && git push                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SERVIDOR DE PRODUCCIÓN (VPS, EC2, DigitalOcean...)        │
│  ───────────────────────────────────────────────────────    │
│  1. git pull                                                │
│  2. docker-compose -f docker-compose.prod.yml up -d --build│
│  3. docker-compose exec api alembic upgrade head           │
└─────────────────────────────────────────────────────────────┘
```

### Paso 1: Preparar el servidor

```bash
# Conectar al servidor
ssh usuario@tu-servidor.com


### Paso 2: Clonar el proyecto

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/chalkin.git
cd chalkin
```

### Paso 3: Configurar variables de entorno

```bash
# Generar SECRET_KEY segura
SECRET_KEY=$(openssl rand -hex 32)

# Crear archivo .env
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
DEBUG=false
DATABASE_URL=sqlite:///./chalkin.db
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
EOF

# Verificar
cat .env
```

### Paso 4: Desplegar

```bash
# Construir y arrancar (primera vez)
docker-compose -f docker-compose.prod.yml up -d --build

# Ejecutar migraciones
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verificar que todo funciona
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

**Acceso:** http://tu-servidor.com (puerto 80)

---

## 🔄 Actualizar en Producción

Cuando hagas cambios en el código:

```bash
# En tu máquina local
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main

# En el servidor
ssh usuario@tu-servidor.com
cd chalkin
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 🛡️ Comandos de Mantenimiento

```bash
# Ver estado
docker-compose -f docker-compose.prod.yml ps

# Ver logs en tiempo real
docker-compose -f docker-compose.prod.yml logs -f

# Ver logs solo de la API
docker-compose -f docker-compose.prod.yml logs -f api

# Reiniciar todo
docker-compose -f docker-compose.prod.yml restart

# Reiniciar solo nginx (después de cambiar config)
docker-compose -f docker-compose.prod.yml restart nginx

# Parar todo
docker-compose -f docker-compose.prod.yml down

# Parar y eliminar volúmenes (¡BORRA LA BD!)
docker-compose -f docker-compose.prod.yml down -v
```

---

## 💾 Backups

La base de datos SQLite se almacena en un volumen Docker persistente en `/app/data/chalkin.db`.

```bash
# Backup de la base de datos
docker cp chalkin_api:/app/data/chalkin.db ./backup-$(date +%Y%m%d).db

# Restaurar backup
docker cp ./backup-20231223.db chalkin_api:/app/data/chalkin.db
docker-compose -f docker-compose.prod.yml restart api

# Verificar que existe la BD
docker-compose -f docker-compose.prod.yml exec api ls -la /app/data/

# Backup automático diario (añadir a crontab)
# crontab -e
# 0 3 * * * docker cp chalkin_api:/app/data/chalkin.db /home/usuario/backups/chalkin-$(date +\%Y\%m\%d).db
```

⚠️ **Importante**: No uses `docker-compose down -v` ya que esto elimina los volúmenes y la base de datos.

---

## 🛠️ Development (sin Docker)

Para debug local usando virtual environment:

### 1. Setup inicial

```bash
# Crear venv e instalar dependencias
./setup_venv.sh

# O manualmente:
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r src/requirements.txt
```

### 2. Configurar y crear BD

```bash
cp src/.env.example src/.env

cd src
source ../venv/bin/activate
alembic upgrade head
```

### 3. Iniciar servidor

```bash
./start_venv.sh

# O manualmente:
cd src
source ../venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 4. Ejecutar tests

```bash
./run_tests.sh
```

---

## Database Migrations (Alembic)

```bash
cd src

# Crear nueva migración (después de modificar models/)
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Rollback
alembic downgrade -1

# Ver versión actual
alembic current
```

---

## Next Steps

- [ ] Photo upload to S3/local storage
- [ ] Push notifications
- [ ] Gym admin panel
- [ ] Mobile app (React Native)
- [ ] Achievements/badges system

---

## Web Pages

| Page | URL | Description |
|------|-----|-------------|
| Landing | `/` | Welcome page |
| Login | `/login` | User authentication |
| Register | `/register` | Create account |
| Dashboard | `/dashboard` | Main hub with stats |
| New Gym | `/gyms/new` | Create gym with map |
| Edit Gym | `/gyms/edit?id={id}` | Edit gym details |
| Gyms List | `/gyms` | Browse all gyms |
| New Session | `/sessions/new` | Start climbing session |
| Session Detail | `/sessions/{id}` | Log ascents |
| Sessions List | `/sessions` | Session history |
| Friends | `/friends` | Manage friendships |
| Feed | `/feed` | Social activity feed |

---
¡A escalar! 🧗‍♂️

