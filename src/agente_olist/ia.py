"""Chamada resiliente ao Gemini: tentativas automáticas + modelo reserva.

APIs de IA às vezes falham temporariamente:
  - 503 UNAVAILABLE      -> servidor sobrecarregado ("high demand")
  - 429 RESOURCE_EXHAUSTED -> você passou do limite por minuto do plano grátis
  - 500 / 502 / 504      -> instabilidade momentânea

Em vez de quebrar, esperamos um pouco e tentamos de novo, cada vez esperando
mais ("backoff exponencial"). Se o modelo principal continuar indisponível,
trocamos para um modelo reserva. É assim que sistemas em produção lidam com APIs.
"""

import time

from google.genai import errors

from .config import MODELO_GEMINI, MODELOS_RESERVA

CODIGOS_TEMPORARIOS = {429, 500, 502, 503, 504}
TENTATIVAS_POR_MODELO = 3
ESPERA_INICIAL_S = 2.0


def gerar_conteudo(cliente, contents, config, verbose: bool = True, espera_inicial: float = ESPERA_INICIAL_S):
    """Igual a cliente.models.generate_content, mas com retentativas e fallback."""
    modelos = [MODELO_GEMINI, *[m for m in MODELOS_RESERVA if m != MODELO_GEMINI]]
    ultimo_erro = None

    for modelo in modelos:
        espera = espera_inicial
        for tentativa in range(1, TENTATIVAS_POR_MODELO + 1):
            try:
                return cliente.models.generate_content(model=modelo, contents=contents, config=config)
            except errors.APIError as e:
                if e.code not in CODIGOS_TEMPORARIOS:
                    raise  # erro definitivo (ex.: chave inválida) -> não adianta insistir
                ultimo_erro = e
                if verbose:
                    print(f"  ⏳ {modelo}: erro {e.code} ({e.status}). Tentativa {tentativa}/{TENTATIVAS_POR_MODELO}, aguardando {espera:.0f}s...")
                if tentativa < TENTATIVAS_POR_MODELO:
                    time.sleep(espera)
                    espera *= 2
        if verbose and modelo != modelos[-1]:
            print(f"  🔁 {modelo} indisponível; trocando para modelo reserva.")

    raise RuntimeError(
        "O Gemini está indisponível no momento (alta demanda ou limite do plano grátis). "
        "Aguarde alguns minutos e tente de novo."
    ) from ultimo_erro
