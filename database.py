"""
Database management and in-memory datastores for Gabinete Inteligente (Python/FastAPI)
"""

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

LOGOS_SECRETARIAS = {
    "ADM": "/static/imagens/adm_bg.png",
    "Saude": "/static/imagens/saude_bg.png",
    "SEDUC": "/static/imagens/seduc_bg.png",
    "Obras": "/static/imagens/obras_bg.png",
    "FIN": "/static/imagens/fin_bg.png",
    "ServicosPublicos": "/static/imagens/servpub_bg.png",
    "SEDTEC": "/static/imagens/sedtec_bg.png",
    "CulturaEsportes": "/static/imagens/secult_bg.png",
    "SEPLAMA": "/static/imagens/seplama_bg.png",
    "Rural": "/static/imagens/rural_bg.png",
    "Social": "/static/imagens/social_bg.png",
    "home": "/static/imagens/padrao_bg.png",
    "pauta-livre": "/static/imagens/padrao_bg.png"
}

def obter_logo_secretaria(sec_id: str) -> str:
    return LOGOS_SECRETARIAS.get(sec_id, "/static/imagens/padrao_bg.png")

# Banco de dados de Usuário
usuario_db = {
    "nome": "Administrador",
    "inicial": "AD",
    "email": "admin@prefeitura.gov.br",
    "cargo": "Chefe de Gabinete",
    "secretaria": "home",
    "telefone": "(81) 99888-7777",
    "notif_email": True,
    "notif_whatsapp": True,
    "senha": "1234"
}

# Banco de dados Global de Participantes Cadastrados
participantes_db = [
    {"id": 1, "nome": "Fabiana Souza", "cargo": "Secretária de Administração", "secretaria": "ADM"},
    {"id": 2, "nome": "Carlos Oliveira", "cargo": "Diretor Geral", "secretaria": "ADM"},
    {"id": 3, "nome": "Roberto Lima", "cargo": "Secretário de Finanças", "secretaria": "FIN"},
    {"id": 4, "nome": "Maria Silva", "cargo": "Coordenadora de Projetos", "secretaria": "SEDUC"},
    {"id": 5, "nome": "João Santos", "cargo": "Assessor Técnico", "secretaria": "home"},
    {"id": 6, "nome": "Juliana Costa", "cargo": "Coordenadora de Processos", "secretaria": "ADM"}
]

# Banco de dados de Reuniões e Encaminhamentos (Demandas)
reunioes_db = [
    {
        "id": 1,
        "titulo": "Alinhamento Estratégico de Metas",
        "assunto": "Planejamento Semestral de Ações do Gabinete",
        "data": "04/08/2026",
        "hora": "09:00",
        "secretaria_id": "ADM",
        "status": "Agendada",
        "local": "Sala da Secretaria de Administração",
        "anotacoes": "Reunião para alinhamento das metas prioritárias do gabinete do prefeito para o segundo semestre de 2026.",
        "participantes": [
            {"nome": "Fabiana Souza", "iniciais": "FS", "cargo": "Secretária de Adm"},
            {"nome": "Carlos Oliveira", "iniciais": "CO", "cargo": "Diretor Geral"}
        ],
        "encaminhamentos": [
            {
                "id": 1,
                "tarefa": "Elaborar minuta do novo fluxo de processos internos",
                "responsavel": "Fabiana Souza",
                "prazo": "10/08/2026",
                "prioridade": "Alta",
                "status": "em_andamento",
                "progresso": 50,
                "concluido": False
            },
            {
                "id": 2,
                "tarefa": "Consolidar relatório de infraestrutura municipal",
                "responsavel": "Carlos Oliveira",
                "prazo": "05/08/2026",
                "prioridade": "Alta",
                "status": "atrasada",
                "progresso": 30,
                "concluido": False
            }
        ]
    },
    {
        "id": 2,
        "titulo": "Revisão Orçamentária e Finanças",
        "assunto": "Captação de Recursos e Balanço Fiscal",
        "data": "05/08/2026",
        "hora": "14:00",
        "secretaria_id": "FIN",
        "status": "Agendada",
        "local": "Auditório da Secretaria de Finanças",
        "anotacoes": "Discussão dos repasses estaduais e federais.",
        "participantes": [
            {"nome": "Roberto Lima", "iniciais": "RL", "cargo": "Secretário de Finanças"}
        ],
        "encaminhamentos": [
            {
                "id": 1,
                "tarefa": "Apresentar prestação de contas trimestral",
                "responsavel": "Roberto Lima",
                "prazo": "12/08/2026",
                "prioridade": "Média",
                "status": "aberta",
                "progresso": 10,
                "concluido": False
            }
        ]
    }
]
