"""
Modèles SQLAlchemy pour GuignoMap v5.0
Basés sur le schéma SQLite existant pour compatibilité
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Real
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Street(Base):
    __tablename__ = 'streets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True)
    sector = Column(Text)
    team = Column(Text)
    status = Column(Text, nullable=False, default='a_faire')
    
    # Relations
    notes = relationship("Note", back_populates="street", cascade="all, delete-orphan")
    addresses = relationship("Address", back_populates="street", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)


class Note(Base):
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    street_name = Column(Text, ForeignKey('streets.name'), nullable=False)
    team_id = Column(Text, ForeignKey('teams.id'), nullable=False)
    address_number = Column(Text)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    street = relationship("Street", back_populates="notes")


class ActivityLog(Base):
    __tablename__ = 'activity_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Text)
    action = Column(Text, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Address(Base):
    __tablename__ = 'addresses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    street_name = Column(Text, ForeignKey('streets.name'), nullable=False)
    house_number = Column(Text, nullable=False)
    latitude = Column(Real)
    longitude = Column(Real)
    osm_type = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    street = relationship("Street", back_populates="addresses")