"""Registro (log) do que o agente faz e de quanto tempo cada etapa leva.

Grava em logs/agente.log. Cada linha tem data/hora, etapa e duração, por exemplo:

    2026-11-07 10:15:02 | LLM   | gemini-flash-latest | tentativa 1 | 4.21s | ok | tokens in=1830 out=95
    2026-11-07 10:15:02 | TOOL  | consultar_pedido | 0.03s | {"order_id": "e481f51c"}

Com isso você responde "por que demorou?" com dados, não com achismo.
No Colab, veja com:  !cat logs/agente.log   ou baixe pelo painel de arquivos (📁).
"""

import logging

from .config import PASTA_LOGS

_FORMATO = "%(asctime)s | %(message)s"


def obter_logger() -> logging.Logger:
    logger = logging.getLogger("agente_olist")
    if not logger.handlers:  # configura só uma vez
        PASTA_LOGS.mkdir(parents=True, exist_ok=True)
        arquivo = logging.FileHandler(PASTA_LOGS / "agente.log", encoding="utf-8")
        arquivo.setFormatter(logging.Formatter(_FORMATO, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(arquivo)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def resumo_tempos(caminho=None, ultimas: int = 300) -> str:
    """Lê o log e responde: quanto do tempo foi IA (LLM), ferramentas e espera entre tentativas."""
    caminho = caminho or PASTA_LOGS / "agente.log"
    try:
        linhas = caminho.read_text(encoding="utf-8").splitlines()[-ultimas:]
    except FileNotFoundError:
        return "Ainda não há log."

    def segundos(partes):
        for p in partes:
            if p.endswith("s") and p[:-1].replace(".", "", 1).isdigit():
                return float(p[:-1])
        return None

    total = llm = tool = 0.0
    erros_llm = 0
    lentas = []
    for linha in linhas:
        partes = [p.strip() for p in linha.split("|")]
        if len(partes) < 3 or (s := segundos(partes)) is None:
            continue
        tipo = partes[1]
        if tipo == "TOTAL":
            total += s
        elif tipo == "LLM":
            llm += s
            erros_llm += "ok" not in partes
            lentas.append((s, f"LLM  {partes[2]} ({partes[3]})"))
        elif tipo == "TOOL":
            tool += s
            lentas.append((s, f"TOOL {partes[2]}"))

    if total == 0:
        return "Nenhuma pergunta registrada ainda."
    espera = max(total - llm - tool, 0)
    pct = lambda x: f"{100 * x / total:4.0f}%"
    texto = [
        f"Tempo total das perguntas: {total:.1f}s",
        f"  IA (chamadas ao Gemini):     {llm:7.1f}s {pct(llm)}   ({erros_llm} chamadas com erro/timeout)",
        f"  Ferramentas (Python/pandas): {tool:7.1f}s {pct(tool)}",
        f"  Espera entre tentativas:     {espera:7.1f}s {pct(espera)}",
        "Etapas mais lentas:",
    ]
    texto += [f"  {s:7.1f}s  {d}" for s, d in sorted(lentas, reverse=True)[:5]]
    return "\n".join(texto)
