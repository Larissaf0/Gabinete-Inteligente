from fastapi import FastAPI, Request, Form, Depends, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from datetime import datetime
from zoneinfo import ZoneInfo
import pytz

from database import (
    usuario_db,
    participantes_db,
    reunioes_db,
    NOMES_SECRETARIAS,
    LOGOS_SECRETARIAS,
    obter_logo_secretaria
)
from models import StatusUpdateSchema

app = FastAPI(title="Gabinete Inteligente")
TZ_RECIFE = ZoneInfo("America/Recife")

# Monta arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configura templates Jinja2
templates = Jinja2Templates(directory="templates")

def get_formatted_date_and_hour():
    now = datetime.now(TZ_RECIFE)
    data_atual = now.strftime('%d/%m/%Y')
    hora_atual = now.strftime('%H:%M')
    return data_atual, hora_atual

def formatar_data_entrada(data_str, fallback_data):
    if not data_str or not str(data_str).strip():
        return fallback_data
    val = str(data_str).strip()
    parts = val.split('-')
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return val

def formatar_hora_entrada(hora_str, fallback_hora):
    if not hora_str or not str(hora_str).strip():
        return fallback_hora
    return str(hora_str).strip()

def parse_date_br(data_str):
    if not data_str:
        return None

    try:
        parts = data_str.strip().split("/")

        if len(parts) == 3:
            dia = int(parts[0])
            mes = int(parts[1])
            ano = int(parts[2])

            return datetime(
                ano,
                mes,
                dia,
                0,
                0,
                0,
                tzinfo=TZ_RECIFE
            )

    except (ValueError, TypeError):
        pass

    return None

def parse_data_hora(data_str, hora_str):
    if not data_str:
        return 0
    d = str(data_str).strip()
    h = str(hora_str or "00:00").strip()
    year, month, day = 2026, 1, 1
    if "/" in d:
        parts = d.split("/")
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    elif "-" in d:
        parts = d.split("-")
        if len(parts) == 3:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    
    hour, minute = 0, 0
    if ":" in h:
        hparts = h.split(":")
        hour, minute = int(hparts[0]), int(hparts[1])
    
    try:
        return datetime(year, month, day, hour, minute).timestamp()
    except Exception:
        return 0

def ordenar_reunioes_cronologicamente():
    reunioes_db.sort(key=lambda r: parse_data_hora(r.get("data"), r.get("hora")), reverse=True)

# Executa ordenacao inicial
ordenar_reunioes_cronologicamente()

def processar_e_salvar_participantes(input_str: str):
    if not input_str or not input_str.strip():
        return []
    raw_list = [s.strip() for s in input_str.split(',') if s.strip()]
    result = []
    for raw in raw_list:
        existing = next((p for p in participantes_db if p["nome"].lower() == raw.lower()), None)
        if not existing:
            new_id = max([p["id"] for p in participantes_db], default=0) + 1
            existing = {"id": new_id, "nome": raw, "cargo": "Participante Registrado", "secretaria": "Gabinete"}
            participantes_db.append(existing)
        
        words = [w for w in raw.split() if w]
        iniciais = "PT"
        if len(words) >= 2:
            iniciais = (words[0][0] + words[-1][0]).upper()
        elif len(words) == 1:
            iniciais = words[0][:2].upper()

        result.append({
            "nome": existing["nome"],
            "iniciais": iniciais,
            "cargo": existing["cargo"]
        })
    return result

def extract_all_demandas(sec_id="home"):
    demandas = []
    hoje = datetime.now(TZ_RECIFE).replace(hour=0, minute=0, second=0, microsecond=0)
    card_counter = 1

    for r in reunioes_db:
        if sec_id != "home" and r.get("secretaria_id") != sec_id:
            continue

        sec_key = r.get("secretaria_id", "home")
        sec_nome = NOMES_SECRETARIAS.get(sec_key, sec_key)

        encs = r.get("encaminhamentos", [])
        if not encs or len(encs) == 0:
            encs = [{
                "id": 1,
                "tarefa": r.get("titulo", "Demanda da Reunião"),
                "responsavel": "Gabinete",
                "prazo": r.get("data", "A definir"),
                "prioridade": "Média",
                "status": "aberta",
                "progresso": 10
            }]

        for idx, enc in enumerate(encs):
            status = enc.get("status", "aberta")
            dt_prazo = parse_date_br(enc.get("prazo"))

            vence_hoje = False
            vence_semana = False

            if dt_prazo:
                diff = (dt_prazo - hoje).days
                if diff == 0:
                    vence_hoje = True
                    vence_semana = True
                elif 0 < diff <= 7:
                    vence_semana = True
                elif diff < 0 and status != "concluida":
                    status = "atrasada"

            progresso = enc.get("progresso", 10)
            if status == "concluida":
                progresso = 100
            elif status == "em_andamento" and progresso < 50:
                progresso = 50

            demandas.append({
                "id": f"{r['id']}_{idx}_{card_counter}",
                "reuniao_id": r["id"],
                "reuniao_titulo": r.get("titulo", "Sem título"),
                "secretaria_id": sec_key,
                "secretaria_nome": sec_nome,
                "encaminhamento_index": idx,
                "tarefa": enc.get("tarefa", r.get("titulo", "Demanda sem título")),
                "responsavel": enc.get("responsavel", "Gabinete"),
                "prazo": enc.get("prazo", "A definir"),
                "prioridade": enc.get("prioridade", "Média"),
                "status": status,
                "progresso": progresso,
                "vence_hoje": vence_hoje,
                "vence_semana": vence_semana
            })
            card_counter += 1

    return demandas

# Routes

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if (username == "admin" and password == usuario_db["senha"]) or (username and password):
        return RedirectResponse(url="/home", status_code=303)
    return HTMLResponse(content="Usuário ou senha incorretos", status_code=401)

@app.get("/solicitar-acesso", response_class=HTMLResponse)
async def solicitar_acesso_page(request: Request, enviado: bool = False):
    return templates.TemplateResponse(request=request, name="solicitar_acesso.html", context={"enviado": enviado})

@app.post("/enviar-solicitacao")
async def enviar_solicitacao(request: Request, nome: str = Form(...), email: str = Form(...), secretaria: str = Form(...)):
    return RedirectResponse(url="/solicitar-acesso?enviado=true", status_code=303)

@app.get("/esqueci-senha", response_class=HTMLResponse)
async def esqueci_senha_page(request: Request, enviado: bool = False):
    return templates.TemplateResponse(request=request, name="esqueci_senha.html", context={"enviado": enviado})

@app.post("/enviar-recuperacao")
async def enviar_recuperacao(request: Request, email: str = Form(...)):
    return RedirectResponse(url="/esqueci-senha?enviado=true", status_code=303)

@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request, sec_id: str = "home"):
    logo = obter_logo_secretaria(sec_id)
    return templates.TemplateResponse(request=request, name="home.html", context={
        "usuario": usuario_db,
        "logo_secretaria": logo
    })

@app.get("/configuracoes", response_class=HTMLResponse)
async def configuracoes_page(request: Request, msg: str = None, erro: str = None):
    logo = obter_logo_secretaria("home")
    return templates.TemplateResponse(request=request, name="configuracoes.html", context={
        "usuario": usuario_db,
        "secretarias": NOMES_SECRETARIAS,
        "logo_secretaria": logo,
        "msg": msg,
        "erro": erro
    })

@app.post("/configuracoes/perfil")
async def atualizar_perfil(
    nome: str = Form(...),
    email: str = Form(...),
    cargo: str = Form(""),
    secretaria: str = Form("home"),
    telefone: str = Form("")
):
    nome_limpo = nome.strip()
    usuario_db["nome"] = nome_limpo
    usuario_db["inicial"] = nome_limpo[:2].upper() if len(nome_limpo) >= 2 else (nome_limpo.upper() if nome_limpo else "AD")
    usuario_db["email"] = email.strip()
    usuario_db["cargo"] = cargo.strip()
    usuario_db["secretaria"] = secretaria.strip()
    usuario_db["telefone"] = telefone.strip()
    return RedirectResponse(url="/configuracoes?msg=perfil_atualizado", status_code=303)

@app.post("/configuracoes/senha")
async def atualizar_senha(
    senha_atual: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...)
):
    if len(nova_senha) < 4:
        return RedirectResponse(url="/configuracoes?erro=senha_curta", status_code=303)
    if nova_senha != confirmar_senha:
        return RedirectResponse(url="/configuracoes?erro=senha_divergente", status_code=303)
    
    usuario_db["senha"] = nova_senha
    return RedirectResponse(url="/configuracoes?msg=senha_atualizada", status_code=303)

@app.post("/configuracoes/preferencias")
async def atualizar_preferencias(
    notif_email: bool = Form(False),
    notif_whatsapp: bool = Form(False)
):
    usuario_db["notif_email"] = notif_email
    usuario_db["notif_whatsapp"] = notif_whatsapp
    return RedirectResponse(url="/configuracoes?msg=preferencias_atualizadas", status_code=303)

@app.get("/reunioes", response_class=HTMLResponse)
async def reunioes_geral(request: Request):
    return RedirectResponse(url="/secretaria/home/reunioes", status_code=303)

@app.get("/pauta-livre", response_class=HTMLResponse)
async def pauta_livre_page(request: Request):
    data_atual, hora_atual = get_formatted_date_and_hour()
    logo = obter_logo_secretaria("pauta-livre")
    return templates.TemplateResponse(request=request, name="pauta_livre.html", context={
        "data_atual": data_atual,
        "hora_atual": hora_atual,
        "participantes_db": participantes_db,
        "usuario": usuario_db,
        "logo_secretaria": logo
    })

@app.post("/salvar-reuniao")
async def salvar_pauta_livre(
    titulo: str = Form(...),
    assunto: str = Form("Pauta Geral"),
    local: str = Form("Gabinete do Prefeito"),
    participantes: str = Form(""),
    anotacoes: str = Form(""),
    data: str = Form(None),
    hora: str = Form(None)
):
    data_atual, hora_atual = get_formatted_date_and_hour()
    dt = formatar_data_entrada(data, data_atual)
    hr = formatar_hora_entrada(hora, hora_atual)
    novo_id = max([r["id"] for r in reunioes_db], default=0) + 1
    
    part_list = processar_e_salvar_participantes(participantes)

    nova_reuniao = {
        "id": novo_id,
        "titulo": titulo,
        "assunto": assunto,
        "data": dt,
        "hora": hr,
        "secretaria_id": "home",
        "status": "Agendada",
        "local": local,
        "anotacoes": anotacoes,
        "participantes": part_list,
        "encaminhamentos": []
    }
    reunioes_db.append(nova_reuniao)
    ordenar_reunioes_cronologicamente()
    return RedirectResponse(url=f"/secretaria/home/reuniao/{novo_id}", status_code=303)

@app.get("/secretaria/{sec_id}/nova-reuniao", response_class=HTMLResponse)
async def nova_reuniao_page(request: Request, sec_id: str):
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    logo = obter_logo_secretaria(sec_id)
    data_atual, hora_atual = get_formatted_date_and_hour()
    return templates.TemplateResponse(request=request, name="nova_reuniao.html", context={
        "sec_id": sec_id,
        "secretaria_nome": secretaria_nome,
        "data_atual": data_atual,
        "hora_atual": hora_atual,
        "participantes_db": participantes_db,
        "usuario": usuario_db,
        "logo_secretaria": logo
    })

@app.post("/secretaria/{sec_id}/salvar-reuniao")
async def salvar_reuniao_secretaria(
    sec_id: str,
    titulo: str = Form(...),
    local: str = Form("Não especificado"),
    participantes: str = Form(""),
    anotacoes: str = Form(""),
    data: str = Form(None),
    hora: str = Form(None)
):
    data_atual, hora_atual = get_formatted_date_and_hour()
    dt = formatar_data_entrada(data, data_atual)
    hr = formatar_hora_entrada(hora, hora_atual)
    novo_id = max([r["id"] for r in reunioes_db], default=0) + 1

    part_list = processar_e_salvar_participantes(participantes)

    nova_reuniao = {
        "id": novo_id,
        "titulo": titulo,
        "assunto": f"Pauta de {NOMES_SECRETARIAS.get(sec_id, sec_id)}",
        "data": dt,
        "hora": hr,
        "secretaria_id": sec_id,
        "status": "Agendada",
        "local": local,
        "anotacoes": anotacoes,
        "participantes": part_list,
        "encaminhamentos": []
    }
    reunioes_db.append(nova_reuniao)
    ordenar_reunioes_cronologicamente()
    return RedirectResponse(url=f"/secretaria/{sec_id}/reuniao/{novo_id}", status_code=303)

@app.get("/secretaria/{sec_id}/reuniao/{meeting_id}/editar", response_class=HTMLResponse)
async def editar_reuniao_page(request: Request, sec_id: str, meeting_id: int):
    reuniao = next((r for r in reunioes_db if r["id"] == meeting_id), None)
    if not reuniao:
        return RedirectResponse(url=f"/secretaria/{sec_id}/reunioes", status_code=303)
    
    sec_id_real = reuniao.get("secretaria_id", sec_id)
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id_real, sec_id_real)
    logo = obter_logo_secretaria(sec_id_real)

    data_input = ""
    dt_str = reuniao.get("data", "")
    if "/" in dt_str:
        parts = dt_str.split("/")
        if len(parts) == 3:
            data_input = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    elif "-" in dt_str:
        data_input = dt_str

    hora_input = reuniao.get("hora", "")[:5] if reuniao.get("hora") else ""

    parts_arr = reuniao.get("participantes", [])
    participantes_str = ""
    if isinstance(parts_arr, list):
        participantes_str = ", ".join([p.get("nome", "") if isinstance(p, dict) else str(p) for p in parts_arr if p])
    elif isinstance(parts_arr, str):
        participantes_str = parts_arr

    return templates.TemplateResponse(request=request, name="editar_reuniao.html", context={
        "sec_id": sec_id_real,
        "secretaria_nome": secretaria_nome,
        "reuniao": reuniao,
        "data_input": data_input,
        "hora_input": hora_input,
        "participantes_str": participantes_str,
        "participantes_db": participantes_db,
        "usuario": usuario_db,
        "logo_secretaria": logo
    })

@app.get("/reuniao/{meeting_id}/editar")
async def editar_reuniao_atalho(meeting_id: int):
    reuniao = next((r for r in reunioes_db if r["id"] == meeting_id), None)
    sec_id = reuniao.get("secretaria_id", "home") if reuniao else "home"
    return RedirectResponse(url=f"/secretaria/{sec_id}/reuniao/{meeting_id}/editar", status_code=303)

@app.post("/secretaria/{sec_id}/reuniao/{meeting_id}/salvar-edicao")
async def salvar_edicao_reuniao(
    sec_id: str,
    meeting_id: int,
    titulo: str = Form(...),
    assunto: str = Form(None),
    local: str = Form(None),
    participantes: str = Form(""),
    anotacoes: str = Form(""),
    data: str = Form(None),
    hora: str = Form(None)
):
    reuniao = next((r for r in reunioes_db if r["id"] == meeting_id), None)
    if not reuniao:
        return RedirectResponse(url=f"/secretaria/{sec_id}/reunioes", status_code=303)

    data_atual, hora_atual = get_formatted_date_and_hour()
    
    if titulo: reuniao["titulo"] = titulo
    if assunto is not None: reuniao["assunto"] = assunto
    if data: reuniao["data"] = formatar_data_entrada(data, data_atual)
    if hora: reuniao["hora"] = formatar_hora_entrada(hora, hora_atual)
    if local: reuniao["local"] = local.strip()
    if anotacoes is not None: reuniao["anotacoes"] = anotacoes
    reuniao["participantes"] = processar_e_salvar_participantes(participantes)
    ordenar_reunioes_cronologicamente()

    sec_id_real = reuniao.get("secretaria_id", sec_id)
    return RedirectResponse(url=f"/secretaria/{sec_id_real}/reuniao/{meeting_id}", status_code=303)

@app.api_route("/reuniao/{meeting_id}/excluir", methods=["GET", "POST"])
@app.api_route("/reuniao/{meeting_id}/excluir/", methods=["GET", "POST"])
async def excluir_reuniao_direta(meeting_id: int):
    global reunioes_db
    reuniao = next((r for r in reunioes_db if int(r.get("id", 0)) == int(meeting_id)), None)
    target_sec_id = reuniao.get("secretaria_id", "home") if reuniao else "home"
    reunioes_db = [r for r in reunioes_db if int(r.get("id", 0)) != int(meeting_id)]
    return RedirectResponse(url=f"/secretaria/{target_sec_id}/reunioes", status_code=303)

@app.api_route("/secretaria/{sec_id}/reuniao/{meeting_id}/excluir", methods=["GET", "POST"])
@app.api_route("/secretaria/{sec_id}/reuniao/{meeting_id}/excluir/", methods=["GET", "POST"])
async def excluir_reuniao_secretaria(sec_id: str, meeting_id: int):
    global reunioes_db
    reunioes_db = [r for r in reunioes_db if int(r.get("id", 0)) != int(meeting_id)]
    return RedirectResponse(url=f"/secretaria/{sec_id}/reunioes", status_code=303)

@app.get("/secretaria/{sec_id}/reunioes", response_class=HTMLResponse)
async def listar_reunioes(request: Request, sec_id: str, pagina: int = 1):
    logo = obter_logo_secretaria(sec_id)
    filtradas = reunioes_db if sec_id == "home" else [r for r in reunioes_db if r["secretaria_id"] == sec_id]
    return templates.TemplateResponse(request=request, name="reunioes.html", context={
        "usuario": usuario_db,
        "sec_id": sec_id,
        "reunioes": filtradas,
        "pagina_atual": pagina,
        "total_paginas": 1,
        "de_registro": 1 if filtradas else 0,
        "ate_registro": len(filtradas),
        "total_registros": len(filtradas),
        "logo_secretaria": logo
    })

@app.get("/secretaria/{sec_id}/reuniao/{meeting_id}", response_class=HTMLResponse)
async def ver_reuniao(request: Request, sec_id: str, meeting_id: int):
    reuniao = next((r for r in reunioes_db if r["id"] == meeting_id), None)
    if not reuniao:
        return RedirectResponse(url=f"/secretaria/{sec_id}/reunioes", status_code=303)
    
    sec_id_real = reuniao.get("secretaria_id", sec_id)
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id_real, sec_id_real)
    logo = obter_logo_secretaria(sec_id_real)
    
    return templates.TemplateResponse(request=request, name="ver_reuniao.html", context={
        "sec_id": sec_id_real,
        "secretaria_nome": secretaria_nome,
        "reuniao": reuniao,
        "usuario": usuario_db,
        "logo_secretaria": logo
    })

@app.get("/reuniao/{meeting_id}")
async def ver_reuniao_atalho(meeting_id: int):
    reuniao = next((r for r in reunioes_db if r["id"] == meeting_id), None)
    sec_id = reuniao.get("secretaria_id", "home") if reuniao else "home"
    return RedirectResponse(url=f"/secretaria/{sec_id}/reuniao/{meeting_id}", status_code=303)

@app.get("/secretaria/{sec_id}", response_class=HTMLResponse)
async def secretaria_dashboard(request: Request, sec_id: str):
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    logo = obter_logo_secretaria(sec_id)
    filtradas = reunioes_db if sec_id == "home" else [r for r in reunioes_db if r["secretaria_id"] == sec_id]
    
    return templates.TemplateResponse(request=request, name="sec_home.html", context={
        "sec_id": sec_id,
        "secretaria_nome": secretaria_nome,
        "notificacoes_qtd": 0,
        "kpis": {"abertas": len(filtradas), "em_andamento": 0, "concluidas": 0},
        "prazos": [],
        "reunioes": filtradas,
        "usuario": usuario_db,
        "logo_secretaria": logo
    })

# Quadro Kanban Route
@app.get("/secretaria/{sec_id}/kanban", response_class=HTMLResponse)
async def kanban_board(request: Request, sec_id: str, status_filtro: str = "todos"):
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    logo = obter_logo_secretaria(sec_id)

    demandas = extract_all_demandas(sec_id)

    colunas = {
        "aberta": [d for d in demandas if d["status"] == "aberta"],
        "em_andamento": [d for d in demandas if d["status"] == "em_andamento"],
        "concluida": [d for d in demandas if d["status"] == "concluida"],
        "atrasada": [d for d in demandas if d["status"] == "atrasada"]
    }

    kpis = {
        "total": len(demandas),
        "abertas": len(colunas["aberta"]),
        "em_andamento": len(colunas["em_andamento"]),
        "concluidas": len(colunas["concluida"]),
        "atrasadas": len(colunas["atrasada"]),
        "vencem_hoje": len([d for d in demandas if d["vence_hoje"]]),
        "vencem_semana": len([d for d in demandas if d["vence_semana"]])
    }

    return templates.TemplateResponse(request=request, name="kanban.html", context={
        "sec_id": sec_id,
        "secretaria_nome": secretaria_nome,
        "usuario": usuario_db,
        "logo_secretaria": logo,
        "demandas": demandas,
        "colunas": colunas,
        "kpis": kpis,
        "status_filtro": status_filtro
    })

# API para atualização de status de encaminhamento/demanda
@app.post("/api/demanda/status")
async def atualizar_status_demanda(body: StatusUpdateSchema):
    meeting_id = body.reuniao_id
    idx = body.encaminhamento_index
    novo_status = body.novo_status
    novo_progresso = body.novo_progresso

    reuniao = next((r for r in reunioes_db if r["id"] == meeting_id), None)
    if reuniao:
        if "encaminhamentos" not in reuniao or not reuniao["encaminhamentos"]:
            reuniao["encaminhamentos"] = [{
                "id": 1,
                "tarefa": reuniao.get("titulo", "Demanda da Reunião"),
                "responsavel": "Gabinete",
                "prazo": reuniao.get("data", "A definir"),
                "prioridade": "Média",
                "status": novo_status,
                "progresso": 10,
                "concluido": False
            }]

        valid_idx = idx if 0 <= idx < len(reuniao["encaminhamentos"]) else 0
        item = reuniao["encaminhamentos"][valid_idx]

        item["status"] = novo_status
        if novo_progresso is not None:
            item["progresso"] = int(novo_progresso)
        else:
            if novo_status == "concluida":
                item["progresso"] = 100
            elif novo_status == "em_andamento":
                item["progresso"] = 50
            elif novo_status == "aberta":
                item["progresso"] = 10
            elif novo_status == "atrasada":
                item["progresso"] = 30

        item["concluido"] = (novo_status == "concluida")
        return JSONResponse({"success": True, "item": item})

    return JSONResponse({"success": False, "message": "Demanda não encontrada"}, status_code=400)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)