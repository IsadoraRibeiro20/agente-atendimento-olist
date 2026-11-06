"""Testa a resiliência contra o erro 503 'high demand' do Gemini."""

import pytest
from google.genai import errors

from agente_olist import ia

ERRO_503 = {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}}
ERRO_400 = {"error": {"code": 400, "message": "API key not valid", "status": "INVALID_ARGUMENT"}}


class ModelsQueFalha:
    """Falha com o erro dado nas primeiras `falhas` chamadas, depois responde."""

    def __init__(self, falhas, erro=errors.ServerError(503, ERRO_503)):
        self.falhas, self.erro, self.modelos_usados = falhas, erro, []

    def generate_content(self, model, contents, config):
        self.modelos_usados.append(model)
        if len(self.modelos_usados) <= self.falhas:
            raise self.erro
        return "ok"


class Cliente:
    def __init__(self, models):
        self.models = models


def test_tenta_de_novo_apos_503():
    m = ModelsQueFalha(falhas=2)
    assert ia.gerar_conteudo(Cliente(m), "oi", None, verbose=False, espera_inicial=0) == "ok"
    assert len(m.modelos_usados) == 3


def test_troca_para_modelo_reserva(monkeypatch):
    monkeypatch.setattr(ia, "MODELOS_RESERVA", ["modelo-reserva"])
    m = ModelsQueFalha(falhas=ia.TENTATIVAS_POR_MODELO)  # principal falha todas as vezes
    assert ia.gerar_conteudo(Cliente(m), "oi", None, verbose=False, espera_inicial=0) == "ok"
    assert m.modelos_usados[-1] == "modelo-reserva"


def test_desiste_com_mensagem_amigavel(monkeypatch):
    monkeypatch.setattr(ia, "MODELOS_RESERVA", [])
    m = ModelsQueFalha(falhas=99)
    with pytest.raises(RuntimeError, match="indisponível"):
        ia.gerar_conteudo(Cliente(m), "oi", None, verbose=False, espera_inicial=0)


def test_erro_definitivo_nao_repete():
    m = ModelsQueFalha(falhas=99, erro=errors.ClientError(400, ERRO_400))
    with pytest.raises(errors.ClientError):
        ia.gerar_conteudo(Cliente(m), "oi", None, verbose=False, espera_inicial=0)
    assert len(m.modelos_usados) == 1
