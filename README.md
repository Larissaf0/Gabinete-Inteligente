# Gabinete Inteligente

Gabinete Inteligente é uma aplicação web desenvolvida para apoiar a gestão institucional por meio de organização de reuniões, acompanhamento de demandas e visualização de informações por secretaria.

A proposta da plataforma é oferecer uma interface funcional, simples e voltada para o contexto de gestão pública, facilitando o acompanhamento de atividades internas e a organização do trabalho do gabinete.

## Funcionalidades

- Tela inicial e autenticação de acesso
- Gestão de reuniões e organização por secretaria
- Páginas específicas por unidade administrativa
- Dashboard com visão geral de atividades
- Painel administrativo para gerenciamento de dados
- Interface responsiva com templates web

## Tecnologias utilizadas

- Python 3
- FastAPI
- Jinja2
- SQLAlchemy
- SQLAdmin
- SQLite
- HTML/CSS/JavaScript
- Uvicorn

## Estrutura do projeto

- main.py: definição das rotas, views e lógica principal da aplicação
- models.py: modelos de dados do sistema
- database.py: configuração do banco e sessão SQLAlchemy
- templates/: páginas HTML renderizadas pelo Jinja2
- static/: arquivos estáticos como CSS, imagens e JS
- requirements.txt: dependências do projeto

## Pré-requisitos

- Python 3.10 ou superior
- pip

## Instalação

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd GabineteInteligente
```

2. Crie um ambiente virtual:

```bash
python -m venv .venv
```

3. Ative o ambiente virtual:

No Windows:

```bash
.venv\Scripts\activate
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

4. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Executando o projeto

Inicie a aplicação com:

```bash
uvicorn main:app --reload
```

Acesse no navegador:

```text
http://127.0.0.1:8000
```

## Acesso rápido

- Página inicial: `/`
- Login: `/login`
- Solicitação de acesso: `/solicitar-acesso`
- Painel administrativo: `/admin`

## Observações

Este projeto ainda pode estar em fase de evolução e pode ser ajustado conforme as necessidades do usuário ou da instituição.

## Licença

Este projeto foi desenvolvido para uso institucional e pode ser adaptado conforme necessidade.