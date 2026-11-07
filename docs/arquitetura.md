# Arquitetura e decisões técnicas

## 1. Por que essa estrutura de pastas?

É o padrão mais usado em projetos Python profissionais (*src layout*):

| Pasta/arquivo | Para que serve | Por que importa |
|---|---|---|
| `src/agente_olist/` | o código "de verdade", como um pacote | importável de qualquer lugar (`from agente_olist import ...`) |
| `tests/` | testes automatizados | prova que funciona; recrutadores olham |
| `notebooks/` | experimentos e demos | notebook **usa** o pacote, não contém a lógica |
| `scripts/` | tarefas avulsas (baixar dados) | separa utilitário de produto |
| `docs/` | documentação técnica | mostra raciocínio |
| `data/` | dados locais, **fora do git** | repositório leve; respeita licença |
| `.github/workflows/` | CI (GitHub Actions) | testes rodam sozinhos a cada push |
| `pyproject.toml` | nome, versão, dependências | `pip install -e .` instala o projeto |
| `.gitignore` | o que o git ignora | evita subir senhas e arquivos gigantes |
| `.env.example` | modelo de configuração | mostra quais segredos são necessários, sem expô-los |

**Regra:** notebook é vitrine; lógica fica em `src/`. Código em `.py` é testável,
versionável (diff legível) e reaproveitável — notebook não.

## 2. Camadas

```
app.py          → interface (como o usuário fala com o agente)
agente.py       → orquestração (o loop LLM ↔ ferramentas)
ferramentas.py  → regras de negócio (o que o agente sabe fazer)
preditivo.py / classificador.py → modelos (ML e IA especializada)
dados.py        → acesso a dados (de onde vêm)
config.py       → configuração
```

Cada camada só conhece a de baixo. Trocar Gradio por Telegram mexe só em `app.py`;
trocar CSV por banco SQL mexe só em `dados.py`.

## 3. O loop agêntico

Implementado à mão em `Agente.perguntar()` (o SDK faria automático, mas o
objetivo é aprender):

1. Envia histórico + declarações das ferramentas ao Gemini.
2. Se a resposta tem `function_calls`, executa cada uma em Python e devolve o
   resultado como `function_response`.
3. Repete até a IA responder com texto, ou até `MAX_PASSOS` (trava de segurança).

Erros nas ferramentas **voltam para a IA** como `{"erro": ...}` em vez de
derrubar o programa — assim ela pode pedir o dado correto ao usuário.

## 4. Decisões

- **Gemini Flash (plano grátis)**: suporta *function calling* e saída estruturada sem custo.
- **Contas no pandas, não no LLM**: precisão e auditabilidade.
- **Classificação em lote**: 1 chamada para N avaliações → economiza cota.
- **Random Forest com `class_weight="balanced"`**: atrasos são minoria (cerca de 8% dos pedidos); o
  balanceamento evita um modelo que só diz "não atrasa". Métrica: AUC.
- **Resiliência (`ia.py`)**: erros temporários da API (503 sobrecarga, 429 limite) são
  repetidos com espera crescente (*backoff exponencial*) e, se persistirem, o agente troca
  para um modelo reserva. Erros definitivos (ex.: chave inválida) não são repetidos.
- **Tempo limite (`GEMINI_TIMEOUT_S`, padrão 45s)**: em alta demanda o servidor pode segurar a
  requisição por minutos; cortamos e tentamos de novo.
- **Log (`logs.py`)**: cada chamada à IA e ferramenta é cronometrada em `logs/agente.log`;
  `resumo_tempos()` mostra onde o tempo foi gasto.
- **Mock da IA nos testes**: testes determinísticos, rápidos e gratuitos.

## 5. Hipóteses para investigar nos dados reais

- Pedidos pagos no **cartão parcelado** podem ter `valor_pago > produtos + frete`
  (juros do parcelamento)? Use `conciliar_pagamentos` para confirmar.
- O atraso depende mais do **prazo prometido** ou do **envio entre estados**? Veja `fatores_mais_importantes` em `prever_atraso`.
