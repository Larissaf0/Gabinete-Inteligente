from http import HTTPStatus
from fastapi import FastAPI, Request, Form, HTTPException,status
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import Base, engine
from datetime import datetime
import database
import models
#from schemas import Message, UserDB, UserList, UserPublic, UserSchema

Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="templates")
RECAPTCHA_SECRET_KEY = "6LfImgQtAAAAALk3enMyZUDRMqRTH3LRD1bO5K-e"

#@app.post("/login", response_class=HTMLResponse)
#async def tela_login(request: Request):
    #return templates.TemplateResponse(
      #  request=request,
     #   name="home.html"
    #)

#landing page, é a tela principal do site, onde faz o login
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

    # 3. Analisar a resposta do Google
    if not resultado_google.get("success"):
        # Se o Google disser que o token é falso ou expirou
        raise HTTPException(status_code=400, detail="Falha na verificação do reCAPTCHA. Tente novamente.")

    # 4. Se passou no captcha, continua com a validação normal de usuário e senha
    if username == "admin" and password == "1234":
        return RedirectResponse(url="/home",status_code=status.HTTP_303_SEE_OTHER)
    
    raise HTTPException(status_code=401, detail="Usuário ou senha incorretos.")

#Tela de Solicitar Acesso
@app.get("/solicitar-acesso", response_class=HTMLResponse)
async def tela_solicitar_acessp(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="solicitar_acesso.html"
    )

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

#tela HOME, é a página inicial após o login. Com painel lateral e escolha de secretaria.
@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    usuario = {"nome": "admin"} # Exemplo de usuário
    return templates.TemplateResponse(request,"home.html", context={"usuario": usuario})

# landing page, é a tela principal do site, onde faz o login
# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#    return templates.TemplateResponse(request, "index.html")

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
}

# Rota para a página interna da secretaria (Dashboard específico)
@app.get("/secretaria/{sec_id}", response_class=HTMLResponse)
async def sec_home(request: Request, sec_id: str):
    # Busca o nome limpo formatado, se não achar usa o próprio ID digitado
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    
    return templates.TemplateResponse(
        request=request, 
        name="sec_home.html", 
        context={"sec_id": sec_id, "sec_nome": secretaria_nome}
    )

# 1. Rota para renderizar o formulário da NOVA REUNIÃO já com os dados da secretaria injetados
@app.get("/secretaria/{sec_id}/nova-reuniao", response_class=HTMLResponse)
async def exibir_formulario_reuniao(request: Request, sec_id: str):
    secretaria_nome = NOMES_SECRETARIAS.get(sec_id, sec_id)
    data_atual = datetime.now().strftime("%d/%m/%Y")
    hora_atual = datetime.now().strftime("%H:%M")
    
    return templates.TemplateResponse(
        request=request, 
        name="nova_reuniao.html", 
        context={
            "sec_id": sec_id, 
            "secretaria_nome": secretaria_nome,
            "data_atual": data_atual,
            "hora_atual": hora_atual
        }
    )

# 2. Rota POST que recebe os dados do formulário e vincula à secretaria no Banco de Dados
@app.post("/secretaria/{sec_id}/salvar-reuniao")
async def salvar_reuniao(
    sec_id: str, 
    titulo: str = Form(...), 
    data: str = Form(None),
    hora: str = Form(None)
):
    # TODO: Aqui você usa o seu 'models' importado para salvar no banco
    # exemplo:
    # db_reuniao = models.Reuniao(titulo=titulo, data=data, hora=hora, secretaria=sec_id)
    # database.session.add(db_reuniao)
    # database.session.commit()
    
    print(f"Gravando Reunião no BD -> Título: {titulo} | Secretaria vinculada: {sec_id}")
    
    # Redireciona o usuário de volta para a dashboard daquela secretaria específica
    return RedirectResponse(url=f"/secretaria/{sec_id}", status_code=status.HTTP_303_SEE_OTHER)

# Página de pauta livre (Independente de secretaria)
@app.get("/pauta-livre", response_class=HTMLResponse)
async def pauta_livre(request: Request):
    data_atual = datetime.now().strftime("%d/%m/%Y")
    hora_atual = datetime.now().strftime("%H:%M")
    return templates.TemplateResponse(
        request=request,
        name="pauta_livre.html",
        context={"data_atual": data_atual, "hora_atual": hora_atual}
    )


#USERs - E-mail -  COMENTADO PARA VER SE MUDAVA ALGUMA COISA
# @app.post("/users/", status_code=HTTPStatus.CREATED, response_model=UserPublic)
# def create_user(user: UserSchema):
#     user_with_id = UserDB(**user.model_dump(), id=len(database) + 1)
#     database.append(user_with_id)
#     return user_with_id

# @app.get("/users/", response_model=UserList)
# def read_users():
#     return {'users': database}

# @app.put("/users/{user_id}", response_model=UserPublic)
# def update_user(user_id: int, user: UserSchema):
#     if user_id > len(database) or user_id < 1:
#         raise HTTPException(
#             status_code=HTTPStatus.NOT_FOUND, detail="Usuário não encontrado"
#             )
#     user_with_id = UserDB(**user.model_dump(), id=user_id)
#     database[user_id - 1] = user_with_id

#     return user_with_id

# @app.delete('/users/{user_id}', response_model=Message)
# def delete_user(user_id: int):
#     if user_id > len(database) or user_id < 1:
#         raise HTTPException(
#             status_code=HTTPStatus.NOT_FOUND, detail="Usuário não encontrado"
#             )
#     del database[user_id - 1]
#     return {"message": "Usuário deletado com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)