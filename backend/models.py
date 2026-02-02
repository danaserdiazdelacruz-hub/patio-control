"""
Modelos de Base de Datos - Control de Patio
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

# ========================================
# ENUMS - Estados del Sistema
# ========================================

class EstadoMovimiento(str, enum.Enum):
    INGRESADO_GARITA = "ingresado_garita"
    DISPONIBLE_PATIO = "disponible_patio"
    SOLICITADO = "solicitado"
    ASIGNADO_EN_CAMINO = "asignado_en_camino"
    EN_RAMPA = "en_rampa"
    CARGA_LISTA = "carga_lista"
    SALIDA_RAMPA = "salida_rampa"
    SALIDA_CD = "salida_cd"

class EstadoRampa(str, enum.Enum):
    LIBRE = "libre"
    OCUPADA = "ocupada"
    MANTENIMIENTO = "mantenimiento"

class RolUsuario(str, enum.Enum):
    ADMIN = "admin"
    CHOFER = "chofer"
    DESPACHO = "despacho"
    LOGISTICA = "logistica"

class TipoCamion(str, enum.Enum):
    SECO = "seco"
    REFRIGERADO = "refrigerado"
    MIXTO = "mixto"

class Prioridad(str, enum.Enum):
    NORMAL = "normal"
    URGENTE = "urgente"
    CRITICO = "critico"

# ========================================
# MODELOS
# ========================================

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, index=True, nullable=False)  # Para login simple
    nombre = Column(String(100), nullable=False)
    pin = Column(String(10), nullable=False)  # PIN simple de 4 dígitos
    rol = Column(Enum(RolUsuario), nullable=False)
    activo = Column(Boolean, default=True)
    telefono = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    camiones = relationship("Camion", back_populates="chofer")
    movimientos_asignados = relationship("Movimiento", back_populates="asignado_por", foreign_keys="Movimiento.asignado_por_id")


class Camion(Base):
    __tablename__ = "camiones"
    
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(20), unique=True, index=True, nullable=False)
    tipo = Column(Enum(TipoCamion), nullable=False)
    chofer_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    capacidad = Column(String(50), nullable=True)  # Ej: "10 toneladas"
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    chofer = relationship("Usuario", back_populates="camiones")
    movimientos = relationship("Movimiento", back_populates="camion")


class Rampa(Base):
    __tablename__ = "rampas"
    
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False)
    nombre = Column(String(50), nullable=True)  # Ej: "Rampa 1 - Secos"
    tipo_permitido = Column(Enum(TipoCamion), nullable=True)  # None = cualquier tipo
    estado = Column(Enum(EstadoRampa), default=EstadoRampa.LIBRE)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    movimientos = relationship("Movimiento", back_populates="rampa")


class Movimiento(Base):
    """
    Registro principal de cada ciclo de un camión en el patio.
    Cada entrada al CD genera un nuevo movimiento.
    """
    __tablename__ = "movimientos"
    
    id = Column(Integer, primary_key=True, index=True)
    camion_id = Column(Integer, ForeignKey("camiones.id"), nullable=False)
    rampa_id = Column(Integer, ForeignKey("rampas.id"), nullable=True)
    asignado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Estado actual
    estado = Column(Enum(EstadoMovimiento), default=EstadoMovimiento.INGRESADO_GARITA)
    prioridad = Column(Enum(Prioridad), default=Prioridad.NORMAL)
    
    # Timestamps de cada etapa
    hora_ingreso_garita = Column(DateTime(timezone=True), server_default=func.now())
    hora_disponible_patio = Column(DateTime(timezone=True), nullable=True)
    hora_solicitado = Column(DateTime(timezone=True), nullable=True)
    hora_asignado = Column(DateTime(timezone=True), nullable=True)
    hora_confirmado_chofer = Column(DateTime(timezone=True), nullable=True)
    hora_en_rampa = Column(DateTime(timezone=True), nullable=True)
    hora_carga_lista = Column(DateTime(timezone=True), nullable=True)
    hora_salida_rampa = Column(DateTime(timezone=True), nullable=True)
    hora_salida_cd = Column(DateTime(timezone=True), nullable=True)
    
    # Notas y observaciones
    notas = Column(Text, nullable=True)
    solicitado_por_despacho = Column(String(100), nullable=True)  # Nombre/área que solicitó
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    camion = relationship("Camion", back_populates="movimientos")
    rampa = relationship("Rampa", back_populates="movimientos")
    asignado_por = relationship("Usuario", back_populates="movimientos_asignados", foreign_keys=[asignado_por_id])


class Notificacion(Base):
    """
    Registro de notificaciones enviadas
    """
    __tablename__ = "notificaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    movimiento_id = Column(Integer, ForeignKey("movimientos.id"), nullable=True)
    
    tipo = Column(String(50), nullable=False)  # asignacion_rampa, carga_lista, etc.
    mensaje = Column(Text, nullable=False)
    leida = Column(Boolean, default=False)
    confirmada = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    leida_at = Column(DateTime(timezone=True), nullable=True)
    confirmada_at = Column(DateTime(timezone=True), nullable=True)


class LogEvento(Base):
    """
    Auditoría de eventos del sistema
    """
    __tablename__ = "log_eventos"
    
    id = Column(Integer, primary_key=True, index=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    accion = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    datos_json = Column(Text, nullable=True)  # Para guardar datos adicionales en JSON
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
