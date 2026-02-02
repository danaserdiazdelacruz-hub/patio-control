"""
API Principal - Control de Patio y Asignación de Rampas
Centro de Distribución Supermercados Bravo
"""
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import json

from database import engine, get_db, Base
from models import (
    Usuario, Camion, Rampa, Movimiento, Notificacion, LogEvento,
    EstadoMovimiento, EstadoRampa, RolUsuario, TipoCamion, Prioridad
)
from schemas import (
    UsuarioCreate, UsuarioUpdate, UsuarioResponse, LoginRequest, LoginResponse,
    CamionCreate, CamionUpdate, CamionResponse, CamionConChofer,
    RampaCreate, RampaUpdate, RampaResponse,
    MovimientoCreate, MovimientoResponse, MovimientoCompleto,
    SolicitudDespacho, AsignacionRampa, ConfirmacionChofer, CambioEstado,
    NotificacionResponse, EstadisticasPatio, ResumenRampa, ColaCamiones,
    QRIngreso, QRSalida, MensajeResponse
)

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Control de Patio - Supermercados Bravo",
    description="Sistema de gestión de patio y asignación de rampas",
    version="1.0.0"
)

# CORS - permitir acceso desde cualquier origen (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos del frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# ========================================
# WEBSOCKET - Notificaciones en tiempo real
# ========================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}  # {user_id: [websockets]}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
    
    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast_to_role(self, role: str, message: dict, db: Session):
        usuarios = db.query(Usuario).filter(Usuario.rol == role).all()
        for usuario in usuarios:
            await self.send_to_user(usuario.id, message)
    
    async def broadcast_all(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Manejar mensajes entrantes si es necesario
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# ========================================
# PÁGINAS FRONTEND
# ========================================

@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")

@app.get("/admin")
async def admin_page():
    return FileResponse("../frontend/admin.html")

@app.get("/chofer")
async def chofer_page():
    return FileResponse("../frontend/chofer.html")

@app.get("/despacho")
async def despacho_page():
    return FileResponse("../frontend/despacho.html")

# ========================================
# AUTENTICACIÓN
# ========================================

@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.codigo == request.codigo,
        Usuario.pin == request.pin,
        Usuario.activo == True
    ).first()
    
    if not usuario:
        return LoginResponse(success=False, mensaje="Código o PIN incorrecto")
    
    return LoginResponse(
        success=True,
        mensaje="Login exitoso",
        usuario=UsuarioResponse.model_validate(usuario)
    )

# ========================================
# USUARIOS
# ========================================

@app.get("/api/usuarios", response_model=List[UsuarioResponse])
def listar_usuarios(
    rol: Optional[RolUsuario] = None,
    activo: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    query = db.query(Usuario)
    if rol:
        query = query.filter(Usuario.rol == rol)
    if activo is not None:
        query = query.filter(Usuario.activo == activo)
    return query.all()

@app.post("/api/usuarios", response_model=UsuarioResponse)
def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar código único
    existente = db.query(Usuario).filter(Usuario.codigo == usuario.codigo).first()
    if existente:
        raise HTTPException(status_code=400, detail="El código ya existe")
    
    db_usuario = Usuario(**usuario.model_dump())
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@app.put("/api/usuarios/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(usuario_id: int, usuario: UsuarioUpdate, db: Session = Depends(get_db)):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    for key, value in usuario.model_dump(exclude_unset=True).items():
        setattr(db_usuario, key, value)
    
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# ========================================
# CAMIONES
# ========================================

@app.get("/api/camiones", response_model=List[CamionConChofer])
def listar_camiones(
    tipo: Optional[TipoCamion] = None,
    activo: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    query = db.query(Camion).options(joinedload(Camion.chofer))
    if tipo:
        query = query.filter(Camion.tipo == tipo)
    if activo is not None:
        query = query.filter(Camion.activo == activo)
    return query.all()

@app.post("/api/camiones", response_model=CamionResponse)
def crear_camion(camion: CamionCreate, db: Session = Depends(get_db)):
    existente = db.query(Camion).filter(Camion.placa == camion.placa).first()
    if existente:
        raise HTTPException(status_code=400, detail="La placa ya existe")
    
    db_camion = Camion(**camion.model_dump())
    db.add(db_camion)
    db.commit()
    db.refresh(db_camion)
    return db_camion

@app.put("/api/camiones/{camion_id}", response_model=CamionResponse)
def actualizar_camion(camion_id: int, camion: CamionUpdate, db: Session = Depends(get_db)):
    db_camion = db.query(Camion).filter(Camion.id == camion_id).first()
    if not db_camion:
        raise HTTPException(status_code=404, detail="Camión no encontrado")
    
    for key, value in camion.model_dump(exclude_unset=True).items():
        setattr(db_camion, key, value)
    
    db.commit()
    db.refresh(db_camion)
    return db_camion

# ========================================
# RAMPAS
# ========================================

@app.get("/api/rampas", response_model=List[RampaResponse])
def listar_rampas(
    estado: Optional[EstadoRampa] = None,
    activo: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    query = db.query(Rampa)
    if estado:
        query = query.filter(Rampa.estado == estado)
    if activo is not None:
        query = query.filter(Rampa.activo == activo)
    return query.order_by(Rampa.numero).all()

@app.post("/api/rampas", response_model=RampaResponse)
def crear_rampa(rampa: RampaCreate, db: Session = Depends(get_db)):
    existente = db.query(Rampa).filter(Rampa.numero == rampa.numero).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de rampa ya existe")
    
    db_rampa = Rampa(**rampa.model_dump())
    db.add(db_rampa)
    db.commit()
    db.refresh(db_rampa)
    return db_rampa

@app.put("/api/rampas/{rampa_id}", response_model=RampaResponse)
def actualizar_rampa(rampa_id: int, rampa: RampaUpdate, db: Session = Depends(get_db)):
    db_rampa = db.query(Rampa).filter(Rampa.id == rampa_id).first()
    if not db_rampa:
        raise HTTPException(status_code=404, detail="Rampa no encontrada")
    
    for key, value in rampa.model_dump(exclude_unset=True).items():
        setattr(db_rampa, key, value)
    
    db.commit()
    db.refresh(db_rampa)
    return db_rampa

@app.get("/api/rampas/resumen", response_model=List[ResumenRampa])
def resumen_rampas(db: Session = Depends(get_db)):
    """Obtiene todas las rampas con su movimiento actual si está ocupada"""
    rampas = db.query(Rampa).filter(Rampa.activo == True).order_by(Rampa.numero).all()
    resultado = []
    
    for rampa in rampas:
        movimiento_actual = None
        tiempo_ocupada = None
        
        if rampa.estado == EstadoRampa.OCUPADA:
            movimiento = db.query(Movimiento).options(
                joinedload(Movimiento.camion).joinedload(Camion.chofer)
            ).filter(
                Movimiento.rampa_id == rampa.id,
                Movimiento.estado.in_([EstadoMovimiento.EN_RAMPA, EstadoMovimiento.CARGA_LISTA])
            ).first()
            
            if movimiento:
                movimiento_actual = MovimientoCompleto.model_validate(movimiento)
                if movimiento.hora_en_rampa:
                    tiempo_ocupada = (datetime.now() - movimiento.hora_en_rampa).total_seconds() / 60
        
        resultado.append(ResumenRampa(
            rampa=RampaResponse.model_validate(rampa),
            movimiento_actual=movimiento_actual,
            tiempo_ocupada=tiempo_ocupada
        ))
    
    return resultado

# ========================================
# MOVIMIENTOS - FLUJO PRINCIPAL
# ========================================

def obtener_movimiento_completo(db: Session, movimiento_id: int) -> Movimiento:
    return db.query(Movimiento).options(
        joinedload(Movimiento.camion).joinedload(Camion.chofer),
        joinedload(Movimiento.rampa),
        joinedload(Movimiento.asignado_por)
    ).filter(Movimiento.id == movimiento_id).first()

@app.get("/api/movimientos", response_model=List[MovimientoCompleto])
def listar_movimientos(
    estado: Optional[EstadoMovimiento] = None,
    fecha: Optional[str] = None,  # YYYY-MM-DD
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Movimiento).options(
        joinedload(Movimiento.camion).joinedload(Camion.chofer),
        joinedload(Movimiento.rampa),
        joinedload(Movimiento.asignado_por)
    )
    
    if estado:
        query = query.filter(Movimiento.estado == estado)
    
    if fecha:
        fecha_inicio = datetime.strptime(fecha, "%Y-%m-%d")
        fecha_fin = fecha_inicio + timedelta(days=1)
        query = query.filter(
            Movimiento.hora_ingreso_garita >= fecha_inicio,
            Movimiento.hora_ingreso_garita < fecha_fin
        )
    
    return query.order_by(Movimiento.hora_ingreso_garita.desc()).limit(limit).all()

@app.get("/api/movimientos/activos", response_model=ColaCamiones)
def movimientos_activos(db: Session = Depends(get_db)):
    """Obtiene los movimientos activos organizados por estado"""
    base_query = db.query(Movimiento).options(
        joinedload(Movimiento.camion).joinedload(Camion.chofer),
        joinedload(Movimiento.rampa)
    )
    
    disponibles = base_query.filter(
        Movimiento.estado == EstadoMovimiento.DISPONIBLE_PATIO
    ).order_by(Movimiento.hora_ingreso_garita).all()
    
    solicitados = base_query.filter(
        Movimiento.estado == EstadoMovimiento.SOLICITADO
    ).order_by(Movimiento.hora_solicitado).all()
    
    en_camino = base_query.filter(
        Movimiento.estado == EstadoMovimiento.ASIGNADO_EN_CAMINO
    ).order_by(Movimiento.hora_asignado).all()
    
    return ColaCamiones(
        disponibles=[MovimientoCompleto.model_validate(m) for m in disponibles],
        solicitados=[MovimientoCompleto.model_validate(m) for m in solicitados],
        en_camino=[MovimientoCompleto.model_validate(m) for m in en_camino]
    )

@app.get("/api/movimientos/{movimiento_id}", response_model=MovimientoCompleto)
def obtener_movimiento(movimiento_id: int, db: Session = Depends(get_db)):
    movimiento = obtener_movimiento_completo(db, movimiento_id)
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return movimiento

# ========================================
# 1️⃣ INGRESO GARITA - Escaneo QR
# ========================================

@app.post("/api/movimientos/ingreso", response_model=MovimientoResponse)
async def registrar_ingreso(datos: QRIngreso, db: Session = Depends(get_db)):
    """Chofer escanea QR en garita - registra ingreso"""
    # Buscar camión
    camion = db.query(Camion).filter(Camion.placa == datos.placa.upper()).first()
    if not camion:
        raise HTTPException(status_code=404, detail="Camión no registrado")
    
    # Verificar chofer
    chofer = db.query(Usuario).filter(
        Usuario.codigo == datos.chofer_codigo,
        Usuario.rol == RolUsuario.CHOFER
    ).first()
    if not chofer:
        raise HTTPException(status_code=404, detail="Chofer no registrado")
    
    # Verificar que no tenga un movimiento activo
    movimiento_activo = db.query(Movimiento).filter(
        Movimiento.camion_id == camion.id,
        Movimiento.estado.notin_([EstadoMovimiento.SALIDA_CD, EstadoMovimiento.SALIDA_RAMPA])
    ).first()
    if movimiento_activo:
        raise HTTPException(status_code=400, detail="Este camión ya tiene un movimiento activo")
    
    # Crear movimiento
    movimiento = Movimiento(
        camion_id=camion.id,
        estado=EstadoMovimiento.INGRESADO_GARITA,
        hora_ingreso_garita=datetime.now()
    )
    db.add(movimiento)
    
    # Log
    log = LogEvento(
        movimiento_id=movimiento.id,
        usuario_id=chofer.id,
        accion="INGRESO_GARITA",
        descripcion=f"Camión {camion.placa} ingresó a garita"
    )
    db.add(log)
    
    db.commit()
    db.refresh(movimiento)
    
    # Notificar a logística
    await manager.broadcast_to_role("logistica", {
        "tipo": "nuevo_ingreso",
        "mensaje": f"Camión {camion.placa} ingresó a garita",
        "movimiento_id": movimiento.id
    }, db)
    
    return movimiento

# ========================================
# 2️⃣ DISPONIBLE EN PATIO
# ========================================

@app.post("/api/movimientos/{movimiento_id}/disponible", response_model=MovimientoResponse)
async def marcar_disponible(movimiento_id: int, db: Session = Depends(get_db)):
    """Marcar camión como disponible en patio (después de ingreso)"""
    movimiento = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado != EstadoMovimiento.INGRESADO_GARITA:
        raise HTTPException(status_code=400, detail="Estado inválido para esta acción")
    
    movimiento.estado = EstadoMovimiento.DISPONIBLE_PATIO
    movimiento.hora_disponible_patio = datetime.now()
    
    db.commit()
    db.refresh(movimiento)
    
    # Notificar
    await manager.broadcast_all({
        "tipo": "camion_disponible",
        "mensaje": "Nuevo camión disponible en patio",
        "movimiento_id": movimiento.id
    })
    
    return movimiento

# ========================================
# 3️⃣ SOLICITUD DESPACHO
# ========================================

@app.post("/api/movimientos/solicitar", response_model=MovimientoResponse)
async def solicitar_camion(solicitud: SolicitudDespacho, db: Session = Depends(get_db)):
    """Despacho solicita un camión específico"""
    movimiento = db.query(Movimiento).filter(Movimiento.id == solicitud.movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado != EstadoMovimiento.DISPONIBLE_PATIO:
        raise HTTPException(status_code=400, detail="El camión no está disponible")
    
    movimiento.estado = EstadoMovimiento.SOLICITADO
    movimiento.hora_solicitado = datetime.now()
    movimiento.solicitado_por_despacho = solicitud.solicitado_por
    
    if solicitud.rampa_id:
        movimiento.rampa_id = solicitud.rampa_id
    if solicitud.prioridad:
        movimiento.prioridad = solicitud.prioridad
    if solicitud.notas:
        movimiento.notas = solicitud.notas
    
    db.commit()
    db.refresh(movimiento)
    
    # Notificar a logística
    await manager.broadcast_to_role("logistica", {
        "tipo": "solicitud_camion",
        "mensaje": f"Despacho solicita camión - Prioridad: {movimiento.prioridad.value}",
        "movimiento_id": movimiento.id
    }, db)
    
    return movimiento

# ========================================
# 4️⃣ ASIGNACIÓN DE RAMPA (Logística)
# ========================================

@app.post("/api/movimientos/asignar", response_model=MovimientoResponse)
async def asignar_rampa(asignacion: AsignacionRampa, db: Session = Depends(get_db)):
    """Logística asigna rampa a un camión"""
    movimiento = db.query(Movimiento).options(
        joinedload(Movimiento.camion).joinedload(Camion.chofer)
    ).filter(Movimiento.id == asignacion.movimiento_id).first()
    
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado not in [EstadoMovimiento.DISPONIBLE_PATIO, EstadoMovimiento.SOLICITADO]:
        raise HTTPException(status_code=400, detail="Estado inválido para asignar rampa")
    
    # Verificar rampa
    rampa = db.query(Rampa).filter(Rampa.id == asignacion.rampa_id).first()
    if not rampa:
        raise HTTPException(status_code=404, detail="Rampa no encontrada")
    
    if rampa.estado != EstadoRampa.LIBRE:
        raise HTTPException(status_code=400, detail="La rampa no está disponible")
    
    # Actualizar movimiento
    movimiento.estado = EstadoMovimiento.ASIGNADO_EN_CAMINO
    movimiento.rampa_id = rampa.id
    movimiento.hora_asignado = datetime.now()
    movimiento.asignado_por_id = asignacion.asignado_por_id
    
    if asignacion.notas:
        movimiento.notas = (movimiento.notas or "") + f"\n{asignacion.notas}"
    
    # Reservar rampa (aún no ocupada)
    # rampa.estado = EstadoRampa.OCUPADA  # Se marca ocupada cuando confirma llegada
    
    # Crear notificación para el chofer
    chofer_id = movimiento.camion.chofer_id if movimiento.camion else None
    if chofer_id:
        notificacion = Notificacion(
            usuario_id=chofer_id,
            movimiento_id=movimiento.id,
            tipo="asignacion_rampa",
            mensaje=f"Diríjase a la Rampa {rampa.numero}"
        )
        db.add(notificacion)
        
        # Notificar por WebSocket
        await manager.send_to_user(chofer_id, {
            "tipo": "asignacion_rampa",
            "mensaje": f"¡ATENCIÓN! Diríjase a la Rampa {rampa.numero}",
            "movimiento_id": movimiento.id,
            "rampa": rampa.numero,
            "requiere_confirmacion": True
        })
    
    db.commit()
    db.refresh(movimiento)
    
    return movimiento

# ========================================
# 5️⃣ CONFIRMACIÓN CHOFER
# ========================================

@app.post("/api/movimientos/{movimiento_id}/confirmar-chofer", response_model=MovimientoResponse)
async def confirmar_asignacion_chofer(movimiento_id: int, db: Session = Depends(get_db)):
    """Chofer confirma que recibió la asignación"""
    movimiento = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado != EstadoMovimiento.ASIGNADO_EN_CAMINO:
        raise HTTPException(status_code=400, detail="Estado inválido para confirmar")
    
    movimiento.hora_confirmado_chofer = datetime.now()
    
    # Marcar notificación como confirmada
    notificacion = db.query(Notificacion).filter(
        Notificacion.movimiento_id == movimiento_id,
        Notificacion.tipo == "asignacion_rampa"
    ).first()
    if notificacion:
        notificacion.confirmada = True
        notificacion.confirmada_at = datetime.now()
    
    db.commit()
    db.refresh(movimiento)
    
    # Notificar a logística y despacho
    await manager.broadcast_to_role("logistica", {
        "tipo": "chofer_confirmo",
        "mensaje": f"Chofer confirmó asignación - En camino a rampa",
        "movimiento_id": movimiento.id
    }, db)
    
    return movimiento

# ========================================
# 6️⃣ LLEGADA A RAMPA (Despacho confirma)
# ========================================

@app.post("/api/movimientos/{movimiento_id}/en-rampa", response_model=MovimientoResponse)
async def confirmar_en_rampa(movimiento_id: int, db: Session = Depends(get_db)):
    """Despacho confirma que el camión llegó a la rampa"""
    movimiento = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado != EstadoMovimiento.ASIGNADO_EN_CAMINO:
        raise HTTPException(status_code=400, detail="Estado inválido para esta acción")
    
    movimiento.estado = EstadoMovimiento.EN_RAMPA
    movimiento.hora_en_rampa = datetime.now()
    
    # Marcar rampa como ocupada
    if movimiento.rampa_id:
        rampa = db.query(Rampa).filter(Rampa.id == movimiento.rampa_id).first()
        if rampa:
            rampa.estado = EstadoRampa.OCUPADA
    
    db.commit()
    db.refresh(movimiento)
    
    await manager.broadcast_all({
        "tipo": "camion_en_rampa",
        "mensaje": f"Camión en rampa - Iniciando carga",
        "movimiento_id": movimiento.id
    })
    
    return movimiento

# ========================================
# 7️⃣ CARGA LISTA
# ========================================

@app.post("/api/movimientos/{movimiento_id}/carga-lista", response_model=MovimientoResponse)
async def marcar_carga_lista(movimiento_id: int, db: Session = Depends(get_db)):
    """Despacho marca que la carga está lista"""
    movimiento = db.query(Movimiento).options(
        joinedload(Movimiento.camion).joinedload(Camion.chofer),
        joinedload(Movimiento.rampa)
    ).filter(Movimiento.id == movimiento_id).first()
    
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado != EstadoMovimiento.EN_RAMPA:
        raise HTTPException(status_code=400, detail="Estado inválido para esta acción")
    
    movimiento.estado = EstadoMovimiento.CARGA_LISTA
    movimiento.hora_carga_lista = datetime.now()
    
    # Notificar al chofer
    chofer_id = movimiento.camion.chofer_id if movimiento.camion else None
    if chofer_id:
        notificacion = Notificacion(
            usuario_id=chofer_id,
            movimiento_id=movimiento.id,
            tipo="carga_lista",
            mensaje=f"¡Carga lista! Puede retirarse de Rampa {movimiento.rampa.numero if movimiento.rampa else ''}"
        )
        db.add(notificacion)
        
        await manager.send_to_user(chofer_id, {
            "tipo": "carga_lista",
            "mensaje": f"¡CARGA LISTA! Puede retirarse de la rampa",
            "movimiento_id": movimiento.id
        })
    
    db.commit()
    db.refresh(movimiento)
    
    return movimiento

# ========================================
# 8️⃣ SALIDA DE RAMPA
# ========================================

@app.post("/api/movimientos/{movimiento_id}/salida-rampa", response_model=MovimientoResponse)
async def registrar_salida_rampa(movimiento_id: int, db: Session = Depends(get_db)):
    """Registrar salida del camión de la rampa"""
    movimiento = db.query(Movimiento).filter(Movimiento.id == movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if movimiento.estado != EstadoMovimiento.CARGA_LISTA:
        raise HTTPException(status_code=400, detail="Estado inválido para esta acción")
    
    movimiento.estado = EstadoMovimiento.SALIDA_RAMPA
    movimiento.hora_salida_rampa = datetime.now()
    
    # Liberar rampa
    if movimiento.rampa_id:
        rampa = db.query(Rampa).filter(Rampa.id == movimiento.rampa_id).first()
        if rampa:
            rampa.estado = EstadoRampa.LIBRE
    
    db.commit()
    db.refresh(movimiento)
    
    await manager.broadcast_all({
        "tipo": "rampa_liberada",
        "mensaje": f"Rampa liberada",
        "movimiento_id": movimiento.id,
        "rampa_id": movimiento.rampa_id
    })
    
    return movimiento

# ========================================
# 9️⃣ SALIDA DEL CD
# ========================================

@app.post("/api/movimientos/salida-cd", response_model=MovimientoResponse)
async def registrar_salida_cd(datos: QRSalida, db: Session = Depends(get_db)):
    """Chofer escanea QR al salir del CD"""
    movimiento = db.query(Movimiento).filter(Movimiento.id == datos.movimiento_id).first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    movimiento.estado = EstadoMovimiento.SALIDA_CD
    movimiento.hora_salida_cd = datetime.now()
    
    db.commit()
    db.refresh(movimiento)
    
    return movimiento

# ========================================
# ESTADÍSTICAS Y DASHBOARD
# ========================================

@app.get("/api/estadisticas", response_model=EstadisticasPatio)
def obtener_estadisticas(db: Session = Depends(get_db)):
    """Estadísticas generales del patio"""
    hoy = datetime.now().date()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    
    # Contar por estados
    estados_activos = [
        EstadoMovimiento.INGRESADO_GARITA,
        EstadoMovimiento.DISPONIBLE_PATIO,
        EstadoMovimiento.SOLICITADO,
        EstadoMovimiento.ASIGNADO_EN_CAMINO,
        EstadoMovimiento.EN_RAMPA,
        EstadoMovimiento.CARGA_LISTA
    ]
    
    camiones_en_patio = db.query(Movimiento).filter(
        Movimiento.estado.in_(estados_activos)
    ).count()
    
    camiones_disponibles = db.query(Movimiento).filter(
        Movimiento.estado == EstadoMovimiento.DISPONIBLE_PATIO
    ).count()
    
    camiones_en_rampa = db.query(Movimiento).filter(
        Movimiento.estado.in_([EstadoMovimiento.EN_RAMPA, EstadoMovimiento.CARGA_LISTA])
    ).count()
    
    rampas_libres = db.query(Rampa).filter(
        Rampa.estado == EstadoRampa.LIBRE,
        Rampa.activo == True
    ).count()
    
    rampas_ocupadas = db.query(Rampa).filter(
        Rampa.estado == EstadoRampa.OCUPADA,
        Rampa.activo == True
    ).count()
    
    # Tiempos promedio (movimientos completados hoy)
    movimientos_completados = db.query(Movimiento).filter(
        Movimiento.hora_ingreso_garita >= inicio_hoy,
        Movimiento.hora_salida_rampa.isnot(None),
        Movimiento.hora_en_rampa.isnot(None)
    ).all()
    
    tiempo_promedio_espera = None
    tiempo_promedio_rampa = None
    
    if movimientos_completados:
        tiempos_espera = []
        tiempos_rampa = []
        
        for m in movimientos_completados:
            if m.hora_disponible_patio and m.hora_en_rampa:
                espera = (m.hora_en_rampa - m.hora_disponible_patio).total_seconds() / 60
                tiempos_espera.append(espera)
            
            if m.hora_en_rampa and m.hora_salida_rampa:
                rampa = (m.hora_salida_rampa - m.hora_en_rampa).total_seconds() / 60
                tiempos_rampa.append(rampa)
        
        if tiempos_espera:
            tiempo_promedio_espera = sum(tiempos_espera) / len(tiempos_espera)
        if tiempos_rampa:
            tiempo_promedio_rampa = sum(tiempos_rampa) / len(tiempos_rampa)
    
    return EstadisticasPatio(
        camiones_en_patio=camiones_en_patio,
        camiones_disponibles=camiones_disponibles,
        camiones_en_rampa=camiones_en_rampa,
        rampas_libres=rampas_libres,
        rampas_ocupadas=rampas_ocupadas,
        tiempo_promedio_espera=tiempo_promedio_espera,
        tiempo_promedio_rampa=tiempo_promedio_rampa
    )

# ========================================
# NOTIFICACIONES
# ========================================

@app.get("/api/notificaciones/{usuario_id}", response_model=List[NotificacionResponse])
def obtener_notificaciones(
    usuario_id: int,
    solo_no_leidas: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Notificacion).filter(Notificacion.usuario_id == usuario_id)
    if solo_no_leidas:
        query = query.filter(Notificacion.leida == False)
    return query.order_by(Notificacion.created_at.desc()).limit(50).all()

@app.post("/api/notificaciones/{notificacion_id}/leer", response_model=NotificacionResponse)
def marcar_leida(notificacion_id: int, db: Session = Depends(get_db)):
    notificacion = db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    notificacion.leida = True
    notificacion.leida_at = datetime.now()
    db.commit()
    db.refresh(notificacion)
    return notificacion

# ========================================
# DATOS INICIALES (para desarrollo/demo)
# ========================================

@app.post("/api/setup/datos-demo", response_model=MensajeResponse)
def crear_datos_demo(db: Session = Depends(get_db)):
    """Crea datos iniciales para demo/pruebas"""
    
    # Verificar si ya hay datos
    if db.query(Usuario).first():
        return MensajeResponse(success=False, mensaje="Ya existen datos en la base de datos")
    
    # Crear usuarios
    usuarios = [
        Usuario(codigo="ADMIN01", nombre="Administrador", pin="1234", rol=RolUsuario.ADMIN),
        Usuario(codigo="LOG001", nombre="Rafico - Logística", pin="1234", rol=RolUsuario.LOGISTICA),
        Usuario(codigo="DES001", nombre="Juan Despacho", pin="1234", rol=RolUsuario.DESPACHO),
        Usuario(codigo="DES002", nombre="María Despacho", pin="1234", rol=RolUsuario.DESPACHO),
        Usuario(codigo="CHO001", nombre="Pedro Chofer", pin="1234", rol=RolUsuario.CHOFER, telefono="809-555-0001"),
        Usuario(codigo="CHO002", nombre="Carlos Chofer", pin="1234", rol=RolUsuario.CHOFER, telefono="809-555-0002"),
        Usuario(codigo="CHO003", nombre="Miguel Chofer", pin="1234", rol=RolUsuario.CHOFER, telefono="809-555-0003"),
    ]
    db.add_all(usuarios)
    db.flush()
    
    # Crear rampas
    rampas = [
        Rampa(numero=1, nombre="Rampa 1 - Secos", tipo_permitido=TipoCamion.SECO),
        Rampa(numero=2, nombre="Rampa 2 - Secos", tipo_permitido=TipoCamion.SECO),
        Rampa(numero=3, nombre="Rampa 3 - Refrigerados", tipo_permitido=TipoCamion.REFRIGERADO),
        Rampa(numero=4, nombre="Rampa 4 - Refrigerados", tipo_permitido=TipoCamion.REFRIGERADO),
        Rampa(numero=5, nombre="Rampa 5 - Mixta"),
        Rampa(numero=6, nombre="Rampa 6 - Mixta"),
    ]
    db.add_all(rampas)
    
    # Crear camiones
    choferes = {u.codigo: u for u in usuarios if u.rol == RolUsuario.CHOFER}
    camiones = [
        Camion(placa="A123456", tipo=TipoCamion.SECO, chofer_id=choferes["CHO001"].id, capacidad="10 ton"),
        Camion(placa="B789012", tipo=TipoCamion.REFRIGERADO, chofer_id=choferes["CHO002"].id, capacidad="8 ton"),
        Camion(placa="C345678", tipo=TipoCamion.MIXTO, chofer_id=choferes["CHO003"].id, capacidad="12 ton"),
        Camion(placa="D901234", tipo=TipoCamion.SECO, capacidad="10 ton"),
        Camion(placa="E567890", tipo=TipoCamion.REFRIGERADO, capacidad="8 ton"),
    ]
    db.add_all(camiones)
    
    db.commit()
    
    return MensajeResponse(
        success=True,
        mensaje="Datos de demo creados exitosamente",
        data={
            "usuarios": len(usuarios),
            "rampas": len(rampas),
            "camiones": len(camiones)
        }
    )

# ========================================
# CHOFER - Endpoints específicos
# ========================================

@app.get("/api/chofer/{chofer_id}/movimiento-activo", response_model=Optional[MovimientoCompleto])
def obtener_movimiento_activo_chofer(chofer_id: int, db: Session = Depends(get_db)):
    """Obtiene el movimiento activo del chofer"""
    # Buscar camión del chofer
    camion = db.query(Camion).filter(Camion.chofer_id == chofer_id).first()
    if not camion:
        return None
    
    movimiento = db.query(Movimiento).options(
        joinedload(Movimiento.camion),
        joinedload(Movimiento.rampa)
    ).filter(
        Movimiento.camion_id == camion.id,
        Movimiento.estado.notin_([EstadoMovimiento.SALIDA_CD])
    ).order_by(Movimiento.created_at.desc()).first()
    
    return movimiento

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
