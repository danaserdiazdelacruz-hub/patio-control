# 🚀 Guía de Despliegue - Railway (GRATIS)

## Opción 1: Railway (Recomendado - Más Fácil)

### Paso 1: Subir a GitHub

1. Ve a [github.com](https://github.com) y crea cuenta si no tienes
2. Click en **"New repository"** (botón verde)
3. Nombre: `patio-control`
4. Déjalo **Public** (o Private si tienes Pro)
5. Click **"Create repository"**

Luego sube los archivos:
- Opción A: Arrastra todos los archivos a la página del repo
- Opción B: Usa GitHub Desktop (más fácil si no conoces git)

### Paso 2: Crear cuenta en Railway

1. Ve a [railway.app](https://railway.app)
2. Click **"Login"** → **"Login with GitHub"**
3. Autoriza Railway

### Paso 3: Crear Base de Datos PostgreSQL

1. En Railway, click **"New Project"**
2. Click **"Provision PostgreSQL"**
3. ¡Listo! Railway crea la BD automáticamente

### Paso 4: Desplegar la App

1. En el mismo proyecto, click **"New"** → **"GitHub Repo"**
2. Selecciona tu repo `patio-control`
3. Railway detecta Python automáticamente y despliega

### Paso 5: Conectar BD con App

1. Click en el servicio de PostgreSQL
2. Ve a **"Variables"** → Copia `DATABASE_URL`
3. Click en tu servicio de la app
4. Ve a **"Variables"** → **"New Variable"**
5. Nombre: `DATABASE_URL`, Valor: (pega lo que copiaste)

### Paso 6: Generar Dominio

1. Click en tu servicio de la app
2. Ve a **"Settings"** → **"Networking"**
3. Click **"Generate Domain"**
4. ¡Tu app estará en algo como `patio-control-xxx.up.railway.app`!

### Paso 7: Crear Datos de Demo

Abre en el navegador:
```
https://TU-DOMINIO.up.railway.app/api/setup/datos-demo
```

Y haz un POST (puedes usar la documentación automática):
```
https://TU-DOMINIO.up.railway.app/docs
```

---

## Opción 2: Render (Alternativa Gratis)

### Paso 1: Subir a GitHub (igual que arriba)

### Paso 2: Crear cuenta en Render

1. Ve a [render.com](https://render.com)
2. Click **"Get Started"** → **"GitHub"**

### Paso 3: Crear PostgreSQL

1. Click **"New"** → **"PostgreSQL"**
2. Nombre: `patio-db`
3. Plan: **Free**
4. Click **"Create Database"**
5. Copia la **"External Database URL"**

### Paso 4: Crear Web Service

1. Click **"New"** → **"Web Service"**
2. Conecta tu repo de GitHub
3. Configuración:
   - Name: `patio-control`
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Click **"Advanced"** → **"Add Environment Variable"**
   - Key: `DATABASE_URL`
   - Value: (pega la URL del PostgreSQL)
5. Click **"Create Web Service"**

---

## 🔑 Variables de Entorno Necesarias

| Variable | Descripción |
|----------|-------------|
| DATABASE_URL | URL de conexión PostgreSQL (Railway/Render la provee) |

---

## 📱 Acceder desde el Celular

Una vez desplegado, accede desde cualquier dispositivo:

```
https://TU-DOMINIO.up.railway.app/          ← Login
https://TU-DOMINIO.up.railway.app/admin     ← Logística
https://TU-DOMINIO.up.railway.app/despacho  ← Despacho  
https://TU-DOMINIO.up.railway.app/chofer    ← Choferes (móvil)
```

---

## ⚠️ Límites del Plan Gratuito

### Railway Free Tier:
- $5 de crédito mensual (suficiente para desarrollo/pruebas)
- Se pausa si no hay uso por un tiempo
- Perfecto para MVP y demos

### Render Free Tier:
- 750 horas/mes
- Se "duerme" después de 15 min sin uso
- Tarda ~30 seg en "despertar"

---

## 🆘 Problemas Comunes

### "Application failed to respond"
- Verifica que `DATABASE_URL` esté configurada
- Revisa los logs en Railway/Render

### "No module named X"
- Verifica que `requirements.txt` esté en la raíz del repo

### WebSocket no conecta
- Railway soporta WebSockets automáticamente
- En Render, verifica que el dominio use `wss://` no `ws://`

---

## 📞 ¿Necesitas Ayuda?

Si te atoras en algún paso, mándame screenshot del error y te ayudo.
