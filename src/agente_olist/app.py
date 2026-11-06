"""Interfaces de chat para o agente.

- Terminal:  python -m agente_olist.app --terminal
- Web:       python -m agente_olist.app          (abre um chat no navegador)
- Colab:     python -m agente_olist.app --share  (gera link público temporário)
"""

import argparse

from .agente import criar_agente

EXEMPLOS = [
    "Qual o status do pedido e481f51cbdc54678b7cc49136f2d6af7?",
    "Esse pedido tem risco de atraso? e481f51c",
    "Faça a conciliação dos pagamentos e me diga se há problemas.",
    "Como foram as vendas em 2018-03?",
    "Quais os principais motivos de reclamação dos clientes?",
    "Gere um relatório executivo completo e salve.",
]


def chat_terminal() -> None:
    agente = criar_agente()
    print("\nDigite sua pergunta ('sair' para encerrar, 'limpar' para nova conversa)\n")
    while True:
        pergunta = input("Você: ").strip()
        if pergunta.lower() in {"sair", "exit", "quit"}:
            break
        if pergunta.lower() == "limpar":
            agente.limpar()
            continue
        if pergunta:
            print(f"\nAgente: {agente.perguntar(pergunta)}\n")


def chat_web(share: bool = False) -> None:
    import gradio as gr

    agente = criar_agente()

    def responder(mensagem, historico):
        if not historico:  # usuário clicou em "limpar" no chat
            agente.limpar()
        return agente.perguntar(mensagem)

    gr.ChatInterface(
        responder,
        title="🛒 Atendimento Inteligente — Olist",
        description="Agente de IA com ferramentas: consulta de pedidos, previsão de atraso, conciliação, indicadores e relatórios.",
        examples=EXEMPLOS,
    ).launch(share=share)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente de atendimento Olist")
    parser.add_argument("--terminal", action="store_true", help="chat no terminal")
    parser.add_argument("--share", action="store_true", help="gera link público (Gradio)")
    args = parser.parse_args()
    chat_terminal() if args.terminal else chat_web(share=args.share)


if __name__ == "__main__":
    main()
