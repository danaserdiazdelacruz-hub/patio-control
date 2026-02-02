"""
Schemas Pydantic - Control de Patio
Para validación y serialización de datos
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ========================================
# ENUMS (duplicados para Pydantic)
# ========================================

class EstadoMovimiento(str, Enum):
    INGRESADO_GARITA = "ingresado_garita"
    DISPONIBLE_PATIO = "disponible_patio"
    SOLICITADO = "solicitado"
    ASIGNADO_EN_CAMINO = "asignado_en_camino"
    EN_RAMPA = "en_rampa"
    CARGA_LISTA = "carga_lista"
    SALIDA_RAMPA = "salida_rampa"
    SALIDA_CD = "salida_cd"

class EstadoRampa(str, Enum):
    LIBRE = "libre"
    OCUPADA = "ocupada"
    MANTENIMIENTO = "mantenimiento"

class RolUsuario(str, Enum):
    ADMIN = "admin"
    CHOFER = "chofer"
    DESPACHO = "despacho"
    LOGISTICA = "logistica"

class TipoCamion(str, Enum):
    SECO = "seco"
    REFRIGERADO = "refrigerado"
    MIXTO = "mixto"

class Prioridad(str, Enum):
    NORMAL = "normal"
    URGENTE = "urgente"
    CRITICO = "critico"

# ========================================
# SCHEMAS DE USUARIO
# ========================================

class UsuarioBase(BaseModel):
    codigo: str
    nombre: str
    rol: RolUsuario
    telefono: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    pin: str

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    pin: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None

class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    codigo: str
    pin: str

class LoginResponse(BaseModel):
    success: bool
    mensaje: str
    usuario: Optional[UsuarioResponse] = None

# ========================================
# SCHEMAS DE CAMIÓN
# ========================================

class CamionBase(BaseModel):
    placa: str
    tipo: TipoCamion
    capacidad: Optional[str] = None

class CamionCreate(CamionBase):
    chofer_id: Optional[int] = None

class CamionUpdate(BaseModel):
    placa: Optional[str] = None
    tipo: Optional[TipoCamion] = None
    chofer_id: Optional[int] = None
    capacidad: Optional[str] = None
    activo: Optional[bool] = None

class CamionResponse(CamionBase):
    id: int
    chofer_id: Optional[int]
    activo: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class CamionConChofer(CamionResponse):
    chofer: Optional[UsuarioResponse] = None

# ========================================
# SCHEMAS DE RAMPA
# ========================================

class RampaBase(BaseModel):
    numero: int
    nombre: Optional[str] = None
    tipo_permitido: Optional[TipoCamion] = None

class RampaCreate(RampaBase):
    pass

class RampaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_permitido: Optional[TipoCamion] = None
    estado: Optional[EstadoRampa] = None
    activo: Optional[bool] = None

class RampaResponse(RampaBase):
    id: int
    estado: EstadoRampa
    activo: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========================================
# SCHEMAS DE MOVIMIENTO
# ========================================

class MovimientoBase(BaseModel):
    camion_id: int
    prioridad: Optional[Prioridad] = Prioridad.NORMAL
    notas: Optional[str] = None

class MovimientoCreate(MovimientoBase):
    pass

class SolicitudDespacho(BaseModel):
    movimiento_id: int
    rampa_id: Optional[int] = None
    prioridad: Optional[Prioridad] = None
    solicitado_por: str
    notas: Optional[str] = None

class AsignacionRampa(BaseModel):
    movimiento_id: int
    rampa_id: int
    asignado_por_id: int
    notas: Optional[str] = None

class ConfirmacionChofer(BaseModel):
    movimiento_id: int

class CambioEstado(BaseModel):
    movimiento_id: int
    nuevo_estado: EstadoMovimiento
    notas: Optional[str] = None

class MovimientoResponse(BaseModel):
    id: int
    camion_id: int
    rampa_id: Optional[int]
    asignado_por_id: Optional[int]
    estado: EstadoMovimiento
    prioridad: Prioridad
    
    hora_ingreso_garita: Optional[datetime]
    hora_disponible_patio: Optional[datetime]
    hora_solicitado: Optional[datetime]
    hora_asignado: Optional[datetime]
    hora_confirmado_chofer: Optional[datetime]
    hora_en_rampa: Optional[datetime]
    hora_carga_lista: Optional[datetime]
    hora_salida_rampa: Optional[datetime]
    hora_salida_cd: Optional[datetime]
    
    notas: Optional[str]
    solicitado_por_despacho: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class MovimientoCompleto(MovimientoResponse):
    """Movimiento con datos relacionados"""
    camion: Optional[CamionConChofer] = None
    rampa: Optional[RampaResponse] = None
    asignado_por: Optional[UsuarioResponse] = None

# ========================================
# SCHEMAS DE NOTIFICACIÓN
# ========================================

class NotificacionResponse(BaseModel):
    id: int
    usuario_id: int
    movimiento_id: Optional[int]
    tipo: str
    mensaje: str
    leida: bool
    confirmada: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========================================
# SCHEMAS DE DASHBOARD/REPORTES
# ========================================

class EstadisticasPatio(BaseModel):
    camiones_en_patio: int
    camiones_disponibles: int
    camiones_en_rampa: int
    rampas_libres: int
    rampas_ocupadas: int
    tiempo_promedio_espera: Optional[float]  # minutos
    tiempo_promedio_rampa: Optional[float]   # minutos

class ResumenRampa(BaseModel):
    rampa: RampaResponse
    movimiento_actual: Optional[MovimientoCompleto] = None
    tiempo_ocupada: Optional[float] = None  # minutos

class ColaCamiones(BaseModel):
    disponibles: List[MovimientoCompleto]
    solicitados: List[MovimientoCompleto]
    en_camino: List[MovimientoCompleto]

# ========================================
# SCHEMAS DE QR
# ========================================

class QRIngreso(BaseModel):
    placa: str
    chofer_codigo: str

class QRSalida(BaseModel):
    movimiento_id: int
    chofer_codigo: str

# ========================================
# RESPUESTAS GENÉRICAS
# ========================================

class MensajeResponse(BaseModel):
    success: bool
    mensaje: str
    data: Optional[dict] = None
