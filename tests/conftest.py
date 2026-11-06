"""Dados falsos (sintéticos) com o mesmo formato da Olist.

Permite testar o código sem baixar nada e sem gastar cota da API.
"""

import hashlib

import numpy as np
import pandas as pd
import pytest

from agente_olist import ferramentas
from agente_olist.dados import BaseOlist

N = 300


@pytest.fixture
def base() -> BaseOlist:
    rng = np.random.default_rng(0)
    ids = [hashlib.md5(str(i).encode()).hexdigest() for i in range(N)]
    compra = pd.Timestamp("2018-01-01") + pd.to_timedelta(rng.integers(0, 180, N), unit="D")
    prazo = rng.integers(7, 30, N)
    estimada = compra + pd.to_timedelta(prazo, unit="D")
    entrega = compra + pd.to_timedelta(prazo + rng.integers(-5, 8, N), unit="D")

    pedidos = pd.DataFrame({
        "order_id": ids,
        "customer_id": [f"c{i}" for i in range(N)],
        "order_status": "delivered",
        "order_purchase_timestamp": compra,
        "order_approved_at": compra,
        "order_delivered_carrier_date": compra,
        "order_delivered_customer_date": entrega,
        "order_estimated_delivery_date": estimada,
    })
    pedidos.loc[0, "order_status"] = "shipped"
    pedidos.loc[0, "order_delivered_customer_date"] = pd.NaT

    precos = rng.uniform(20, 500, N).round(2)
    fretes = rng.uniform(5, 40, N).round(2)
    itens = pd.DataFrame({
        "order_id": ids, "order_item_id": 1, "product_id": [f"p{i % 10}" for i in range(N)],
        "seller_id": [f"s{i % 5}" for i in range(N)], "price": precos, "freight_value": fretes,
    })
    pagos = (precos + fretes).round(2)
    pagos[1] += 50.0  # divergência proposital: pagou R$ 50 a mais
    pagamentos = pd.DataFrame({
        "order_id": ids, "payment_sequential": 1, "payment_type": "credit_card",
        "payment_installments": 1, "payment_value": pagos,
    })
    avaliacoes = pd.DataFrame({
        "review_id": [f"r{i}" for i in range(N)], "order_id": ids,
        "review_score": rng.integers(1, 6, N),
        "review_comment_message": ["Produto chegou atrasado"] * N,
    })
    clientes = pd.DataFrame({"customer_id": [f"c{i}" for i in range(N)], "customer_state": rng.choice(["SP", "RJ", "MG"], N)})
    produtos = pd.DataFrame({"product_id": [f"p{i}" for i in range(10)], "product_category_name": "beleza_saude", "product_weight_g": 500})
    vendedores = pd.DataFrame({"seller_id": [f"s{i}" for i in range(5)], "seller_state": "SP"})

    b = BaseOlist(pedidos, itens, pagamentos, avaliacoes, clientes, produtos, vendedores)
    ferramentas.configurar(b)
    return b
