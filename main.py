from fastapi import FastAPI, Request, Form, HTTPException,status
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import Base, engine
from datetime import datetime
from models import Secretaria

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

@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    usuario = {"nome": "Admin"} # Exemplo de usuário
    return templates.TemplateResponse(request,"home.html", context={"usuario": usuario})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

# Página para criar nova reunião, com o nome da secretaria injetado dinamicamente
@app.get("/nova-reuniao/{secretaria_nome}", response_class=HTMLResponse)
async def pagina_nova_reuniao(request: Request, secretaria_nome: str):

    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    # Mapeamento para deixar o nome com acentuação e espaços corretos na tela
    nomes_formatados = {
        "Educacao": "Educação",
        "Saude": "Saúde",
        "Administracao": "Administração",
        "ServicosPublicos":"Serviços Públicos",
        "DesenvolvimentoEconomico": "Desenvolvimento Econômico, Ciência e Tecnologia",
    }
    
    # Busca o nome limpo no dicionário. Se não achar, usa o próprio texto digitado na URL
    secretaria_display = nomes_formatados.get(secretaria_nome, secretaria_nome)
    
    # Injeta dinamicamente a variável 'secretaria' no contexto do template padrão
    return templates.TemplateResponse(
        request=request,
        name="nova_reuniao.html",
        context={"secretaria": secretaria_display,
                 "data_atual": data_atual,
                 "hora_atual": datetime.now().strftime("%H:%M")
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)