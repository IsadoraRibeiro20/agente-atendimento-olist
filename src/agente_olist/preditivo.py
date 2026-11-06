"""Modelo preditivo: estima a chance de um pedido ser entregue com atraso.

É um modelo de Machine Learning "clássico" (Random Forest, do scikit-learn),
treinado com o histórico de pedidos já entregues. O agente de IA usa esse
modelo como mais uma ferramenta — LLM e ML tradicional trabalhando juntos.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from .dados import BaseOlist

FEATURES = [
    "prazo_prometido_dias",
    "valor_produtos",
    "valor_frete",
    "qtd_itens",
    "mesmo_estado",
    "peso_total_g",
    "mes_compra",
]


def montar_features(base: BaseOlist) -> pd.DataFrame:
    """Cria uma linha por pedido com as variáveis que o modelo usa."""
    p = base.pedidos.merge(base.clientes[["customer_id", "customer_state"]], on="customer_id", how="left")

    itens = base.itens.merge(base.produtos[["product_id", "product_weight_g"]], on="product_id", how="left")
    itens = itens.merge(base.vendedores[["seller_id", "seller_state"]], on="seller_id", how="left")
    agg = itens.groupby("order_id").agg(
        valor_produtos=("price", "sum"),
        valor_frete=("freight_value", "sum"),
        qtd_itens=("order_item_id", "count"),
        peso_total_g=("product_weight_g", "sum"),
        seller_state=("seller_state", "first"),
    )
    df = p.merge(agg, on="order_id", how="inner")

    df["prazo_prometido_dias"] = (df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]).dt.days
    df["mesmo_estado"] = (df["customer_state"] == df["seller_state"]).astype(int)
    df["mes_compra"] = df["order_purchase_timestamp"].dt.month
    df["atrasou"] = (df["order_delivered_customer_date"] > df["order_estimated_delivery_date"]).astype(int)
    df[FEATURES] = df[FEATURES].fillna(0)
    return df.set_index("order_id")


class ModeloAtraso:
    """Encapsula treino e previsão. Treina uma vez e reaproveita."""

    def __init__(self, base: BaseOlist):
        self.features = montar_features(base)
        entregues = self.features[self.features["order_delivered_customer_date"].notna()]

        X, y = entregues[FEATURES], entregues["atrasou"]
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        self.modelo = RandomForestClassifier(
            n_estimators=100, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1
        )
        self.modelo.fit(X_tr, y_tr)
        self.auc = float(roc_auc_score(y_te, self.modelo.predict_proba(X_te)[:, 1]))

    def prever(self, order_id: str) -> float | None:
        """Probabilidade (0 a 1) de atraso para um pedido, ou None se não existir."""
        if order_id not in self.features.index:
            return None
        linha = self.features.loc[[order_id], FEATURES]
        return float(self.modelo.predict_proba(linha)[0, 1])

    def importancias(self) -> dict[str, float]:
        return dict(sorted(zip(FEATURES, self.modelo.feature_importances_.round(3)), key=lambda x: -x[1]))
