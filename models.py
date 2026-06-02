from sqlalchemy import Column, Integer, String
from database import Base

class Secretaria(Base):
    __tablename__ = "secretarias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    descricao = Column(String, index=True)
    def __repr__(self):
        return f"<Secretaria(nome='{self.nome}', descricao='{self.descricao}')>"