# Chalkin - Boulder Climbing Tracker 🧗

Track your climbing sessions, log boulder ascents, and monitor your progress. Like Strava, but for climbers.

## Features

- 🏠 **Multi-gym support** - Track across different climbing gyms
- 🎨 **Flexible grading** - Colors, V-scale, Font scale, or custom
- 📊 **Progress tracking** - Weekly stats, grade distribution, PRs
- 📸 **Photo logging** - Optional photos for your sends
- 🔄 **Grade comparison** - Compare difficulty across gyms

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
│   │   └── env.py           # Alembic config
│   ├── app/
│   │   ├── main.py          # FastAPI server entry point
│   │   ├── core/            # Config, security, dependencies
│   │   ├── db/              # Database setup
│   │   ├── models/          # SQLAlchemy models
│   │   ├── routers/         # API endpoints
│   │   ├── schemas/         # Pydantic schemas
│   │   └── static/          # Static files and HTML templates
│   └── requirements.txt     # Python dependencies
├── tests/                   # Test suite
└── start_venv.sh            # Script to run the virtual environment
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

## 🚀 Production Deployment (Docker)

### 1. Configure Environment

```bash
cp src/.env.example src/.env
nano src/.env
```

**Cambios importantes para producción:**

```dotenv
# OBLIGATORIO: genera con 'openssl rand -hex 32'
SECRET_KEY=tu-clave-secreta-segura-de-64-caracteres

DEBUG=false
```

### 2. Build y Run

```bash
# Construir y arrancar
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Ejecutar migraciones (crear tablas)
docker-compose exec api alembic upgrade head
```

### 3. Acceso

- **API Docs**: http://localhost:8001/docs
- **Web App**: http://localhost:8001

### 4. Mantenimiento

```bash
# Parar
docker-compose down

# Backup de la base de datos
docker cp chalkin_api:/app/chalkin.db ./backup.db

# Actualizar después de cambios
docker-compose up -d --build
docker-compose exec api alembic upgrade head
```

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

- [ ] Frontend web app (React/Vue)
- [ ] Photo upload to S3/local storage
- [ ] Social features (follow climbers, feed)
- [ ] Gym admin panel
- [ ] Mobile app (React Native)

---
¡A escalar! 🧗‍♂️

