from pydantic import BaseModel
from datetime import date
from typing import Optional
from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Secretaria, Reuniao, Demanda
from datetime import datetime
from pytz import timezone

class DemandaCreate(BaseModel):
    titulo: str
    descricao: str | None = None
    secretaria_id: str
    reuniao_id: int
    responsavel: str | None = None
    prioridade: str = "Média"
    prazo: date | None = None

class DemandaResponse(DemandaCreate):
    id: int
    status: str

    class Config:
        from_attributes = True