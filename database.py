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

# Aliases oficiais atuais preservando compatibilidade com IDs legados
NOMES_SECRETARIAS.update({
    "SADM": "Administração",
    "SDR": "Desenvolvimento Rural",
    "SDS": "Desenvolvimento Social",
    "SDTEC": "Desenvolvimento Econômico, Ciência e Tecnologia",
    "SDUO": "Desenvolvimento Urbano e Obras",
    "SECULTE": "Cultura e Esportes",
    "SFIN": "Finanças",
    "SPMA": "Planejamento e Meio Ambiente",
    "SSAU": "Saúde",
    "SSP": "Serviços Públicos",
})

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

LOGOS_SECRETARIAS.update({
    "SADM": "/static/imagens/adm_bg.png",
    "SDR": "/static/imagens/rural_bg.png",
    "SDS": "/static/imagens/social_bg.png",
    "SDTEC": "/static/imagens/sedtec_bg.png",
    "SDUO": "/static/imagens/obras_bg.png",
    "SECULTE": "/static/imagens/secult_bg.png",
    "SFIN": "/static/imagens/fin_bg.png",
    "SPMA": "/static/imagens/seplama_bg.png",
    "SSAU": "/static/imagens/saude_bg.png",
    "SSP": "/static/imagens/servpub_bg.png",
})

def obter_logo_secretaria(sec_id: str) -> str:
    return LOGOS_SECRETARIAS.get(sec_id, "/static/imagens/padrao_bg.png")

# Compatibilidade legada: dados dinâmicos agora vêm do Supabase.
participantes_db = []

# Banco de dados de Reuniões e Encaminhamentos (Demandas)
reunioes_db = []
