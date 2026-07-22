from sqlalchemy.orm import Session
from sqladmin import Admin, ModelView
from http import HTTPStatus
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import Base, engine
from datetime import datetime
from zoneinfo import ZoneInfo
import database
import models

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

templates = Jinja2Templates(directory="templates")
RECAPTCHA_SECRET_KEY = "6LfImgQtAAAAALk3enMyZUDRMqRTH3LRD1bO5K-e"

fuso_br = ZoneInfo("America/Recife")

# Mapeamento global para deixar o nome com acentuação e espaços corretos na tela
NOMES_SECRETARIAS = {
    "SEDUC": "Educação",
    "FIN": "Finanças",
    "Saude": "Saúde",
    "ADM": "Administração",
    "ServicosPublicos": "Serviços Públicos",
    "SEDTEC": "Desenvolvimento Econômico, Ciência e Tecnologia",
    "CulturaEsportes": "Cultura e Esportes",
    "Obras": "Desenvolvimento Urbano e Obras",
    "SEPLAMA": "Planejamento e Meio Ambiente",
    "Rural": "Desenvolvimento Rural",
    "Social": "Desenvolvimento Social",
    "home": "Gabinete",
    "pauta-livre": "Pauta Livre"
}

# Caminhos padrão das imagens associadas aos IDs exatos usados nas rotas
LOGOS_SECRETARIAS = {
    "ADM": "/static/imagens/adm_bg.png",
    "Saude": "/static/imagens/saude_bg.png",
    "SEDUC": "/static/imagens/seduc_bg.png",
    "Obras":"/static/imagens/obras_bg.png",
    "FIN": "/static/imagens/fin_bg.png",
    "ServicosPublicos": "/static/imagens/servpub_bg.png",
    "SEDTEC": "/static/imagens/sedtec_bg.png",
    "CulturaEsportes": "/static/imagens/secult_bg.png",
    "SEPLAMA": "/static/imagens/seplama_bg.png",
    "Rural": "/static/imagens/rural_bg.png",
    "Social": "/static/imagens/social_bg.png",
    "home":"/static/imagens/padrao_bg.png",
    "pauta-livre": "/static/imagens/padrao_bg.png"
}

# Função para buscar no database o BG da página
def obter_logo_secretaria(sec_id: str, db: Session) -> str:
    # 1. Tenta buscar da tabela do banco de dados primeiro
    secretaria = db.query(models.Secretaria).filter(models.Secretaria.id == sec_id).first()
    if secretaria and getattr(secretaria, 'logo_url', None):
        return secretaria.logo_url
    
    return LOGOS_SECRETARIAS.get(sec_id, "/static/imagens")

admin = Admin(app, engine, title="Painel de Controle - Gabinete")

class ReuniaoAdmin(ModelView, model=models.Reuniao):
    name = "Reunião"
    name_plural = "Reuniões"
    icon = "fa-solid fa-calendar"
    column_list = [models.Reuniao.id, models.Reuniao.titulo, models.Reuniao.data, models.Reuniao.hora, models.Reuniao.secretaria_id]
    column_searchable_list = [models.Reuniao.titulo, models.Reuniao.data]
    column_filters = [models.Reuniao.secretaria_id, models.Reuniao.data]

class SecretariaAdmin(ModelView, model=models.Secretaria):
    name = "Secretaria"
    name_plural = "Secretarias"
    icon = "fa-solid fa-building"
    column_list = [models.Secretaria.id, models.Secretaria.nome]
    column_searchable_list = [models.Secretaria.nome]

admin.add_view(ReuniaoAdmin)
admin.add_view(SecretariaAdmin)


# Landing page (Login)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    g_recaptcha_response: str = Form(alias="g-recaptcha-response")
):
    if not g_recaptcha_response:
        raise HTTPException(status_code=400, detail="Por favor, marque a caixa 'Não Sou um robô'.")

    async with httpx.AsyncClient() as client:
        url_google = "https://www.google.com/recaptcha/api/siteverify"
        dados_validacao = {
            "secret": RECAPTCHA_SECRET_KEY,
            "response": g_recaptcha_response
        }
        resposta = await client.post(url_google, data=dados_validacao)
        resultado_google = resposta.json()

    if not resultado_google.get("success"):
        raise HTTPException(status_code=400, detail="Falha na verificação do reCAPTCHA. Tente novamente.")

    if username == "admin" and password == "1234":
        return RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)
    
    raise HTTPException(status_code=401, detail="Usuário ou senha incorretos.")

# Tela de Solicitar Acesso
@app.get("/solicitar-acesso", response_class=HTMLResponse)
async def tela_solicitar_acessp(request: Request):
    return templates.TemplateResponse(request=request, name="solicitar_acesso.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/imagens/favicon.ico")

# Tela HOME principal pós-login
@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request, sec_id: str = "home", db: Session = Depends(get_db)):
    usuario = {"nome": "admin"}

    logo_da_vez = obter_logo_secretaria(sec_id, db)

    return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "usuario": usuario,
                "logo_secretaria": logo_da_vez
            }
    )

# --- Rota para listar todas as Reunioes da Secretaria ---
@app.get("/secretaria/{sec_id}/reunioes", response_class=HTMLResponse)
async def listar_todas_reunioes(request: Request, sec_id: str, pagina: int = 1, db: Session = Depends(get_db)):
    usuario = {"nome": "admin"}
    
    itens_por_pagina = 8
    offset = (pagina - 1) * itens_por_pagina

    total_registros = db.query(models.Reuniao).filter(models.Reuniao.secretaria_id == sec_id).count()
    total_paginas = max(1, (total_registros + itens_por_pagina - 1) // itens_por_pagina)

    reunioes_do_banco = db.query(models.Reuniao)\
            .filter(models.Reuniao.secretaria_id == sec_id)\
            .order_by(models.Reuniao.id.desc())\
            .offset(offset)\
            .limit(itens_por_pagina)\
            .all()

    lista_reunioes = []
    for r in reunioes_do_banco:
        nome_sec = NOMES_SECRETARIAS.get(r.secretaria_id, "Gabinete")
        lista_reunioes.append({
            "id": r.id,
            "titulo": r.titulo,
            "assunto": f"Demanda vinculada à Secretaria de {nome_sec}",
            "data": r.data if r.data else "--/--/----",
            "hora": r.hora if r.hora else "--:--",
            "local": f"Sala da Secretaria de {nome_sec}" if r.secretaria_id else "Sala do Gabinete",
            "status": "Agendada",
            "participantes": [{"iniciais": "ADM"}]
        })

    # Coleta a imagem correspondente de forma dinâmica
    logo_da_vez = obter_logo_secretaria(sec_id, db)

    de_registro = offset + 1 if total_registros > 0 else 0
    ate_registro = min(offset + itens_por_pagina, total_registros)

    contexto = {
        "usuario": usuario,
        "sec_id": sec_id,
        "reunioes": lista_reunioes,
        "pagina_atual": pagina,
        "total_paginas": total_paginas,
        "de_registro": de_registro,
        "ate_registro": ate_registro,
        "total_registros": total_registros,
        "logo_secretaria": logo_da_vez
    }

    return templates.TemplateResponse(request, "reunioes.html", context=contexto)


# Rota para a página interna da secretaria (Dashboard específico)
@app.get("/secretaria/{sec_id}", response_class=HTMLResponse)
async def sec_home(request: Request, sec_id: str, db: Session = Depends(get_db)):
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    reunioes_do_banco = db.query(models.Reuniao).filter(models.Reuniao.secretaria_id == sec_id).all()
    
    lista_reunioes = []
    for r in reunioes_do_banco:
        lista_reunioes.append({
            "titulo": r.titulo,
            "data_hora": f"{r.data} às {r.hora}" if r.hora else r.data,
            "encaminhamentos_qtd": getattr(r, 'encaminhamentos_qtd', 0)
        })
        
    total_reunioes = len(reunioes_do_banco)
    kpis_reais = {
        "abertas": total_reunioes,
        "em_andamento": 0,
        "concluidas": 0,
        "atrasadas": 0,
        "vencem_hoje": 0,
        "vencem_semana": 0
    }
    
    # Coleta a imagem correspondente de forma dinâmica
    logo_da_vez = obter_logo_secretaria(sec_id, db)

    contexto = {
        "sec_id": sec_id,
        "secretaria_nome": secretaria_nome,
        "notificacoes_qtd": 0,
        "kpis": kpis_reais,
        "prazos": [],
        "reunioes": lista_reunioes,
        "logo_secretaria": logo_da_vez
    }
    
    return templates.TemplateResponse(request, "sec_home.html", context=contexto)


# Rota para renderizar o formulário da NOVA REUNIÃO
@app.get("/secretaria/{sec_id}/nova-reuniao", response_class=HTMLResponse)
async def exibir_formulario_reuniao(request: Request, sec_id: str, db: Session = Depends(get_db)):
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    data_atual = datetime.now(fuso_br).strftime("%d/%m/%Y")
    hora_atual = datetime.now(fuso_br).strftime("%H:%M")
    
    # Coleta a imagem correspondente
    logo_da_vez = obter_logo_secretaria(sec_id, db)
    
    return templates.TemplateResponse(
        request=request, 
        name="nova_reuniao.html", 
        context={
            "sec_id": sec_id, 
            "secretaria_nome": secretaria_nome,
            "data_atual": data_atual,
            "hora_atual": hora_atual,
            "logo_secretaria": logo_da_vez 
        }
    )

# Rota POST para salvar nova reunião
@app.post("/secretaria/{sec_id}/salvar-reuniao")
async def salvar_reuniao(
    sec_id: str, 
    titulo: str = Form(...), 
    data: str = Form(None),
    hora: str = Form(None),
    db: Session = Depends(get_db)
):
    db_reuniao = models.Reuniao(
        titulo=titulo,
        data=data,
        hora=hora,
        secretaria_id=sec_id
    )
    db.add(db_reuniao)
    db.commit()
    
    print(f"Gravando Reunião no BD -> Título: {titulo} | Secretaria vinculada: {sec_id}")
    return RedirectResponse(url=f"/secretaria/{sec_id}", status_code=status.HTTP_303_SEE_OTHER)

# Página de pauta livre
@app.get("/pauta-livre", response_class=HTMLResponse)
async def pauta_livre(request: Request, sec_id: str = "pauta-livre", db: Session = Depends(get_db)):
    data_atual = datetime.now(fuso_br).strftime("%d/%m/%Y")
    hora_atual = datetime.now(fuso_br).strftime("%H:%M")
    logo_da_vez = obter_logo_secretaria(sec_id, db)
    
    return templates.TemplateResponse(
            request=request,
            name="pauta_livre.html",
            context={
                "data_atual": data_atual,
                "hora_atual": hora_atual,
                "logo_secretaria": logo_da_vez
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)