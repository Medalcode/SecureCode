# SECURECODE — Deployment Gratuito: Supabase + Cloud Run

**Documento:** Guía de deployment a costo CERO  
**Audiencia:** Jonatthan + Jose (equipo de desarrollo)  
**Costo Estimado:** $0 (planes gratuitos de ambas plataformas)  
**Tiempo Total:** 30 minutos  
**Ventaja:** No pagar $15-30/mes por proyecto temporal

---

## 🎯 **Por Qué Esta Opción**

| Aspecto | Railway | Supabase + Cloud Run |
|---------|---------|-------------------|
| **Costo mensual** | $5-10 | $0 |
| **Para 3 meses demostración** | $15-30 | $0 |
| **Plan gratuito** | Limitado | Generoso (hobby) |
| **PostgreSQL incluida** | Sí ($5-10) | Sí (GRATIS) |
| **Compute** | Incluido | Cloud Run GRATIS |
| **Realtime features** | No | Sí (Supabase) |

**Para proyecto académico que vive 2-3 meses: Supabase + Cloud Run es GRATIS.**

---

## 📋 **Parte 1: Setup Supabase (5 minutos)**

### Paso 1: Crear Cuenta Supabase

```bash
# Ir a: https://app.supabase.com/
# Clic en: "Sign Up"
# Opciones:
#   - GitHub (recomendado: 1 click)
#   - Google
#   - Email

# Resultado: Estás logged in
```

### Paso 2: Crear Proyecto

```bash
# Clic: "New Project"
# Form:
#   Name: securecode-mvp
#   Database Password: (Supabase genera, copy para después)
#   Region: us-east-1 (más barato)
#   Plan: Free (IMPORTANTE: seleccionar free)

# Esperar 30 segundos
# Status debe decir: "Initialized"
```

### Paso 3: Obtener Connection String

```bash
# Ir a: Settings → Database (sidebar izquierdo)
# Desplazar hasta: "Connection String"
# Seleccionar: "URI" (no "Session pooler")
# Copy el string completo

# Formato:
# postgresql://postgres:PASSWORD@db.REGION.supabase.co:5432/postgres
```

### Paso 4: Guardar en .env

```bash
# En tu proyecto local:
cat > .env << 'ENVFILE'
# Supabase Database
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.us-east-1.supabase.co:5432/postgres

# GitHub (como antes)
GITHUB_API_TOKEN=ghp_xxxxxxxxxxxx

# JWT (como antes)
JWT_SECRET_KEY=your-secret-key-32-chars-minimum
JWT_ALGORITHM=HS256

# App config (como antes)
APP_ENV=production
LOG_LEVEL=INFO
ENVFILE
```

### Paso 5: Ejecutar Migraciones

```bash
# Localemente primero (verificar sintaxis)
alembic upgrade head

# Supabase UI
# Settings → SQL Editor
# Copiar-pegar el contenido de db/alembic/versions/001_init.sql
# Ejecutar
```

✅ **Supabase setup completo**

---

## 📦 **Parte 2: Setup Cloud Run (10 minutos)**

### Paso 1: Crear Proyecto GCP

```bash
# Opción A: Desde gcloud CLI
gcloud projects create securecode-mvp --set-as-default

# Opción B: Desde console.cloud.google.com
# "Select a project" → "New Project" → securecode-mvp
```

### Paso 2: Habilitar APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

# Esperar 30s
```

### Paso 3: Crear Artifact Registry (repositorio de imágenes)

```bash
gcloud artifacts repositories create securecode \
  --repository-format=docker \
  --location=us-central1 \
  --description="SECURECODE Docker images"
```

### Paso 4: Build y Push de Imagen Docker

```bash
# Configurar Docker CLI
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build
docker build -t us-central1-docker.pkg.dev/securecode-mvp/securecode/app:latest .

# Push a Artifact Registry
docker push us-central1-docker.pkg.dev/securecode-mvp/securecode/app:latest

# Verificar
gcloud artifacts docker images list us-central1-docker.pkg.dev/securecode-mvp/securecode
```

### Paso 5: Deploy a Cloud Run

```bash
gcloud run deploy securecode \
  --image us-central1-docker.pkg.dev/securecode-mvp/securecode/app:latest \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL="postgresql://postgres:PASSWORD@db.us-east-1.supabase.co:5432/postgres" \
  --set-env-vars GITHUB_API_TOKEN="ghp_xxxx" \
  --set-env-vars JWT_SECRET_KEY="your-key" \
  --set-env-vars APP_ENV="production" \
  --quiet

# Esperar 2-3 minutos
# Resultado: URL de tu app
# https://securecode-XXXXX.run.app
```

### Paso 6: Verificar Deployment

```bash
# Health check
curl https://securecode-XXXXX.run.app/healthcheck

# Debe retornar:
# {"status": "healthy", "timestamp": "..."}

# Swagger UI
# Abrir en navegador: https://securecode-XXXXX.run.app/docs
```

✅ **Cloud Run deployment completo**

---

## 🔄 **Parte 3: CI/CD Automático (Opcional, 5 min)**

```yaml
# .github/workflows/deploy.yml

name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  REGION: us-central1
  PROJECT_ID: securecode-mvp
  GAR_LOCATION: us-central1
  REPOSITORY: securecode
  IMAGE: app

jobs:
  deploy:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Build and push Docker image
        run: |
          gcloud builds submit \
            --tag "${{ env.GAR_LOCATION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.IMAGE }}:${{ github.sha }}"

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.IMAGE }} \
            --image "${{ env.GAR_LOCATION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.IMAGE }}:${{ github.sha }}" \
            --region ${{ env.REGION }} \
            --platform managed \
            --set-env-vars DATABASE_URL="${{ secrets.DATABASE_URL }}" \
            --allow-unauthenticated
```

---

## 💰 **Verificar Costos**

### Supabase Free Plan Límites

```
PostgreSQL:
├─ Storage: 1 GB
├─ Connections: 2 simultáneas (OK para MVP)
├─ Realtime: 2 MB/sec (excelente)
└─ Auth: Unlimited users

Costo: $0
Suficiente para: Demostración + evaluación
```

### Cloud Run Free Tier

```
Compute:
├─ 2M request/mes (GRATIS)
├─ 360,000 GB-seconds/mes (GRATIS)
├─ CPU time: 180,000 vCPU-seconds/mes (GRATIS)
└─ Networking: 1 GB/mes outbound (GRATIS)

Costo: $0 (en MVP)
Suficiente para: 100+ evaluaciones/día
```

### Total Monthly Cost

```
Dashboard: https://console.cloud.google.com/billing

Expected (Supabase + Cloud Run):
├─ Compute: $0 (free tier)
├─ Database: $0 (Supabase free)
└─ TOTAL: $0
```

---

## 🔧 **Cambios de Código Necesarios**

### Cambio 1: Connection String Format

```python
# Antes (Railway):
DATABASE_URL=postgresql://user:pass@railway.app:5432/db

# Ahora (Supabase):
DATABASE_URL=postgresql://postgres:SUPABASE_PASSWORD@db.REGION.supabase.co:5432/postgres

# SQLAlchemy automaticamente detecta el formato, no requiere cambios
```

### Cambio 2: Timezone Handling

```python
# Supabase usa UTC siempre, verificar en código:

from datetime import datetime, timezone

# ✓ BIEN
now = datetime.now(timezone.utc)

# ❌ MALO (datetime.now() es local time)
now = datetime.now()
```

### Cambio 3: Connection Pooling

```python
# Si usas supabase-py SDK (opcional):
# pip install supabase

from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# PERO: En SECURECODE, seguir usando SQLAlchemy
# No cambios si ya usas psycopg2 + SQLAlchemy
```

---

## 📊 **Comparativa 3 Meses Demo**

```
SCENARIO: Demostración de proyecto académico (Sep - Dic 2026)

Railway:
├─ Mes 1 (Setup): $5
├─ Mes 2 (Demo): $5
├─ Mes 3 (Defensa): $5
├─ TOTAL: $15
└─ Después: Olvidado (dinero gastado)

Supabase + Cloud Run:
├─ Mes 1 (Setup): $0
├─ Mes 2 (Demo): $0
├─ Mes 3 (Defensa): $0
├─ TOTAL: $0
└─ Después: Datos quedan en Supabase (puedes recuperar)

AHORRO: $15 (pequeño, pero principio de la cosa)
```

---

## 🛠️ **Troubleshooting**

### Problema: "FATAL: remaining connection slots reserved"

**Síntoma:**
```
psycopg2.OperationalError: FATAL: remaining connection slots reserved
```

**Causa:** Supabase free plan = 2 conexiones simultáneas

**Solución:**
```python
# Reducir pool size en requirements (SQLAlchemy)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=1,  # Reducir a 1
    max_overflow=1,  # Y max 1 overflow
)
```

---

### Problema: "Password authentication failed"

**Síntoma:**
```
FATAL: password authentication failed
```

**Causa:** Connection string password incorrecto

**Solución:**
```bash
# Verificar en Supabase console:
# Settings → Database → Show Password
# Copiar exactamente (incluyendo caracteres especiales)
```

---

### Problema: "Cloud Run deployment timeout"

**Síntoma:**
```
Deployment failed: request deadline exceeded
```

**Causa:** Alembic migration tarda >10 min

**Solución:**
```bash
# Pre-ejecutar migraciones ANTES de deploy
# En Supabase SQL editor (antes de cloud run):
# 1. Paste todas las migraciones
# 2. Ejecutar
# 3. Luego deploy Cloud Run (sin migraciones)
```

---

## ✅ **Checklist Deployment**

**Pre-Deploy:**
- [ ] Supabase proyecto creado
- [ ] Connection string en .env
- [ ] Migraciones ejecutadas (Supabase SQL Editor)
- [ ] Test local contra Supabase (make test)
- [ ] GCP proyecto creado
- [ ] Cloud Run API habilitada
- [ ] Docker build local funciona

**Deploy:**
- [ ] Artifact Registry creado
- [ ] Docker push successful
- [ ] Cloud Run deployment successful
- [ ] Healthcheck responde 200
- [ ] Swagger UI accesible
- [ ] Login funciona

**Post-Deploy:**
- [ ] Curl API endpoints (sin auth para healthcheck)
- [ ] Test evaluación en producción
- [ ] Ver logs: `gcloud run logs read securecode`

---

## 📅 **Ejemplo Timeline Real**

```
AHORA (31-Ago):
├─ Leer este documento: 10 min
├─ Setup Supabase: 5 min
└─ Setup Cloud Run: 10 min

SEMANA 1 (01-Sep):
├─ Tests locales contra Supabase
└─ Primer deploy a Cloud Run

SEMANA 2-4 (02-Sep → 25-Sep):
├─ Desarrollo normal
├─ Deploy automático en cada push (CI/CD)
└─ URL estable para testing

SEMANA 5 (28-Sep):
├─ URL final lista para AAI
├─ Presentación en producción (Cloud Run)
└─ Defensa en producción (Cloud Run)

POST-DEFENSA (10-Dic):
├─ Proyecto congelado
├─ Datos quedan en Supabase (2 años free hobby)
└─ Costo total: $0
```

---

## 🎯 **Resumen: Por Qué Es la Mejor Opción**

✅ **Costo:** $0 vs Railway $15-30  
✅ **Escalabilidad:** Cloud Run escala automáticamente  
✅ **Data persistence:** Supabase guarda datos indefinidamente  
✅ **Profesional:** Evaluadores ven Google Cloud (enterprise)  
✅ **Sin vendor lock:** PostgreSQL estándar, fácil migrar después  
✅ **Simplicidad:** 30 minutos setup, listo  

---

## 📝 **Próximos Pasos**

1. Crear cuenta Supabase (5 min)
2. Crear proyecto GCP (3 min)  
3. Ejecutar este documento paso a paso (20 min)
4. Verificar con: `curl https://securecode-xxx.run.app/healthcheck`
5. ¡Listo! Ya estás en producción gratis

---

**Estado: RECOMENDADO PARA SECURECODE MVP**

Versión: 1.0  
Fecha: 31 de agosto de 2026

