# 🛒 Agente de Atendimento e Análise com IA — Olist

![testes](https://github.com/IsadoraRibeiro20/agente-atendimento-olist/actions/workflows/testes.yml/badge.svg)
[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IsadoraRibeiro20/agente-atendimento-olist/blob/main/notebooks/demo_colab.ipynb)

Agente de IA que **atende clientes, prevê atrasos, concilia pagamentos, categoriza
reclamações e gera relatórios** sobre ~100 mil pedidos reais (anonimizados) do
e-commerce brasileiro [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Projeto 100% gratuito: Google Colab + Gemini API (plano grátis) + dados públicos.

## 💬 Exemplo

> **Você:** Qual o status do pedido e481f51c? Tem risco de atrasar?
>
> 🔧 `consultar_pedido(order_id="e481f51c")`
> 🔧 `prever_atraso(order_id="e481f51c")`
>
> **Agente:** Seu pedido já foi entregue, antes da data prevista. 🎉 O risco calculado pelo modelo era baixo. …  *(exemplo ilustrativo)*

## 🧠 Como funciona

```
 Usuário (chat web / terminal)
          │ pergunta
          ▼
 ┌──────────────────────┐   "chame consultar_pedido(...)"   ┌───────────────────────┐
 │   Agente (agente.py) │ ◄───────────────────────────────► │ Gemini (LLM, decide)  │
 │   loop agêntico      │      resultado da ferramenta      └───────────────────────┘
 └─────────┬────────────┘
           │ executa
           ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │ Ferramentas (ferramentas.py) — Python + pandas, contas exatas       │
 │  consultar_pedido │ prever_atraso (ML) │ conciliar_pagamentos       │
 │  resumo_vendas    │ classificar_avaliacoes (IA) │ salvar_relatorio  │
 └─────────────────────────────────────────────────────────────────────┘
           │
           ▼
   Dados Olist (CSVs → pandas)
```

**Princípio:** a IA *decide o que fazer*; o código *faz as contas*. LLMs erram cálculos —
por isso toda informação numérica vem das ferramentas. Detalhes em [docs/arquitetura.md](docs/arquitetura.md).

| Capacidade | Ferramenta | Técnica |
|---|---|---|
| Atendimento | `consultar_pedido` | consulta pandas |
| Preditivo | `prever_atraso` | Random Forest (scikit-learn) |
| Conciliação | `conciliar_pagamentos` | cruzamento itens × pagamentos |
| Cruzamento / KPIs | `resumo_vendas` | agregações pandas |
| Categorização | `classificar_avaliacoes` | Gemini com saída estruturada (JSON) |
| Relatórios | `salvar_relatorio` | LLM redige, código salva |

## 🚀 Como rodar

### Opção 1 — Google Colab (recomendado, nada para instalar)
Clique no selo **Abrir no Colab** acima e siga as células.

### Opção 2 — No seu computador
```bash
git clone https://github.com/IsadoraRibeiro20/agente-atendimento-olist.git
cd agente-atendimento-olist
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/baixar_dados.py
export GEMINI_API_KEY="sua_chave"                     # grátis em aistudio.google.com/apikey
python -m agente_olist.app                            # chat web
python -m agente_olist.app --terminal                 # chat no terminal
```

### Testes
```bash
pytest -v
```
Os testes usam dados sintéticos e uma IA falsa (*mock*): rodam sem internet e sem gastar cota.

## 📁 Estrutura

```
agente-atendimento-olist/
├── .github/workflows/testes.yml  # CI: roda os testes a cada push
├── data/                         # dados (não versionados) + dicionário
├── docs/arquitetura.md           # decisões técnicas
├── notebooks/demo_colab.ipynb    # demonstração no Colab
├── relatorios/                   # relatórios gerados pelo agente
├── scripts/baixar_dados.py       # download do dataset
├── src/agente_olist/
│   ├── config.py                 # configurações e chave da API
│   ├── dados.py                  # carga dos CSVs
│   ├── ferramentas.py            # tools do agente
│   ├── preditivo.py              # modelo de ML de atraso
│   ├── classificador.py          # categorização com IA
│   ├── agente.py                 # loop agêntico
│   └── app.py                    # interfaces de chat (Gradio / terminal)
├── tests/                        # testes automatizados (pytest)
├── pyproject.toml                # metadados e dependências
└── requirements.txt
```

## 🗺️ Roadmap

- [x] Agente com 6 ferramentas e loop agêntico manual
- [x] Modelo preditivo de atraso
- [x] Chat web com Gradio
- [x] Testes + CI
- [ ] Bot no Telegram
- [ ] Memória de longo prazo / RAG sobre políticas da loja
- [ ] Multi-agentes (atendente + analista + auditor)
- [ ] Deploy gratuito (Hugging Face Spaces)

## 📜 Licença
Código sob MIT. Dados © Olist, sob CC BY-NC-SA 4.0.
