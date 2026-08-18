"""
Data models and schemas for Gabinete Inteligente (Python/FastAPI)
"""
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class ParticipanteSchema(BaseModel):
    nome: str
    iniciais: Optional[str] = None
    cargo: Optional[str] = "Participante"

class EncaminhamentoSchema(BaseModel):
    id: Optional[int] = None
    tarefa: str
    responsavel: str
    prazo: str
    prioridade: Optional[str] = "Média"
    status: Optional[str] = "aberta"
    progresso: Optional[int] = 10
    concluido: Optional[bool] = False

class ReuniaoCreateSchema(BaseModel):
    titulo: str
    assunto: Optional[str] = None
    local: str
    participantes: Optional[str] = ""
    anotacoes: Optional[str] = ""
    data: Optional[str] = None
    hora: Optional[str] = None

class StatusUpdateSchema(BaseModel):
    reuniao_id: int
    encaminhamento_index: int
    novo_status: str
    novo_progresso: Optional[int] = None

class UsuarioPerfilSchema(BaseModel):
    nome: str
    email: str
    cargo: Optional[str] = ""
    secretaria: Optional[str] = "home"
    telefone: Optional[str] = ""

class UsuarioSenhaSchema(BaseModel):
    senha_atual: str
    nova_senha: str
    confirmar_senha: str
