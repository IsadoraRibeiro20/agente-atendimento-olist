"""Ferramentas (tools) que o agente pode usar.

Cada função aqui é Python "normal": recebe parâmetros simples e devolve um
dicionário. O Gemini lê o NOME, os PARÂMETROS e a DOCSTRING de cada função
para decidir quando chamá-la — por isso as docstrings são escritas para a IA.

Regra de ouro: a IA decide O QUE fazer; o código faz as contas.
(LLMs erram cálculos; pandas não.)
"""

from collections import Counter
from datetime import datetime

import pandas as pd

from .config import PASTA_RELATORIOS
from .dados import BaseOlist

# Estado do módulo, preenchido por configurar(). Mantém as funções simples
# (sem parâmetros técnicos), que é o formato que a IA entende melhor.
_base: BaseOlist | None = None
_modelo_atraso = None
_cliente_ia = None


def configurar(base: BaseOlist, modelo_atraso=None, cliente_ia=None) -> None:
    global _base, _modelo_atraso, _cliente_ia
    _base, _modelo_atraso, _cliente_ia = base, modelo_atraso, cliente_ia


def _exigir_base() -> BaseOlist:
    if _base is None:
        raise RuntimeError("Chame ferramentas.configurar(base) antes de usar as ferramentas.")
    return _base


def _encontrar_pedido(order_id: str) -> pd.Series | None:
    """Aceita o ID completo ou só o começo dele (mínimo 6 caracteres)."""
    pedidos = _exigir_base().pedidos
    order_id = order_id.strip().lower()
    achados = pedidos[pedidos["order_id"] == order_id]
    if achados.empty and len(order_id) >= 6:
        achados = pedidos[pedidos["order_id"].str.startswith(order_id)]
    return achados.iloc[0] if len(achados) == 1 else None


def _fmt(data) -> str | None:
    return None if pd.isna(data) else data.strftime("%d/%m/%Y")


# --------------------------------------------------------------------------
# 1) ATENDIMENTO
# --------------------------------------------------------------------------
def consultar_pedido(order_id: str) -> dict:
    """Consulta status, datas, valores e itens de um pedido.

    Use quando o cliente perguntar sobre um pedido específico (onde está,
    quando chega, quanto pagou). Aceita o ID completo ou os primeiros caracteres.
    """
    base = _exigir_base()
    pedido = _encontrar_pedido(order_id)
    if pedido is None:
        return {"erro": f"Pedido '{order_id}' não encontrado (ou ID ambíguo)."}

    oid = pedido["order_id"]
    itens = base.itens[base.itens["order_id"] == oid].merge(
        base.produtos[["product_id", "product_category_name"]], on="product_id", how="left"
    )
    pagos = base.pagamentos[base.pagamentos["order_id"] == oid]

    entregue = pedido["order_delivered_customer_date"]
    previsto = pedido["order_estimated_delivery_date"]
    atrasado = bool(pd.notna(entregue) and entregue > previsto) or bool(
        pd.isna(entregue) and pedido["order_status"] != "canceled" and previsto < base.pedidos["order_purchase_timestamp"].max()
    )

    return {
        "order_id": oid,
        "status": pedido["order_status"],
        "data_compra": _fmt(pedido["order_purchase_timestamp"]),
        "previsao_entrega": _fmt(previsto),
        "data_entrega": _fmt(entregue),
        "atrasado": atrasado,
        "itens": [
            {"categoria": r.product_category_name, "preco": round(r.price, 2), "frete": round(r.freight_value, 2)}
            for r in itens.itertuples()
        ],
        "total_pago": round(float(pagos["payment_value"].sum()), 2),
        "formas_pagamento": sorted(pagos["payment_type"].unique().tolist()),
    }


# --------------------------------------------------------------------------
# 2) PREDITIVO
# --------------------------------------------------------------------------
def prever_atraso(order_id: str) -> dict:
    """Estima, com um modelo de Machine Learning, a chance de um pedido atrasar.

    Use quando perguntarem sobre risco de atraso de um pedido.
    """
    if _modelo_atraso is None:
        return {"erro": "Modelo preditivo não carregado."}
    pedido = _encontrar_pedido(order_id)
    if pedido is None:
        return {"erro": f"Pedido '{order_id}' não encontrado."}
    prob = _modelo_atraso.prever(pedido["order_id"])
    if prob is None:
        return {"erro": "Pedido sem dados suficientes para previsão."}
    risco = "alto" if prob >= 0.6 else "médio" if prob >= 0.35 else "baixo"
    return {
        "order_id": pedido["order_id"],
        "probabilidade_atraso": round(prob, 3),
        "risco": risco,
        "qualidade_modelo_auc": round(_modelo_atraso.auc, 3),
        "fatores_mais_importantes": _modelo_atraso.importancias(),
    }


# --------------------------------------------------------------------------
# 3) CONCILIAÇÃO
# --------------------------------------------------------------------------
def conciliar_pagamentos(tolerancia_reais: float = 1.0) -> dict:
    """Cruza o valor de cada pedido (produtos + frete) com o total efetivamente pago.

    Use para auditoria financeira / conciliação. Retorna totais, quantidade de
    divergências e os maiores exemplos. Diferença positiva = pagou a mais.
    """
    base = _exigir_base()
    esperado = base.itens.groupby("order_id").apply(
        lambda g: (g["price"] + g["freight_value"]).sum(), include_groups=False
    ).rename("valor_esperado")
    pago = base.pagamentos.groupby("order_id")["payment_value"].sum().rename("valor_pago")
    parcelas = base.pagamentos.groupby("order_id")["payment_installments"].max().rename("parcelas")

    df = pd.concat([esperado, pago, parcelas], axis=1)
    df["diferenca"] = (df["valor_pago"].fillna(0) - df["valor_esperado"].fillna(0)).round(2)

    sem_pagamento = df["valor_pago"].isna() & df["valor_esperado"].notna()
    sem_itens = df["valor_esperado"].isna() & df["valor_pago"].notna()
    divergentes = df[(df["diferenca"].abs() > tolerancia_reais) & ~sem_pagamento & ~sem_itens]

    top = divergentes.reindex(divergentes["diferenca"].abs().sort_values(ascending=False).index).head(10)
    return {
        "pedidos_analisados": int(len(df)),
        "total_esperado": round(float(df["valor_esperado"].sum()), 2),
        "total_pago": round(float(df["valor_pago"].sum()), 2),
        "pedidos_sem_pagamento": int(sem_pagamento.sum()),
        "pagamentos_sem_itens": int(sem_itens.sum()),
        "pedidos_divergentes": int(len(divergentes)),
        "pct_divergentes": round(100 * len(divergentes) / max(len(df), 1), 2),
        "divergentes_parcelados_pct": round(100 * float((divergentes["parcelas"] > 1).mean()), 1) if len(divergentes) else 0.0,
        "maiores_divergencias": [
            {"order_id": oid, "esperado": round(r.valor_esperado, 2), "pago": round(r.valor_pago, 2), "diferenca": r.diferenca, "parcelas": int(r.parcelas)}
            for oid, r in top.iterrows()
        ],
    }


# --------------------------------------------------------------------------
# 4) CRUZAMENTO DE DADOS / INDICADORES
# --------------------------------------------------------------------------
def resumo_vendas(ano_mes: str = "") -> dict:
    """Indicadores de vendas: faturamento, nº de pedidos, ticket médio, nota média,
    taxa de atraso e top categorias.

    ano_mes: filtro opcional no formato 'AAAA-MM' (ex: '2018-03'). Vazio = período todo.
    """
    base = _exigir_base()
    p = base.pedidos
    if ano_mes:
        p = p[p["order_purchase_timestamp"].dt.strftime("%Y-%m") == ano_mes]
        if p.empty:
            return {"erro": f"Sem pedidos em {ano_mes}."}

    ids = set(p["order_id"])
    itens = base.itens[base.itens["order_id"].isin(ids)].merge(
        base.produtos[["product_id", "product_category_name"]], on="product_id", how="left"
    )
    faturamento = float((itens["price"] + itens["freight_value"]).sum())
    entregues = p[p["order_delivered_customer_date"].notna()]
    taxa_atraso = float((entregues["order_delivered_customer_date"] > entregues["order_estimated_delivery_date"]).mean() or 0)
    notas = base.avaliacoes[base.avaliacoes["order_id"].isin(ids)]["review_score"]
    top_cat = itens.groupby("product_category_name")["price"].sum().sort_values(ascending=False).head(5)

    return {
        "periodo": ano_mes or f"{_fmt(p['order_purchase_timestamp'].min())} a {_fmt(p['order_purchase_timestamp'].max())}",
        "pedidos": int(len(p)),
        "faturamento": round(faturamento, 2),
        "ticket_medio": round(faturamento / max(len(ids), 1), 2),
        "nota_media": round(float(notas.mean()), 2) if len(notas) else None,
        "taxa_atraso_pct": round(100 * taxa_atraso, 1),
        "status": p["order_status"].value_counts().to_dict(),
        "top_categorias_faturamento": {k: round(v, 2) for k, v in top_cat.items()},
    }


# --------------------------------------------------------------------------
# 5) CATEGORIZAÇÃO COM IA
# --------------------------------------------------------------------------
def classificar_avaliacoes(quantidade: int = 20, nota_maxima: int = 2) -> dict:
    """Usa IA para categorizar por motivo as avaliações com comentário escrito.

    quantidade: quantas avaliações analisar (máx. 50 para poupar a cota grátis).
    nota_maxima: só avalia notas até este valor (2 = só reclamações; 5 = todas).
    """
    from .classificador import classificar_textos

    if _cliente_ia is None:
        return {"erro": "Cliente de IA não configurado."}
    base = _exigir_base()
    av = base.avaliacoes
    av = av[(av["review_score"] <= nota_maxima) & av["review_comment_message"].notna()]
    amostra = av.sample(min(quantidade, 50, len(av)), random_state=7)
    textos = amostra["review_comment_message"].str.slice(0, 300).tolist()

    resultado = classificar_textos(_cliente_ia, textos)
    contagem = Counter(c.categoria.value for c in resultado)
    exemplos = {}
    for c in resultado:
        exemplos.setdefault(c.categoria.value, textos[c.indice] if c.indice < len(textos) else "")
    return {
        "avaliacoes_analisadas": len(textos),
        "por_categoria": dict(contagem.most_common()),
        "exemplo_por_categoria": exemplos,
    }


# --------------------------------------------------------------------------
# 6) RELATÓRIO
# --------------------------------------------------------------------------
def salvar_relatorio(titulo: str, conteudo_markdown: str) -> dict:
    """Salva um relatório em Markdown na pasta relatorios/.

    Use DEPOIS de reunir os dados com as outras ferramentas: escreva o relatório
    completo (resumo executivo, indicadores, riscos, recomendações) e salve.
    """
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)
    nome = f"relatorio_{datetime.now():%Y%m%d_%H%M%S}.md"
    caminho = PASTA_RELATORIOS / nome
    caminho.write_text(f"# {titulo}\n\n{conteudo_markdown}\n", encoding="utf-8")
    return {"salvo_em": str(caminho)}


TODAS = [consultar_pedido, prever_atraso, conciliar_pagamentos, resumo_vendas, classificar_avaliacoes, salvar_relatorio]
