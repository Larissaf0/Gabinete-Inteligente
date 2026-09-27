# 🏛️ Gabinete Inteligente

Sistema web desenvolvido para apoiar a **gestão, organização e acompanhamento das atividades de um Gabinete Municipal**, centralizando reuniões, demandas, encaminhamentos e informações das Secretarias Municipais.

O projeto busca transformar informações administrativas dispersas em um ambiente único de acompanhamento, permitindo maior controle sobre reuniões, responsabilidades, prazos e andamento das demandas da gestão.

---

## 🎯 Objetivo

O **Gabinete Inteligente** foi desenvolvido para auxiliar o Poder Executivo Municipal no acompanhamento das ações realizadas entre o Gabinete e as Secretarias.

A plataforma permite:

- organizar reuniões por Secretaria;
- registrar pautas e encaminhamentos;
- acompanhar demandas através de Kanban;
- definir responsáveis, prioridades e prazos;
- acompanhar o histórico de atualizações das demandas;
- visualizar indicadores consolidados;
- acompanhar individualmente cada Secretaria;
- centralizar informações estratégicas do Gabinete.

---

## ✨ Principais funcionalidades

### 📊 Dashboard do Gabinete
Visão consolidada das Secretarias Municipais, reuniões e demandas cadastradas no sistema.

### 🏢 Gestão por Secretaria
Cada Secretaria possui seu próprio ambiente, permitindo visualizar informações, reuniões e demandas relacionadas especificamente ao setor.

### 📅 Gestão de Reuniões
Permite cadastrar e acompanhar reuniões contendo informações como:

- título;
- data e horário;
- participantes;
- pauta;
- observações;
- encaminhamentos.

### 📋 Kanban de Demandas
Os encaminhamentos das reuniões são transformados em demandas que podem ser acompanhadas por status:

- **Aberta**
- **Em andamento**
- **Concluída**
- **Atrasada**

O sistema possui Kanban geral do Gabinete e visualizações específicas por Secretaria.

### 🕒 Histórico de Demandas
Permite acompanhar a evolução de uma demanda através de uma linha do tempo de versões e atualizações.

As atualizações podem registrar alterações de informações como responsável, prazo, status e observações.

### 🔔 Notificações
Estrutura para acompanhamento de informações importantes relacionadas a reuniões, prazos e demandas.

### 🤖 Inteligência Artificial
O projeto possui estrutura preparada para integração de recursos de IA voltados à análise de reuniões, pautas e encaminhamentos administrativos.

---

## 🛠️ Tecnologias

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### Frontend

- HTML5
- CSS3
- JavaScript
- Jinja2
- Bootstrap / Tabler
- Font Awesome

### Banco de dados

- Supabase
- PostgreSQL

### Infraestrutura

- Git / GitHub
- Vercel
- Variáveis de ambiente para credenciais e configurações sensíveis

---

## 🏗️ Arquitetura

A aplicação utiliza o **FastAPI** como backend e o **Jinja2** para renderização das interfaces.

O **Supabase** é utilizado como camada de persistência dos dados.

Fluxo simplificado:

```text
Usuário
   │
   ▼
Interface Web
HTML / CSS / JavaScript
   │
   ▼
Jinja2 Templates
   │
   ▼
FastAPI
   │
   ▼
Supabase
   │
   ▼
PostgreSQL