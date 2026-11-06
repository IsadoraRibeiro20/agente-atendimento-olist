"""Configurações centrais do projeto.

Tudo que pode mudar entre ambientes (seu PC, Colab, servidor) fica aqui,
lido de variáveis de ambiente. Assim o código não tem "valores mágicos"
espalhados e nenhuma chave secreta vai parar no GitHub.
"""

import os
from pathlib import Path

# Raiz do repositório (duas pastas acima deste arquivo: src/agente_olist -> raiz)
RAIZ_PROJETO = Path(__file__).resolve().parents[2]

# Onde ficam os CSVs da Olist (baixados por scripts/baixar_dados.py)
PASTA_DADOS = Path(os.getenv("OLIST_DATA_DIR", RAIZ_PROJETO / "data" / "raw"))

# Onde os relatórios gerados são salvos
PASTA_RELATORIOS = Path(os.getenv("OLIST_REPORTS_DIR", RAIZ_PROJETO / "relatorios"))

# Modelo do Gemini. "gemini-flash-latest" aponta sempre para o Flash mais
# recente, que faz parte do plano gratuito do Google AI Studio.
MODELO_GEMINI = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Modelos usados se o principal estiver sobrecarregado (erro 503) ou no limite (429).
# Separados por vírgula. O Flash-Lite é mais leve e costuma ter mais disponibilidade.
MODELOS_RESERVA = [
    m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest").split(",") if m.strip()
]


def obter_chave_gemini() -> str:
    """Busca a chave da API: primeiro nos Secrets do Colab, depois no ambiente."""
    try:  # Só existe dentro do Google Colab
        from google.colab import userdata  # type: ignore

        chave = userdata.get("GEMINI_API_KEY")
        if chave:
            return chave
    except Exception:
        pass

    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada. Crie uma chave grátis em "
            "https://aistudio.google.com/apikey e defina a variável de ambiente "
            "(ou o Secret no Colab)."
        )
    return chave
