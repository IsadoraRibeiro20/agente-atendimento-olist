"""Chamada resiliente ao Gemini: tempo limite + tentativas + modelo reserva + log.

APIs de IA às vezes falham ou travam temporariamente:
  - 503 UNAVAILABLE        -> servidor sobrecarregado ("high demand")
  - 429 RESOURCE_EXHAUSTED -> você passou do limite por minuto do plano grátis
  - 500 / 502 / 504        -> instabilidade momentânea
  - timeout                -> o servidor "segurou" a requisição tempo demais

Em vez de quebrar (ou ficar minutos parado), cortamos no tempo limite, esperamos
um pouco e tentamos de novo, cada vez esperando mais ("backoff exponencial").
Se o modelo principal continuar ruim, trocamos para um modelo reserva.
Toda chamada é cronometrada e registrada em logs/agente.log.
"""

import time

import httpx
from google.genai import errors

from .config import MODELO_GEMINI, MODELOS_RESERVA
from .logs import obter_logger

CODIGOS_TEMPORARIOS = {429, 500, 502, 503, 504}
TENTATIVAS_POR_MODELO = 3
ESPERA_INICIAL_S = 2.0

log = obter_logger()


def _tokens(resposta) -> str:
    uso = getattr(resposta, "usage_metadata", None)
    if not uso:
        return ""
    return f"tokens in={uso.prompt_token_count} out={uso.candidates_token_count} pensamento={uso.thoughts_token_count or 0}"


def gerar_conteudo(cliente, contents, config, verbose: bool = True, espera_inicial: float = ESPERA_INICIAL_S):
    """Igual a cliente.models.generate_content, mas com timeout, retentativas, fallback e log."""
    modelos = [MODELO_GEMINI, *[m for m in MODELOS_RESERVA if m != MODELO_GEMINI]]
    ultimo_erro = None

    for modelo in modelos:
        espera = espera_inicial
        for tentativa in range(1, TENTATIVAS_POR_MODELO + 1):
            inicio = time.perf_counter()
            try:
                resposta = cliente.models.generate_content(model=modelo, contents=contents, config=config)
                dur = time.perf_counter() - inicio
                log.info(f"LLM   | {modelo} | tentativa {tentativa} | {dur:.2f}s | ok | {_tokens(resposta)}")
                if verbose:
                    print(f"  🧠 {modelo}: respondeu em {dur:.1f}s")
                return resposta
            except errors.APIError as e:
                dur = time.perf_counter() - inicio
                log.info(f"LLM   | {modelo} | tentativa {tentativa} | {dur:.2f}s | erro {e.code} {e.status}")
                if e.code not in CODIGOS_TEMPORARIOS:
                    raise  # erro definitivo (ex.: chave inválida) -> não adianta insistir
                ultimo_erro, motivo = e, f"erro {e.code} ({e.status}) após {dur:.0f}s"
            except httpx.TransportError as e:  # timeout ou queda de conexão
                dur = time.perf_counter() - inicio
                log.info(f"LLM   | {modelo} | tentativa {tentativa} | {dur:.2f}s | {type(e).__name__}")
                ultimo_erro, motivo = e, f"sem resposta em {dur:.0f}s ({type(e).__name__})"

            if verbose:
                print(f"  ⏳ {modelo}: {motivo}. Tentativa {tentativa}/{TENTATIVAS_POR_MODELO}"
                      + (f", aguardando {espera:.0f}s..." if tentativa < TENTATIVAS_POR_MODELO else ""))
            if tentativa < TENTATIVAS_POR_MODELO:
                time.sleep(espera)
                espera *= 2
        if verbose and modelo != modelos[-1]:
            print(f"  🔁 {modelo} indisponível; trocando para modelo reserva.")

    raise RuntimeError(
        "O Gemini está indisponível no momento (alta demanda ou limite do plano grátis). "
        "Aguarde alguns minutos e tente de novo."
    ) from ultimo_erro
