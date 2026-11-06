# Dados

Os CSVs **não ficam no repositório** (são grandes e têm licença própria).
Baixe com:

```bash
python scripts/baixar_dados.py
```

Fonte: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
— ~100 mil pedidos reais anonimizados (2016–2018), licença CC BY-NC-SA 4.0.

| Arquivo | Conteúdo | Usado em |
|---|---|---|
| `olist_orders_dataset.csv` | pedidos, status e datas | atendimento, preditivo |
| `olist_order_items_dataset.csv` | itens, preço e frete | conciliação, indicadores |
| `olist_order_payments_dataset.csv` | pagamentos e parcelas | conciliação |
| `olist_order_reviews_dataset.csv` | notas e comentários (PT-BR) | categorização com IA |
| `olist_customers_dataset.csv` | cliente e estado | preditivo |
| `olist_products_dataset.csv` | categoria e peso | indicadores, preditivo |
| `olist_sellers_dataset.csv` | vendedor e estado | preditivo |
