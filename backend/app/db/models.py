import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Date, DateTime, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    industry = Column(String)
    location = Column(String)
    base_sustainability_score = Column(Float)
    
    certifications = relationship("Certification", back_populates="supplier")
    risk_profile = relationship("RiskProfile", back_populates="supplier", uselist=False)

class Certification(Base):
    __tablename__ = "certifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    name = Column(String, nullable=False)
    valid_until = Column(Date)
    
    supplier = relationship("Supplier", back_populates="certifications")

class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), unique=True)
    concentration_risk = Column(Float)
    operational_risk = Column(Float)
    geopolitical_risk = Column(Float)
    
    supplier = relationship("Supplier", back_populates="risk_profile")

class Product(Base):
    __tablename__ = "products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    name = Column(String, nullable=False)
    category = Column(String)
    unit_price = Column(Float)

class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_date = Column(DateTime, default=func.now())
    total_cost = Column(Float)

class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    shipping_mode = Column(String)
    emissions_kg = Column(Float)

class Recommendation(Base):
    """Persisted record of every agent recommendation and its approval decision."""
    __tablename__ = "recommendations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    alternative = Column(String)
    current_supplier = Column(String)
    status = Column(String, default="pending")  # pending | approved | rejected
    reasoning = Column(Text)
    cost_impact = Column(String)
    risk_impact = Column(String)
    sustainability_impact = Column(String)
    evidence = Column(JSONB, default=list)       # list of strings
    sources = Column(JSONB, default=list)         # list of strings
    confidence = Column(Integer)
    decision_score = Column(Integer)
    cost_score = Column(Integer)
    delivery_score = Column(Integer)
    risk_score = Column(Integer)
    sustainability_score = Column(Integer)
    location_score = Column(Integer)
    candidates = Column(JSONB, default=list)      # array of evaluated suppliers
    agent_trace = Column(JSONB, default=list)     # list of trace step dicts
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)
