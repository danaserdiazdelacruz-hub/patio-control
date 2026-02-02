# 🚛 Control de Patio - MVP
## Sistema de Gestión de Patio y Asignación de Rampas
### Centro de Distribución - Supermercados Bravo

---

## 📋 Descripción

Sistema digital para gestionar el flujo de camiones en el Centro de Distribución mediante:
- **App móvil para choferes**: Recibe notificaciones de asignación de rampa
- **Panel de Despacho**: Solicita camiones y confirma cargas
- **Panel de Logística/Admin**: Visualiza patio completo y asigna rampas

---

## 🚀 Instalación Rápida

### 1. Requisitos Previos
- Python 3.9+
- PostgreSQL 12+

### 2. Crear Base de Datos

```sql
-- Conectarse a PostgreSQL y ejecutar:
CREATE DATABASE patio_control;
```

### 3. Configurar Conexión

Edita el archivo `backend/database.py` y cambia la línea:

```python
DATABASE_URL = "postgresql://usuario:password@localhost:5432/patio_control"
```

Por tus credenciales reales:
```python
DATABASE_URL = "postgresql://TU_USUARIO:TU_PASSWORD@localhost:5432/patio_control"
```

### 4. Instalar Dependencias

```bash
cd patio-control
pip install -r requirements.txt
```

### 5. Iniciar el Servidor

```bash
cd backend
python main.py
```

O con uvicorn directamente:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Crear Datos de Demo

Abre en el navegador:
```
http://localhost:8000
```

Luego ejecuta este endpoint para crear datos de prueba:
```
POST http://localhost:8000/api/setup/datos-demo
```

O usa curl:
```bash
curl -X POST http://localhost:8000/api/setup/datos-demo
```

---

## 👥 Usuarios de Demo

| Código | PIN | Rol | Acceso |
|--------|-----|-----|--------|
| LOG001 | 1234 | Logística | Panel Admin |
| DES001 | 1234 | Despacho | Panel Despacho |
| CHO001 | 1234 | Chofer | App Chofer |
| CHO002 | 1234 | Chofer | App Chofer |
| CHO003 | 1234 | Chofer | App Chofer |

---

## 🔗 URLs del Sistema

| Pantalla | URL |
|----------|-----|
| Login | http://localhost:8000/ |
| Admin/Logística | http://localhost:8000/admin |
| Despacho | http://localhost:8000/despacho |
| Chofer | http://localhost:8000/chofer |
| API Docs | http://localhost:8000/docs |

---

## 📱 Flujo de Operación

```
1️⃣ INGRESO GARITA
   └─> Chofer escanea QR (o Admin registra manualmente)
   
2️⃣ DISPONIBLE EN PATIO
   └─> Camión visible en cola
   
3️⃣ SOLICITUD (Opcional)
   └─> Despacho solicita camión específico
   
4️⃣ ASIGNACIÓN DE RAMPA
   └─> Logística asigna rampa
   └─> Chofer recibe notificación con sonido
   
5️⃣ CONFIRMACIÓN CHOFER
   └─> Chofer confirma que va en camino
   
6️⃣ EN RAMPA
   └─> Despacho confirma llegada del camión
   
7️⃣ CARGA LISTA
   └─> Despacho marca carga completada
   └─> Chofer recibe notificación
   
8️⃣ SALIDA DE RAMPA
   └─> Se libera la rampa
   
9️⃣ SALIDA DEL CD
   └─> Registro completo del ciclo
```

---

## 📊 Métricas que Mide

- **Tiempo de espera en patio**: Desde disponible hasta asignación
- **Tiempo en rampa**: Desde llegada hasta salida
- **Tiempo total del ciclo**: Ingreso a salida
- **Uso de rampas**: Ocupación en tiempo real
- **Historial exportable**: Por día, camión, chofer

---

## 🔧 Estructura del Proyecto

```
patio-control/
├── backend/
│   ├── database.py     # 🔧 CONFIGURAR AQUÍ LA BASE DE DATOS
│   ├── models.py       # Modelos SQLAlchemy
│   ├── schemas.py      # Validación Pydantic
│   └── main.py         # API FastAPI
├── frontend/
│   ├── styles.css      # Estilos compartidos
│   ├── index.html      # Login
│   ├── admin.html      # Panel Logística
│   ├── despacho.html   # Panel Despacho
│   └── chofer.html     # App Chofer
├── requirements.txt
└── README.md
```

---

## 🗃️ Modelo de Datos

### Tablas Principales

- **usuarios**: Choferes, despachadores, logística, admin
- **camiones**: Flota con placa, tipo, chofer asignado
- **rampas**: Rampas del CD con estado
- **movimientos**: Registro de cada ciclo de camión
- **notificaciones**: Alertas enviadas
- **log_eventos**: Auditoría

### Estados del Movimiento

```python
INGRESADO_GARITA    # Acaba de entrar
DISPONIBLE_PATIO    # Listo para asignar
SOLICITADO          # Despacho lo pidió
ASIGNADO_EN_CAMINO  # Tiene rampa, va en camino
EN_RAMPA            # Llegó, cargando
CARGA_LISTA         # Listo para salir
SALIDA_RAMPA        # Dejó la rampa
SALIDA_CD           # Salió del centro
```

---

## 🔌 API Endpoints Principales

### Autenticación
- `POST /api/auth/login` - Login con código y PIN

### Movimientos (Flujo principal)
- `POST /api/movimientos/ingreso` - Registrar entrada
- `POST /api/movimientos/{id}/disponible` - Marcar disponible
- `POST /api/movimientos/solicitar` - Despacho solicita
- `POST /api/movimientos/asignar` - Logística asigna rampa
- `POST /api/movimientos/{id}/confirmar-chofer` - Chofer confirma
- `POST /api/movimientos/{id}/en-rampa` - Confirmar llegada
- `POST /api/movimientos/{id}/carga-lista` - Marcar carga lista
- `POST /api/movimientos/{id}/salida-rampa` - Salida de rampa

### Consultas
- `GET /api/movimientos/activos` - Cola actual
- `GET /api/rampas/resumen` - Estado de rampas
- `GET /api/estadisticas` - Dashboard stats
- `GET /api/chofer/{id}/movimiento-activo` - Estado del chofer

### WebSocket
- `WS /ws/{user_id}` - Notificaciones en tiempo real

---

## 🔒 Seguridad (Para Producción)

Antes de ir a producción, implementar:

1. **Hashing de PIN**: Usar bcrypt en vez de texto plano
2. **JWT Tokens**: Para autenticación de API
3. **HTTPS**: Certificado SSL
4. **CORS**: Restringir orígenes permitidos
5. **Rate Limiting**: Limitar requests por IP

---

## 📱 Acceso Móvil

La interfaz del chofer está optimizada para móvil. Para acceder desde el celular:

1. Conecta el celular a la misma red que el servidor
2. Usa la IP del servidor: `http://192.168.X.X:8000/chofer`
3. Añadir a pantalla de inicio para experiencia de app

---

## 🛠️ Troubleshooting

### Error de conexión a BD
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solución**: Verificar que PostgreSQL esté corriendo y las credenciales sean correctas.

### WebSocket no conecta
**Solución**: Verificar que no haya firewall bloqueando el puerto 8000.

### Notificaciones no llegan al chofer
**Solución**: 
1. Verificar que el chofer tenga un camión asignado en la BD
2. Revisar la consola del navegador por errores de WebSocket

---

## 📞 Soporte

Desarrollado por **Astria Lab**
Contacto: [Tu información de contacto]

---

## 📄 Licencia

Proyecto privado - Supermercados Bravo © 2025
