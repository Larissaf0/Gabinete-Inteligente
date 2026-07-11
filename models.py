from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Secretaria(Base):
    __tablename__ = "secretarias"

    # Mudamos para String para aceitar "SEDUC", "Saude", etc., como chave primária direto na URL
    id = Column(String, primary_key=True, index=True) 
    nome = Column(String, index=True)

    reunioes = relationship("Reuniao", back_populates="secretaria")

class Reuniao(Base):
    __tablename__ = "reunioes"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    
    # Adicionando os campos que o seu formulário envia e o main.py recebe:
    data = Column(String, nullable=True)
    hora = Column(String, nullable=True)
    
    # Chave estrangeira ajustada para tipo String para combinar com o ID da secretaria
    secretaria_id = Column(String, ForeignKey("secretarias.id"))

    secretaria = relationship("Secretaria", back_populates="reunioes")