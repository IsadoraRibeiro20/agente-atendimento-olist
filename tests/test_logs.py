import httpx

from agente_olist import ia
from agente_olist.logs import resumo_tempos


def test_timeout_e_tratado_como_temporario(monkeypatch):
    monkeypatch.setattr(ia, "MODELOS_RESERVA", [])

    class Models:
        n = 0

        def generate_content(self, model, contents, config):
            Models.n += 1
            if Models.n == 1:
                raise httpx.ReadTimeout("demorou")
            return "ok"

    class Cliente:
        models = Models()

    assert ia.gerar_conteudo(Cliente(), "oi", None, verbose=False, espera_inicial=0) == "ok"
    assert Models.n == 2


def test_resumo_tempos(tmp_path):
    log = tmp_path / "agente.log"
    log.write_text(
        "2026-11-07 10:00:00 | LLM   | gemini-flash-latest | tentativa 1 | 45.00s | ReadTimeout\n"
        "2026-11-07 10:00:50 | LLM   | gemini-flash-latest | tentativa 2 | 5.00s | ok | tokens in=10 out=5\n"
        "2026-11-07 10:00:50 | TOOL  | consultar_pedido | 0.50s | {}\n"
        "2026-11-07 10:00:55 | TOTAL | pergunta respondida | 52.50s\n",
        encoding="utf-8",
    )
    r = resumo_tempos(log)
    assert "52.5s" in r
    assert "50.0s" in r  # IA
    assert "1 chamadas com erro" in r
    assert "2.0s" in r  # espera entre tentativas
