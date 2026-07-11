from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Secretaria(Base):
    __tablename__ = "secretarias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)

    reunioes = relationship("Reuniao", back_populates="secretaria")

class Reuniao(Base):
    __tablename__ = "reunioes"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)
    secretaria_id = Column(Integer,ForeignKey("secretarias.id"))

    secretaria = relationship("Secretaria", back_populates="reunioes")