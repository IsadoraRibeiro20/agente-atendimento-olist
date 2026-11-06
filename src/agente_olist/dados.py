"""Camada de dados: carrega os CSVs da Olist em DataFrames do pandas.

Separar "de onde vêm os dados" do "que fazemos com eles" é uma boa prática:
se amanhã os dados vierem de um banco SQL, só este arquivo muda.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import PASTA_DADOS

ARQUIVOS = {
    "pedidos": "olist_orders_dataset.csv",
    "itens": "olist_order_items_dataset.csv",
    "pagamentos": "olist_order_payments_dataset.csv",
    "avaliacoes": "olist_order_reviews_dataset.csv",
    "clientes": "olist_customers_dataset.csv",
    "produtos": "olist_products_dataset.csv",
    "vendedores": "olist_sellers_dataset.csv",
}

COLUNAS_DATA = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


@dataclass
class BaseOlist:
    """Agrupa todas as tabelas em um único objeto fácil de passar adiante."""

    pedidos: pd.DataFrame
    itens: pd.DataFrame
    pagamentos: pd.DataFrame
    avaliacoes: pd.DataFrame
    clientes: pd.DataFrame
    produtos: pd.DataFrame
    vendedores: pd.DataFrame


def carregar_base(pasta: Path | str = PASTA_DADOS) -> BaseOlist:
    """Lê os CSVs e devolve uma BaseOlist com as datas já convertidas."""
    pasta = Path(pasta)
    faltando = [nome for nome in ARQUIVOS.values() if not (pasta / nome).exists()]
    if faltando:
        raise FileNotFoundError(
            f"Arquivos não encontrados em {pasta}: {faltando}. "
            "Rode `python scripts/baixar_dados.py` primeiro."
        )

    tabelas = {chave: pd.read_csv(pasta / nome) for chave, nome in ARQUIVOS.items()}

    for coluna in COLUNAS_DATA:
        tabelas["pedidos"][coluna] = pd.to_datetime(tabelas["pedidos"][coluna])

    return BaseOlist(**tabelas)
