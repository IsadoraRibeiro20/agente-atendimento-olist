"""Categorização com IA: classifica avaliações de clientes por motivo.

Aqui usamos o Gemini com "saída estruturada" (JSON com formato fixo).
Em vez de um texto livre, pedimos uma lista de objetos com campos definidos,
o que torna a resposta da IA confiável para ser processada por código.
"""

from enum import Enum

from pydantic import BaseModel

from .ia import gerar_conteudo


class Categoria(str, Enum):
    ATRASO = "atraso_entrega"
    NAO_RECEBIDO = "produto_nao_recebido"
    DEFEITO = "produto_defeituoso_ou_errado"
    QUALIDADE = "qualidade_abaixo_esperado"
    ATENDIMENTO = "atendimento_ou_comunicacao"
    ELOGIO = "elogio"
    OUTRO = "outro"


class Classificacao(BaseModel):
    indice: int
    categoria: Categoria
    sentimento: str  # "positivo", "neutro" ou "negativo"


PROMPT = """Você classifica avaliações de clientes de um e-commerce brasileiro.
Para cada avaliação numerada abaixo, devolva a categoria principal e o sentimento.

{avaliacoes}"""


def classificar_textos(cliente, textos: list[str]) -> list[Classificacao]:
    """Envia vários textos em UMA chamada (economiza a cota grátis da API)."""
    from google.genai import types

    numeradas = "\n".join(f"{i}. {t}" for i, t in enumerate(textos))
    resposta = gerar_conteudo(
        cliente,
        PROMPT.format(avaliacoes=numeradas),
        types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[Classificacao],
            temperature=0,
        ),
    )
    return resposta.parsed
