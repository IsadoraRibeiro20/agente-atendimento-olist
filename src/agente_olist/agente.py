"""O agente: o "cérebro" que liga o LLM (Gemini) às ferramentas.

O ciclo agêntico, escrito à mão para você ver cada passo:

    1. Envia ao LLM: histórico da conversa + lista de ferramentas disponíveis
    2. O LLM responde de um de dois jeitos:
         a) com texto final  -> devolvemos ao usuário. FIM.
         b) pedindo para chamar ferramenta(s) -> vamos ao passo 3
    3. Executamos a(s) ferramenta(s) em Python e devolvemos o resultado ao LLM
    4. Volta ao passo 1 (o LLM agora "vê" o resultado e decide o próximo passo)

O SDK do Gemini até faz esse loop sozinho, mas desligamos de propósito
(automatic_function_calling disable=True) para fins didáticos e de controle.
"""

import json
import time

from google import genai
from google.genai import types

from . import ferramentas
from .config import TIMEOUT_GEMINI_S, obter_chave_gemini
from .ia import gerar_conteudo
from .logs import obter_logger

log = obter_logger()

INSTRUCOES = """Você é a assistente virtual de atendimento e análise de uma loja de e-commerce brasileira.
Responda sempre em português do Brasil, de forma cordial e objetiva.

Regras:
- Para qualquer número, status ou dado, USE AS FERRAMENTAS. Nunca invente dados.
- Se o cliente não informar o ID do pedido, peça.
- Ao falar de um pedido, informe status e previsão; se houver risco de atraso, avise com empatia.
- Para relatórios: primeiro colete os dados (resumo_vendas, conciliar_pagamentos,
  classificar_avaliacoes), depois escreva um relatório executivo e salve com salvar_relatorio.
- Valores em reais no formato R$ 1.234,56.
"""

MAX_PASSOS = 8  # trava de segurança para o agente não entrar em loop infinito


class Agente:
    def __init__(self, cliente: genai.Client | None = None, verbose: bool = True):
        self.cliente = cliente or genai.Client(
            api_key=obter_chave_gemini(),
            http_options=types.HttpOptions(timeout=int(TIMEOUT_GEMINI_S * 1000)),  # em milissegundos
        )
        self.verbose = verbose
        self.historico: list[types.Content] = []
        self.mapa_ferramentas = {f.__name__: f for f in ferramentas.TODAS}
        self.config = types.GenerateContentConfig(
            system_instruction=INSTRUCOES,
            tools=ferramentas.TODAS,  # o SDK transforma as funções em "declarações" para a IA
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,
        )

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _executar(self, nome: str, argumentos: dict) -> dict:
        funcao = self.mapa_ferramentas.get(nome)
        if funcao is None:
            return {"erro": f"Ferramenta desconhecida: {nome}"}
        try:
            return funcao(**argumentos)
        except Exception as e:  # o erro volta para a IA, que pode tentar de outro jeito
            return {"erro": f"{type(e).__name__}: {e}"}

    def perguntar(self, mensagem: str) -> str:
        inicio = time.perf_counter()
        log.info(f"USER  | pergunta | {mensagem[:120]!r}")
        try:
            resposta = self._perguntar(mensagem)
        finally:
            log.info(f"TOTAL | pergunta respondida | {time.perf_counter() - inicio:.2f}s")
        if self.verbose:
            print(f"  ⏱️ total: {time.perf_counter() - inicio:.1f}s\n")
        return resposta

    def _perguntar(self, mensagem: str) -> str:
        tamanho_antes = len(self.historico)
        self.historico.append(types.Content(role="user", parts=[types.Part(text=mensagem)]))

        for passo in range(1, MAX_PASSOS + 1):
            try:
                resposta = gerar_conteudo(self.cliente, self.historico, self.config, verbose=self.verbose)
            except RuntimeError as e:
                del self.historico[tamanho_antes:]  # desfaz a pergunta não respondida
                return f"⚠️ {e}"
            conteudo = resposta.candidates[0].content
            self.historico.append(conteudo)

            chamadas = resposta.function_calls
            if not chamadas:  # (a) resposta final
                return resposta.text or "(sem resposta)"

            # (b) a IA pediu ferramentas -> executamos e devolvemos os resultados
            partes = []
            for chamada in chamadas:
                args = dict(chamada.args or {})
                self._log(f"  🔧 passo {passo}: {chamada.name}({json.dumps(args, ensure_ascii=False)})")
                t = time.perf_counter()
                resultado = self._executar(chamada.name, args)
                log.info(f"TOOL  | {chamada.name} | {time.perf_counter() - t:.2f}s | {json.dumps(args, ensure_ascii=False)}")
                partes.append(types.Part.from_function_response(name=chamada.name, response={"resultado": resultado}))
            self.historico.append(types.Content(role="user", parts=partes))

        return "Desculpe, não consegui concluir. Pode reformular a pergunta?"

    def limpar(self) -> None:
        self.historico = []


def criar_agente(verbose: bool = True, com_modelo_preditivo: bool = True) -> Agente:
    """Monta tudo: carrega dados, treina o modelo, conecta a IA e as ferramentas."""
    from .dados import carregar_base
    from .preditivo import ModeloAtraso

    print("📂 Carregando dados...")
    base = carregar_base()
    modelo = None
    if com_modelo_preditivo:
        print("🤖 Treinando modelo de atraso...")
        modelo = ModeloAtraso(base)
        print(f"   AUC do modelo: {modelo.auc:.3f}")
    agente = Agente(verbose=verbose)
    ferramentas.configurar(base, modelo_atraso=modelo, cliente_ia=agente.cliente)
    print("✅ Agente pronto!")
    return agente
