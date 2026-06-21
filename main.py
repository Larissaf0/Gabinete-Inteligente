from http import HTTPStatus
from fastapi import FastAPI, Request, Form, HTTPException,status
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import Base, engine
from datetime import datetime
import database
from models import Secretaria
from schemas import Message, UserDB, UserList, UserPublic, UserSchema

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

#Página home de cada secretaria (dashboard será específico)
@app.get("/sec-home", response_class=HTMLResponse)
async def sec_home(request: Request):
    return templates.TemplateResponse(request,"sec_home.html")
          

#página padrão de cada reunião - 
@app.get("/nova-reuniao",response_class=HTMLResponse)
async def nova_reuniao(request: Request):

    data_atual = datetime.now().strftime("%d/%m/%Y")

    return templates.TemplateResponse(
        request=request,
        name="nova_reuniao.html",
        context={
            "data_atual": data_atual,
            "hora_atual": datetime.now().strftime("%H:%M")
        }
    )

# Página para criar nova reunião, com o nome da secretaria injetado dinamicamente
# @app.get("/nova-reuniao/{{secretaria_nome}}", response_class=HTMLResponse)
# async def nova_reuniao(request: Request, secretaria_nome: str):

#     data_atual = datetime.now().strftime("%d/%m/%Y")
    
#     # Mapeamento para deixar o nome com acentuação e espaços corretos na tela
#     nomes_formatados = {
#         "SEDUC": "Educação",
#         "Financas": "Finanças",
#         "Saude": "Saúde",
#         "ADM": "Administração",
#         "ServicosPublicos":"Serviços Públicos",
#         "SEDTEC": "Desenvolvimento Econômico, Ciência e Tecnologia",
#         "CulturaEsportes": "Cultura e Esportes",
#         "Obras": "Desenvolvimento Urbano e Obras",
#         "SEPLAMA": "Planejamento e Meio Ambiente",
#         "Rural":"Desenvolvimento Rural",
#         "Social": "Desenvolvimento Social",

#     }
    
#     # Busca o nome limpo no dicionário. Se não achar, usa o próprio texto digitado na URL
#     secretaria_nome = nomes_formatados.get(secretaria_nome, secretaria_nome)
    
#     # Injeta dinamicamente a variável 'secretaria' no contexto do template padrão
#     return templates.TemplateResponse(
#         request=request,
#         name="nova_reuniao.html",
#         context={"secretaria_nome": secretaria_nome,
#                  "data_atual": data_atual,
#                  "hora_atual": datetime.now().strftime("%H:%M")
#         }
#     )

#página de pauta livre
@app.get("/pauta-livre",response_class=HTMLResponse)
async def pauta_livre(request: Request):

    data_atual = datetime.now().strftime("%d/%m/%Y")

    return templates.TemplateResponse(
        request=request,
        name="pauta_livre.html",
        context={
            "data_atual": data_atual,
            "hora_atual": datetime.now().strftime("%H:%M")
        }
    )

#USERs - E-mail
@app.post("/users/", status_code=HTTPStatus.CREATED, response_model=UserPublic)
def create_user(user: UserSchema):
    user_with_id = UserDB(**user.model_dump(), id=len(database) + 1)
    database.append(user_with_id)
    return user_with_id

@app.get("/users/", response_model=UserList)
def read_users():
    return {'users': database}

@app.put("/users/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user: UserSchema):
    if user_id > len(database) or user_id < 1:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Usuário não encontrado"
            )
    user_with_id = UserDB(**user.model_dump(), id=user_id)
    database[user_id - 1] = user_with_id

    return user_with_id

@app.delete('/users/{user_id}', response_model=Message)
def delete_user(user_id: int):
    if user_id > len(database) or user_id < 1:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Usuário não encontrado"
            )
    del database[user_id - 1]
    return {"message": "Usuário deletado com sucesso"}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)