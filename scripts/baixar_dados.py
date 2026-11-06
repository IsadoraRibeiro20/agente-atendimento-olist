"""Baixa o dataset público da Olist do Kaggle para data/raw/.

Uso:  python scripts/baixar_dados.py

Se o download automático pedir login, crie uma conta grátis no Kaggle,
gere um token em kaggle.com/settings (API -> Create New Token) e defina
KAGGLE_USERNAME e KAGGLE_KEY. Alternativa: baixe o .zip manualmente em
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce e extraia em data/raw/.
"""

import shutil
from pathlib import Path

import kagglehub

DESTINO = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    print("⬇️  Baixando dataset olistbr/brazilian-ecommerce ...")
    origem = Path(kagglehub.dataset_download("olistbr/brazilian-ecommerce"))
    DESTINO.mkdir(parents=True, exist_ok=True)
    for csv in origem.glob("*.csv"):
        shutil.copy2(csv, DESTINO / csv.name)
        print(f"   ✔ {csv.name}")
    print(f"✅ Dados em {DESTINO}")


if __name__ == "__main__":
    main()
