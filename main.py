from fastapi import FastAPI, Request, Form, Depends, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from datetime import datetime
from zoneinfo import ZoneInfo
import pytz
from supabase_client import supabase
from starlette.middleware.sessions import SessionMiddleware
import os

from database import (
    participantes_db,
    reunioes_db,
    NOMES_SECRETARIAS,
    LOGOS_SECRETARIAS,
    obter_logo_secretaria
)
from models import StatusUpdateSchema

app = FastAPI(title="Gabinete Inteligente")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-me")
)
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
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": username.strip(),
            "password": password
        })

        if response.user:
            request.session["user_id"] = str(response.user.id)
            request.session["user_email"] = response.user.email

            return RedirectResponse(
                url="/home",
                status_code=303
            )

        return HTMLResponse(
            content="Usuário ou senha incorretos",
            status_code=401
        )

    except Exception as e:
        print("ERRO NO LOGIN:", e)

        return HTMLResponse(
            content="Usuário ou senha incorretos",
            status_code=401
        )

#Busca o perfil do usuário logado
def obter_perfil_usuario(user_id: str, email: str = ""):
    if not user_id:
        return None

    try:
        response = (
            supabase
            .table("perfis")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        perfil = response.data

        if not perfil:
            return {
                "user_id": user_id,
                "nome": "",
                "inicial": "",
                "email": email or "",
                "cargo": "",
                "secretaria": "home",
                "telefone": "",
                "notif_email": False,
                "notif_whatsapp": False,
                "lembretes_prazos": False,
            }

        perfil["email"] = email or ""

        nome = (perfil.get("nome") or "").strip()
        perfil["inicial"] = nome[:2].upper() if nome else ""

        return perfil

    except Exception as e:
        print("ERRO AO BUSCAR PERFIL:", e)
        return None
    
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
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    logo = obter_logo_secretaria(sec_id)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "usuario": usuario,
            "logo_secretaria": logo
        }
    )

@app.get("/configuracoes", response_class=HTMLResponse)
async def configuracoes_page(
    request: Request,
    msg: str = None,
    erro: str = None
):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    logo = obter_logo_secretaria("home")

    return templates.TemplateResponse(
        request=request,
        name="configuracoes.html",
        context={
            "usuario": usuario,
            "secretarias": NOMES_SECRETARIAS,
            "logo_secretaria": logo,
            "msg": msg,
            "erro": erro
        }
    )

@app.post("/configuracoes/perfil")
async def atualizar_perfil(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    cargo: str = Form(""),
    secretaria: str = Form("home"),
    telefone: str = Form("")
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    try:
        perfil = {
            "user_id": user_id,
            "nome": nome.strip(),
            "cargo": cargo.strip(),
            "secretaria": secretaria.strip(),
            "telefone": telefone.strip(),
        }

        (
            supabase
            .table("perfis")
            .upsert(perfil, on_conflict="user_id")
            .execute()
        )

        return RedirectResponse(
            url="/configuracoes?msg=perfil_atualizado",
            status_code=303
        )

    except Exception as e:
        print("ERRO AO ATUALIZAR PERFIL:", e)

        return RedirectResponse(
            url="/configuracoes?erro=perfil",
            status_code=303
        )

@app.post("/configuracoes/senha")
async def atualizar_senha(
    request: Request,
    senha_atual: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...)
):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email")

    if not user_id or not user_email:
        return RedirectResponse(url="/", status_code=303)

    if len(nova_senha) < 4:
        return RedirectResponse(
            url="/configuracoes?erro=senha_curta",
            status_code=303
        )

    if nova_senha != confirmar_senha:
        return RedirectResponse(
            url="/configuracoes?erro=senha_divergente",
            status_code=303
        )

    try:
        # Confirma se a senha atual realmente pertence ao usuário logado
        auth_response = supabase.auth.sign_in_with_password({
            "email": user_email,
            "password": senha_atual
        })

        if not auth_response.user:
            return RedirectResponse(
                url="/configuracoes?erro=senha_atual_incorreta",
                status_code=303
            )

        # Atualiza a senha no Supabase Auth
        supabase.auth.update_user({
            "password": nova_senha
        })

        return RedirectResponse(
            url="/configuracoes?msg=senha_atualizada",
            status_code=303
        )

    except Exception as e:
        print("ERRO AO ALTERAR SENHA:", e)

        return RedirectResponse(
            url="/configuracoes?erro=senha_atual_incorreta",
            status_code=303
        )

@app.post("/configuracoes/preferencias")
async def atualizar_preferencias(
    request: Request,
    notif_email: bool = Form(False),
    notif_whatsapp: bool = Form(False),
    lembretes_prazos: bool = Form(False)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    try:
        (
            supabase
            .table("perfis")
            .update({
                "notif_email": notif_email,
                "notif_whatsapp": notif_whatsapp,
                "lembretes_prazos": lembretes_prazos
            })
            .eq("user_id", user_id)
            .execute()
        )

        return RedirectResponse(
            url="/configuracoes?msg=preferencias_atualizadas",
            status_code=303
        )

    except Exception as e:
        print("ERRO AO ATUALIZAR PREFERÊNCIAS:", e)

        return RedirectResponse(
            url="/configuracoes?erro=preferencias",
            status_code=303
        )

@app.get("/reunioes", response_class=HTMLResponse)
async def reunioes_geral(request: Request):
    return RedirectResponse(url="/secretaria/home/reunioes", status_code=303)

@app.get("/pauta-livre", response_class=HTMLResponse)
async def pauta_livre_page(request: Request):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    data_atual, hora_atual = get_formatted_date_and_hour()

    return templates.TemplateResponse(
        request=request,
        name="pauta_livre.html",
        context={
            "data_atual": data_atual,
            "hora_atual": hora_atual,
            "participantes_db": obter_participantes_supabase(),
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria("pauta-livre")
        }
    )


def _salvar_participantes_reuniao(reuniao_id: int, nomes: str):
    if not nomes:
        return
    existentes = obter_participantes_supabase()
    by_name = {p["nome"].strip().lower(): p for p in existentes if p.get("nome")}
    for nome in [x.strip() for x in nomes.split(",") if x.strip()]:
        p = by_name.get(nome.lower())
        if not p or not p.get("id"):
            continue
        try:
            supabase.table("reuniao_participantes").upsert({"reuniao_id": reuniao_id, "participante_id": p["id"]}).execute()
        except Exception as exc:
            print(f"Aviso vínculo participante: {exc}")


def _participantes_da_reuniao(reuniao_id: int):
    try:
        links = supabase.table("reuniao_participantes").select("participante_id").eq("reuniao_id", reuniao_id).execute().data or []
        ids = [x.get("participante_id") for x in links if x.get("participante_id") is not None]
        if not ids:
            return []
        todos = obter_participantes_supabase()
        return [p for p in todos if p.get("id") in ids]
    except Exception:
        return []


def _get_reuniao_supabase(meeting_id: int):
    try:
        resp = supabase.table("reunioes").select("*").eq("id", meeting_id).single().execute()
        r = resp.data or None
        if r:
            r["data"] = _format_date_br(r.get("data"))
            if r.get("hora"): r["hora"] = str(r["hora"])[:5]
            r["participantes"] = _participantes_da_reuniao(meeting_id)
        return r
    except Exception:
        return None


async def _criar_reuniao_supabase(sec_id, titulo, assunto, local, participantes, anotacoes, data, hora):
    data_atual, hora_atual = get_formatted_date_and_hour()
    payload = {
        "titulo": titulo.strip(), "assunto": assunto,
        "data": _format_date_iso(data or data_atual), "hora": (hora or hora_atual)[:5],
        "secretaria_id": sec_id, "status": "Agendada", "local": local.strip(), "anotacoes": anotacoes
    }
    resp = supabase.table("reunioes").insert(payload).execute()
    if not resp.data:
        return None
    rid = resp.data[0]["id"]
    _salvar_participantes_reuniao(rid, participantes)
    return rid


@app.post("/salvar-reuniao")
async def salvar_pauta_livre(titulo: str = Form(...), assunto: str = Form("Pauta Geral"),
                             local: str = Form("Gabinete do Prefeito"), participantes: str = Form(""),
                             anotacoes: str = Form(""), data: str = Form(None), hora: str = Form(None)):
    try:
        rid = await _criar_reuniao_supabase("home", titulo, assunto, local, participantes, anotacoes, data, hora)
    except Exception as exc:
        return HTMLResponse(f"Erro ao salvar reunião no Supabase: {exc}", status_code=500)
    if not rid: return HTMLResponse("Não foi possível criar a reunião.", status_code=500)
    return RedirectResponse(url=f"/secretaria/home/reuniao/{rid}", status_code=303)


@app.get("/secretaria/{sec_id}/nova-reuniao", response_class=HTMLResponse)
async def nova_reuniao_page(request: Request, sec_id: str):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    data_atual, hora_atual = get_formatted_date_and_hour()

    return templates.TemplateResponse(
        request=request,
        name="nova_reuniao.html",
        context={
            "sec_id": sec_id,
            "secretaria_nome": NOMES_SECRETARIAS.get(sec_id, sec_id),
            "data_atual": data_atual,
            "hora_atual": hora_atual,
            "participantes_db": obter_participantes_supabase(),
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria(sec_id)
        }
    )


@app.post("/secretaria/{sec_id}/salvar-reuniao")
async def salvar_reuniao_secretaria(sec_id: str, titulo: str = Form(...), local: str = Form("Não especificado"),
                                     participantes: str = Form(""), anotacoes: str = Form(""),
                                     data: str = Form(None), hora: str = Form(None)):
    try:
        rid = await _criar_reuniao_supabase(sec_id, titulo, f"Pauta de {NOMES_SECRETARIAS.get(sec_id,sec_id)}",
                                            local, participantes, anotacoes, data, hora)
    except Exception as exc:
        return HTMLResponse(f"Erro ao salvar reunião no Supabase: {exc}", status_code=500)
    if not rid: return HTMLResponse("Não foi possível criar a reunião.", status_code=500)
    return RedirectResponse(url=f"/secretaria/{sec_id}/reuniao/{rid}", status_code=303)


@app.get(
    "/secretaria/{sec_id}/reuniao/{meeting_id}/editar",
    response_class=HTMLResponse
)
async def editar_reuniao_page(
    request: Request,
    sec_id: str,
    meeting_id: int
):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    reuniao = _get_reuniao_supabase(meeting_id)

    if not reuniao:
        return RedirectResponse(
            url=f"/secretaria/{sec_id}/reunioes",
            status_code=303
        )

    sec_real = reuniao.get("secretaria_id", sec_id)

    participantes_str = ", ".join(
        p.get("nome", "")
        for p in reuniao.get("participantes", [])
    )

    return templates.TemplateResponse(
        request=request,
        name="editar_reuniao.html",
        context={
            "sec_id": sec_real,
            "secretaria_nome": NOMES_SECRETARIAS.get(sec_real, sec_real),
            "reuniao": reuniao,
            "data_input": _format_date_iso(reuniao.get("data")) or "",
            "hora_input": reuniao.get("hora", "")[:5],
            "participantes_str": participantes_str,
            "participantes_db": obter_participantes_supabase(),
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria(sec_real)
        }
    )


@app.get("/reuniao/{meeting_id}/editar")
async def editar_reuniao_atalho(meeting_id: int):
    r = _get_reuniao_supabase(meeting_id)
    return RedirectResponse(url=f"/secretaria/{r.get('secretaria_id','home') if r else 'home'}/reuniao/{meeting_id}/editar", status_code=303)


@app.post("/secretaria/{sec_id}/reuniao/{meeting_id}/salvar-edicao")
async def salvar_edicao_reuniao(sec_id: str, meeting_id: int, titulo: str = Form(...), assunto: str = Form(None),
                                 local: str = Form(None), participantes: str = Form(""), anotacoes: str = Form(""),
                                 data: str = Form(None), hora: str = Form(None)):
    update = {"titulo": titulo.strip(), "anotacoes": anotacoes}
    if assunto is not None: update["assunto"] = assunto
    if local is not None: update["local"] = local.strip()
    if data: update["data"] = _format_date_iso(data)
    if hora: update["hora"] = hora[:5]
    try:
        supabase.table("reunioes").update(update).eq("id", meeting_id).execute()
        _salvar_participantes_reuniao(meeting_id, participantes)
    except Exception as exc:
        return HTMLResponse(f"Erro ao atualizar reunião: {exc}", status_code=500)
    r = _get_reuniao_supabase(meeting_id)
    return RedirectResponse(url=f"/secretaria/{r.get('secretaria_id',sec_id) if r else sec_id}/reuniao/{meeting_id}", status_code=303)


@app.api_route("/reuniao/{meeting_id}/excluir", methods=["GET", "POST"])
@app.api_route("/reuniao/{meeting_id}/excluir/", methods=["GET", "POST"])
async def excluir_reuniao_direta(meeting_id: int):
    r = _get_reuniao_supabase(meeting_id); sec = r.get("secretaria_id", "home") if r else "home"
    try: supabase.table("reunioes").delete().eq("id", meeting_id).execute()
    except Exception as exc: return HTMLResponse(f"Erro ao excluir reunião: {exc}", status_code=500)
    return RedirectResponse(url=f"/secretaria/{sec}/reunioes", status_code=303)


@app.api_route("/secretaria/{sec_id}/reuniao/{meeting_id}/excluir", methods=["GET", "POST"])
@app.api_route("/secretaria/{sec_id}/reuniao/{meeting_id}/excluir/", methods=["GET", "POST"])
async def excluir_reuniao_secretaria(sec_id: str, meeting_id: int):
    return await excluir_reuniao_direta(meeting_id)


@app.get("/secretaria/{sec_id}/reunioes", response_class=HTMLResponse)
async def listar_reunioes(
    request: Request,
    sec_id: str,
    pagina: int = 1
):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    filtradas = obter_reunioes_supabase(sec_id)

    return templates.TemplateResponse(
        request=request,
        name="reunioes.html",
        context={
            "usuario": usuario,
            "sec_id": sec_id,
            "reunioes": filtradas,
            "pagina_atual": pagina,
            "total_paginas": 1,
            "de_registro": 1 if filtradas else 0,
            "ate_registro": len(filtradas),
            "total_registros": len(filtradas),
            "logo_secretaria": obter_logo_secretaria(sec_id)
        }
    )


@app.get("/secretaria/{sec_id}/reuniao/{meeting_id}", response_class=HTMLResponse)
async def ver_reuniao(
    request: Request,
    sec_id: str,
    meeting_id: int
):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    reuniao = _get_reuniao_supabase(meeting_id)

    if not reuniao:
        return RedirectResponse(
            url=f"/secretaria/{sec_id}/reunioes",
            status_code=303
        )

    sec_real = reuniao.get("secretaria_id", sec_id)

    demandas = [
        d
        for d in await extract_all_demandas_supabase("home")
        if d.get("reuniao_id") == meeting_id
    ]

    return templates.TemplateResponse(
        request=request,
        name="ver_reuniao.html",
        context={
            "sec_id": sec_real,
            "secretaria_nome": NOMES_SECRETARIAS.get(sec_real, sec_real),
            "reuniao": reuniao,
            "demandas_reuniao": demandas,
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria(sec_real)
        }
    )


@app.get("/reuniao/{meeting_id}")
async def ver_reuniao_atalho(meeting_id: int):
    r = _get_reuniao_supabase(meeting_id); sec = r.get("secretaria_id", "home") if r else "home"
    return RedirectResponse(url=f"/secretaria/{sec}/reuniao/{meeting_id}", status_code=303)


SEC_ID_ALIASES = {
    "ADM": "SADM", "FIN": "SFIN", "Saude": "SSAU", "ServicosPublicos": "SSP",
    "CulturaEsportes": "SECULTE", "Obras": "SDUO", "SEPLAMA": "SPMA",
    "Rural": "SDR", "Social": "SDS",
}

def canonical_sec_id(sec_id: str) -> str:
    aliases = {
    # Administração
    "ADM": "SADM",
    "SADM": "SADM",

    # Finanças
    "FIN": "SFIN",
    "SFIN": "SFIN",

    # Saúde
    "Saude": "SSAU",
    "SSAU": "SSAU",

    # Serviços Públicos
    "ServicosPublicos": "SSP",
    "SSP": "SSP",

    # Desenvolvimento Econômico
    "SEDTEC": "SDTEC",
    "SDTEC": "SDTEC",

    # Cultura e Esportes
    "CulturaEsportes": "SECULTE",
    "SECULTE": "SECULTE",

    # Obras
    "Obras": "SDUO",
    "SDUO": "SDUO",

    # Planejamento
    "SEPLAMA": "SPMA",
    "SPMA": "SPMA",

    # Desenvolvimento Rural
    "Rural": "SDR",
    "SDR": "SDR",

    # Desenvolvimento Social
    "Social": "SDS",
    "SDS": "SDS",

    # Educação
    "SEDUC": "SEDUC",

    # Gerais
    "home": "home",
    "pauta-livre": "pauta-livre",
    }
    return SEC_ID_ALIASES.get(sec_id, sec_id)

def _parse_any_date(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).replace(tzinfo=TZ_RECIFE)
        except ValueError:
            pass
    return None


def _format_date_br(value):
    dt = _parse_any_date(value)
    return dt.strftime("%d/%m/%Y") if dt else (str(value) if value else "")


def _format_date_iso(value):
    dt = _parse_any_date(value)
    return dt.strftime("%Y-%m-%d") if dt else None


def _safe_supabase_rows(table, select="*"):
    try:
        response = supabase.table(table).select(select).execute()
        return response.data or []
    except Exception as exc:
        print(f"Aviso Supabase ({table}): {exc}")
        return []


def obter_participantes_supabase():
    rows = _safe_supabase_rows("participantes")
    return [{
        "id": r.get("id"),
        "nome": r.get("nome", ""),
        "cargo": r.get("cargo", "Participante"),
        "secretaria": r.get("secretaria_id") or r.get("secretaria") or "home",
    } for r in rows]


def obter_reunioes_supabase(sec_id="home"):
    sec_id = canonical_sec_id(sec_id)
    rows = _safe_supabase_rows("reunioes")
    if sec_id != "home":
        rows = [r for r in rows if r.get("secretaria_id") == sec_id]
    for r in rows:
        r["data"] = _format_date_br(r.get("data"))
        if r.get("hora"):
            r["hora"] = str(r["hora"])[:5]
    rows.sort(key=lambda r: parse_data_hora(r.get("data"), r.get("hora")), reverse=True)
    return rows


async def extract_all_demandas_supabase(sec_id="home"):
    sec_id = canonical_sec_id(sec_id)
    encaminhamentos = _safe_supabase_rows("encaminhamentos")
    reunioes = {r.get("id"): r for r in _safe_supabase_rows("reunioes")}
    hoje = datetime.now(TZ_RECIFE).replace(hour=0, minute=0, second=0, microsecond=0)
    demandas = []
    indices_por_reuniao = {}

    for item in encaminhamentos:
        reuniao = reunioes.get(item.get("reuniao_id"), {})
        sec_key = reuniao.get("secretaria_id", "home")
        if sec_id != "home" and sec_key != sec_id:
            continue

        idx = indices_por_reuniao.get(item.get("reuniao_id"), 0)
        indices_por_reuniao[item.get("reuniao_id")] = idx + 1
        status = item.get("status") or "aberta"
        dt_prazo = _parse_any_date(item.get("prazo"))
        vence_hoje = False
        vence_semana = False
        if dt_prazo:
            diff = (dt_prazo - hoje).days
            vence_hoje = diff == 0
            vence_semana = 0 <= diff <= 7
            if diff < 0 and status != "concluida":
                status = "atrasada"

        progresso = int(item.get("progresso") or 0)
        if status == "concluida": progresso = 100
        elif status == "em_andamento" and progresso < 50: progresso = 50
        elif status == "aberta" and progresso <= 0: progresso = 10
        elif status == "atrasada" and progresso <= 0: progresso = 30

        demandas.append({
            "id": item.get("id"),
            "reuniao_id": item.get("reuniao_id"),
            "reuniao_titulo": reuniao.get("titulo") or "Demanda Geral",
            "secretaria_id": sec_key,
            "secretaria_nome": NOMES_SECRETARIAS.get(sec_key, sec_key),
            "encaminhamento_index": idx,
            "tarefa": item.get("tarefa") or "Demanda sem título",
            "responsavel": item.get("responsavel") or "Gabinete",
            "prazo": _format_date_br(item.get("prazo")) or "A definir",
            "prioridade": item.get("prioridade") or "Média",
            "status": status,
            "progresso": progresso,
            "concluido": bool(item.get("concluido", False)),
            "vence_hoje": vence_hoje,
            "vence_semana": vence_semana,
            # Compatibilidade visual com os componentes do Studio sem alterar o schema estável.
            "emenda_deputado": "",
            "local_definicao": "",
            "pendencias": "",
            "valor": "",
            "custo": "",
            "historico": [],
        })
    return demandas


def _build_kanban(demandas):
    colunas = {
        "aberta": [d for d in demandas if d["status"] == "aberta"],
        "em_andamento": [d for d in demandas if d["status"] == "em_andamento"],
        "concluida": [d for d in demandas if d["status"] == "concluida"],
        "atrasada": [d for d in demandas if d["status"] == "atrasada"],
    }
    kpis = {
        "total": len(demandas),
        "abertas": len(colunas["aberta"]),
        "em_andamento": len(colunas["em_andamento"]),
        "concluidas": len(colunas["concluida"]),
        "atrasadas": len(colunas["atrasada"]),
        "vencem_hoje": sum(1 for d in demandas if d["vence_hoje"]),
        "vencem_semana": sum(1 for d in demandas if d["vence_semana"]),
    }
    return colunas, kpis


@app.get("/secretaria/home", response_class=HTMLResponse)
@app.get("/secretaria/home/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/dashboard/", response_class=HTMLResponse)
async def gabinete_dashboard(request: Request):

    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    demandas = await extract_all_demandas_supabase("home")
    colunas, kpis = _build_kanban(demandas)
    reunioes = obter_reunioes_supabase("home")

    secretarias_oficiais = {
        "SADM": "Administração",
        "SDR": "Desenvolvimento Rural",
        "SDS": "Desenvolvimento Social",
        "SDTEC": "Desenvolvimento Econômico, Ciência e Tecnologia",
        "SDUO": "Desenvolvimento Urbano e Obras",
        "SECULTE": "Cultura e Esportes",
        "SEDUC": "Educação",
        "SFIN": "Finanças",
        "SPMA": "Planejamento e Meio Ambiente",
        "SSAU": "Saúde",
        "SSP": "Serviços Públicos",
    }

    secretarias_info = []

    for sid, nome in secretarias_oficiais.items():

        sd = [
            d for d in demandas
            if canonical_sec_id(d.get("secretaria_id")) == sid
        ]

        sr = [
            r for r in reunioes
            if canonical_sec_id(r.get("secretaria_id")) == sid
        ]

        secretarias_info.append({
            "id": sid,
            "nome": nome,
            "icone": "fa-solid fa-building-columns",
            "cor": "primary",
            "demandas_total": len(sd),
            "demandas_abertas": sum(
                1 for d in sd
                if d["status"] in ("aberta", "em_andamento")
            ),
            "demandas_atrasadas": sum(
                1 for d in sd
                if d["status"] == "atrasada"
            ),
            "demandas_concluidas": sum(
                1 for d in sd
                if d["status"] == "concluida"
            ),
            "reunioes_qtd": len(sr),
        })

    notificacoes = _montar_notificacoes(
        demandas,
        reunioes
    )[:12]

    reunioes_fmt = [
        {
            **r,
            "data_hora": f"{r.get('data', '')} às {r.get('hora', '')}",
            "secretaria_nome": NOMES_SECRETARIAS.get(
                r.get("secretaria_id"),
                "Gabinete"
            ),
            "encaminhamentos_qtd": sum(
                1 for d in demandas
                if d.get("reuniao_id") == r.get("id")
            ),
            "participantes_qtd": 0,
        }
        for r in reunioes
    ]

    return templates.TemplateResponse(
        request=request,
        name="gabinete_dashboard.html",
        context={
            "sec_id": "home",
            "secretaria_nome": "Gabinete",
            "kpis": kpis,
            "colunas": colunas,
            "demandas": demandas,
            "notificacoes": notificacoes,
            "reunioes_gerais": reunioes_fmt,
            "secretarias_stats": secretarias_info,
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria("home")
        }
    )


@app.get("/secretaria/{sec_id}", response_class=HTMLResponse)
@app.get("/secretaria/{sec_id}/", response_class=HTMLResponse)
async def secretaria_dashboard(request: Request, sec_id: str):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    original_sec_id = sec_id
    sec_id = canonical_sec_id(sec_id)

    if sec_id == "home":
        return await gabinete_dashboard(request)

    demandas = await extract_all_demandas_supabase(sec_id)

    _, kpis = _build_kanban(demandas)

    reunioes = obter_reunioes_supabase(sec_id)

    prazos = []

    hoje = datetime.now(TZ_RECIFE).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    for d in demandas:
        if d["status"] == "concluida":
            continue

        dt = _parse_any_date(d.get("prazo"))

        if dt:
            prazos.append({
                "titulo": d["tarefa"],
                "data_limite": d["prazo"],
                "dias_restantes": (dt - hoje).days
            })

    prazos.sort(
        key=lambda p: p["dias_restantes"]
    )

    reunioes_fmt = [
        {
            **r,
            "data_hora": f"{r.get('data', '')} às {r.get('hora', '')}",
            "encaminhamentos_qtd": sum(
                1 for d in demandas
                if d.get("reuniao_id") == r.get("id")
            )
        }
        for r in reunioes
    ]

    return templates.TemplateResponse(
        request=request,
        name="sec_home.html",
        context={
            "sec_id": sec_id,
            "secretaria_nome": NOMES_SECRETARIAS.get(sec_id, sec_id),
            "notificacoes_qtd": (
                kpis["atrasadas"] + kpis["vencem_hoje"]
            ),
            "kpis": kpis,
            "prazos": prazos[:5],
            "reunioes": reunioes_fmt,
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria(sec_id)
        }
    )

@app.get("/secretaria/{sec_id}/kanban", response_class=HTMLResponse)
async def kanban_board(
    request: Request,
    sec_id: str,
    status: str = "todos",
    status_filtro: str = "todos"
):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    sec_id = canonical_sec_id(sec_id)

    filtro = status if status != "todos" else status_filtro

    demandas = await extract_all_demandas_supabase(sec_id)

    colunas, kpis = _build_kanban(demandas)

    return templates.TemplateResponse(
        request=request,
        name="kanban.html",
        context={
            "sec_id": sec_id,
            "secretaria_nome": NOMES_SECRETARIAS.get(sec_id, sec_id),
            "secretarias": NOMES_SECRETARIAS,
            "todas_reunioes": obter_reunioes_supabase(sec_id),
            "participantes_db": obter_participantes_supabase(),
            "usuario": usuario,
            "logo_secretaria": obter_logo_secretaria(sec_id),
            "demandas": demandas,
            "colunas": colunas,
            "kpis": kpis,
            "status_filtro": filtro
        }
    )


@app.get("/kanban", response_class=HTMLResponse)
async def kanban_geral(request: Request, status: str = "todos", status_filtro: str = "todos"):
    user_id = request.session.get("user_id")
    user_email = request.session.get("user_email", "")

    if not user_id:
        return RedirectResponse(url="/", status_code=303)

    usuario = obter_perfil_usuario(
        user_id=user_id,
        email=user_email
    )

    filtro = status if status != "todos" else status_filtro
    demandas = await extract_all_demandas_supabase("home")
    colunas, kpis = _build_kanban(demandas)
    return templates.TemplateResponse(request=request, name="kanban.html", context={
        "sec_id": "home", "secretaria_nome": "Todas as Secretarias", "secretarias": NOMES_SECRETARIAS,
        "todas_reunioes": obter_reunioes_supabase("home"), "participantes_db": obter_participantes_supabase(),
        "usuario": usuario, "logo_secretaria": obter_logo_secretaria("home"),
        "demandas": demandas, "colunas": colunas, "kpis": kpis, "status_filtro": filtro
    })


def _montar_notificacoes(demandas, reunioes):
    hoje = datetime.now(TZ_RECIFE).replace(hour=0, minute=0, second=0, microsecond=0)
    items = []
    for d in demandas:
        dt = _parse_any_date(d.get("prazo"))
        if not dt or d["status"] == "concluida": continue
        diff = (dt-hoje).days
        if diff < 0:
            tipo, cor, texto, titulo = "atrasada", "danger", "Atrasada", "Demanda Atrasada"
        elif diff == 0:
            tipo, cor, texto, titulo = "hoje", "warning", "Hoje", "Vence Hoje"
        elif diff <= 7:
            tipo, cor, texto, titulo = "semana", "info", f"{diff} dias", "Vence na Semana"
        else:
            continue
        items.append({"id": f"{tipo}_{d['id']}", "tipo": tipo, "titulo": titulo, "mensagem": d["tarefa"],
                      "detalhes": f"{d['secretaria_nome']} • Responsável: {d['responsavel']}", "prazo": d["prazo"],
                      "link": f"/secretaria/{d['secretaria_id']}/kanban?status={d['status'] if diff<0 else ('vencem_hoje' if diff==0 else 'vencem_semana')}",
                      "badge_cor": cor, "badge_texto": texto,
                      "icone": "fa-solid fa-triangle-exclamation" if diff<0 else "fa-regular fa-calendar"})
    return items


@app.get("/api/notificacoes")
async def api_notificacoes():
    demandas = await extract_all_demandas_supabase("home")
    reunioes = obter_reunioes_supabase("home")
    items = _montar_notificacoes(demandas, reunioes)
    return JSONResponse({"success": True, "total": len(items), "items": items})


@app.post("/secretaria/{sec_id}/demanda/adicionar")
async def adicionar_demanda(
    sec_id: str,
    titulo_acao: str = Form(...),
    prazo_execucao: str = Form(""),
    responsavel_execucao: str = Form("Gabinete"),
    prioridade: str = Form("Média"),
    status: str = Form("aberta"),
    reuniao_id: str = Form(""),
    secretaria_id: str = Form(""),
    emenda_deputado: str = Form(""), local_definicao: str = Form(""),
    pendencias: str = Form(""), valor: str = Form(""), custo: str = Form("")
):
    target_sec = canonical_sec_id(secretaria_id or sec_id)
    rid = int(reuniao_id) if reuniao_id and str(reuniao_id).isdigit() else None
    if rid is None:
        existentes = obter_reunioes_supabase(target_sec)
        if existentes:
            rid = existentes[0]["id"]
        else:
            data_atual, hora_atual = get_formatted_date_and_hour()
            payload = {"titulo": f"Demandas de {NOMES_SECRETARIAS.get(target_sec,target_sec)}",
                       "assunto": "Acompanhamento de Ações e Projetos", "data": _format_date_iso(data_atual),
                       "hora": hora_atual, "secretaria_id": target_sec, "status": "Agendada",
                       "local": local_definicao or "Gabinete", "anotacoes": "Registro de demandas setoriais."}
            try:
                ins = supabase.table("reunioes").insert(payload).execute()
                rid = ins.data[0]["id"] if ins.data else None
            except Exception as exc:
                return HTMLResponse(f"Não foi possível criar reunião de vínculo: {exc}", status_code=500)
    if rid is None:
        return HTMLResponse("Não foi possível definir reunião para a demanda.", status_code=400)
    prog = 100 if status == "concluida" else 50 if status == "em_andamento" else 30 if status == "atrasada" else 10
    payload = {"reuniao_id": rid, "tarefa": titulo_acao.strip(), "responsavel": responsavel_execucao.strip() or "Gabinete",
               "prazo": _format_date_iso(prazo_execucao), "prioridade": prioridade, "status": status,
               "progresso": prog, "concluido": status == "concluida"}
    try:
        supabase.table("encaminhamentos").insert(payload).execute()
    except Exception as exc:
        return HTMLResponse(f"Erro ao salvar demanda no Supabase: {exc}", status_code=500)
    return RedirectResponse(url=f"/secretaria/{target_sec}/kanban", status_code=303)


@app.post("/api/demanda/status")
async def atualizar_status_demanda(body: StatusUpdateSchema):
    prog = body.novo_progresso
    if prog is None:
        prog = 100 if body.novo_status == "concluida" else 50 if body.novo_status == "em_andamento" else 30 if body.novo_status == "atrasada" else 10
    try:
        resp = supabase.table("encaminhamentos").update({"status": body.novo_status, "progresso": prog,
                                                         "concluido": body.novo_status == "concluida"}).eq("id", body.encaminhamento_id).execute()
    except Exception as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=500)
    if not resp.data:
        return JSONResponse({"success": False, "message": "Demanda não encontrada"}, status_code=404)
    return JSONResponse({"success": True, "item": resp.data[0], "historico": []})


@app.post("/api/demanda/atualizar")
async def atualizar_demanda(request: Request):
    body = await request.json()
    eid = body.get("encaminhamento_id")
    if not eid:
        # O Studio envia índice; resolvemos pelo id da reunião + posição ordenada.
        rid = int(body.get("reuniao_id") or 0)
        items = [d for d in await extract_all_demandas_supabase("home") if int(d.get("reuniao_id") or 0) == rid]
        try:
            idx = int(body.get("encaminhamento_index") or 0)
            eid = items[idx]["id"]
        except (ValueError, IndexError):
            eid = None
    if not eid:
        return JSONResponse({"success": False, "message": "Demanda não encontrada"}, status_code=404)
    update = {}
    if body.get("novo_status"):
        st = body["novo_status"]; update["status"] = st; update["concluido"] = st == "concluida"
        update["progresso"] = 100 if st == "concluida" else 50 if st == "em_andamento" else 30 if st == "atrasada" else 10
    if body.get("prazo"):
        update["prazo"] = _format_date_iso(body["prazo"])
    if body.get("responsavel"):
        update["responsavel"] = str(body["responsavel"]).strip()
    try:
        resp = supabase.table("encaminhamentos").update(update).eq("id", eid).execute() if update else None
    except Exception as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=500)
    item = (resp.data[0] if resp and resp.data else {"id": eid, **update})
    return JSONResponse({"success": True, "item": item, "historico": []})


@app.post("/api/analise-ia")
async def analise_ia(request: Request):
    body = await request.json()
    titulo = body.get("titulo") or "Pauta do Gabinete"
    anotacoes = (body.get("anotacoes") or body.get("pauta") or "").strip()
    secretaria = body.get("secretaria_nome") or "Gabinete Municipal"
    resumo = anotacoes[:500] + ("..." if len(anotacoes) > 500 else "") if anotacoes else "Sem anotações detalhadas."
    analise = (f"### Análise Executiva: {titulo}\n**Secretaria:** {secretaria}\n\n"
               f"#### Resumo\n{resumo}\n\n#### Ações sugeridas\n"
               "- Formalizar as deliberações e responsáveis.\n- Definir prazos e acompanhar no Kanban.\n"
               "- Validar dependências administrativas e orçamentárias.\n\n#### Pontos de atenção\n"
               "- Revisar prazos, responsáveis e pendências antes do próximo acompanhamento.")
    return JSONResponse({"success": True, "analise": analise})


@app.get("/teste-encaminhamentos")
async def teste_encaminhamentos():
    rows = _safe_supabase_rows("encaminhamentos")
    return {"quantidade": len(rows), "encaminhamentos": rows}


@app.get("/teste-supabase")
async def teste_supabase():
    rows = _safe_supabase_rows("reunioes")
    return {"quantidade": len(rows), "reunioes": rows}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
