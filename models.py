from sqlalchemy import Column, Integer, String#, Mapped, mapped_as_dataclass, mapped_column, registry
# from sqlalchemy import func
from datetime import datetime
from database import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

#table_registry = registry()

class Secretaria(Base):
    __tablename__ = "secretarias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    descricao = Column(String, index=True)
    def __repr__(self):
        return f"<Secretaria(nome='{self.nome}', descricao='{self.descricao}')>"


# # @mapped_as_dataclass(table_registry)
# # class User:
# #     __tablename__ = 'users'

# #     id: Mapped[int] = mapped_column(init=False, primary_key=True)
# #     username: Mapped[str] = mapped_column(unique=True)
# #     password: Mapped[str]
# #     email: Mapped[str] = mapped_column(unique=True)
# #     created_at: Mapped[datetime] = mapped_column(
# #         init=False, server_default=func.now()
# #     )

