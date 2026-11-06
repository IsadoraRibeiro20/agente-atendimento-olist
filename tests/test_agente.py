"""Testa o LOOP do agente com uma IA "de mentira" (mock).

A IA falsa primeiro pede a ferramenta consultar_pedido e, depois de receber o
resultado, responde com texto. Assim validamos o ciclo agêntico sem internet.
"""

from google.genai import types

from agente_olist.agente import Agente


def _resposta(parte: types.Part) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[parte]))]
    )


class ModelsFalso:
    def __init__(self, order_id):
        self.chamadas = 0
        self.order_id = order_id
        self.ultimo_contents = None

    def generate_content(self, model, contents, config):
        self.chamadas += 1
        self.ultimo_contents = list(contents)
        if self.chamadas == 1:
            return _resposta(types.Part(function_call=types.FunctionCall(name="consultar_pedido", args={"order_id": self.order_id})))
        return _resposta(types.Part(text="Seu pedido foi entregue!"))


class ClienteFalso:
    def __init__(self, order_id):
        self.models = ModelsFalso(order_id)


def test_loop_agentico_chama_ferramenta_e_responde(base):
    cliente = ClienteFalso(base.pedidos.order_id[3])
    agente = Agente(cliente=cliente, verbose=False)

    resposta = agente.perguntar("Cadê meu pedido?")

    assert resposta == "Seu pedido foi entregue!"
    assert cliente.models.chamadas == 2
    # o resultado da ferramenta foi devolvido à IA na 2ª chamada
    retorno = cliente.models.ultimo_contents[-1].parts[0].function_response
    assert retorno.name == "consultar_pedido"
    assert retorno.response["resultado"]["status"] == "delivered"
