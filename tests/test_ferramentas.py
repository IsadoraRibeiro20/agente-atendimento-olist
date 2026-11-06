from agente_olist import ferramentas
from agente_olist.preditivo import ModeloAtraso


def test_consultar_pedido_por_id_completo(base):
    r = ferramentas.consultar_pedido(base.pedidos.order_id[5])
    assert r["status"] == "delivered"
    assert r["total_pago"] > 0
    assert len(r["itens"]) == 1


def test_consultar_pedido_por_prefixo(base):
    oid = base.pedidos.order_id[0]
    r = ferramentas.consultar_pedido(oid[:10])  # só os 10 primeiros caracteres
    assert r["status"] == "shipped"
    assert r["data_entrega"] is None


def test_pedido_inexistente(base):
    assert "erro" in ferramentas.consultar_pedido("naoexiste")


def test_conciliacao_encontra_divergencia(base):
    r = ferramentas.conciliar_pagamentos()
    assert r["pedidos_analisados"] == len(base.pedidos)
    assert r["pedidos_divergentes"] == 1
    assert r["maiores_divergencias"][0]["diferenca"] == 50.0


def test_resumo_vendas(base):
    r = ferramentas.resumo_vendas()
    assert r["pedidos"] == len(base.pedidos)
    assert 0 <= r["taxa_atraso_pct"] <= 100
    assert "erro" in ferramentas.resumo_vendas("1999-01")


def test_modelo_preditivo(base):
    modelo = ModeloAtraso(base)
    ferramentas.configurar(base, modelo_atraso=modelo)
    r = ferramentas.prever_atraso(base.pedidos.order_id[10])
    assert 0 <= r["probabilidade_atraso"] <= 1
    assert r["risco"] in {"baixo", "médio", "alto"}


def test_salvar_relatorio(tmp_path, monkeypatch):
    monkeypatch.setattr(ferramentas, "PASTA_RELATORIOS", tmp_path)
    r = ferramentas.salvar_relatorio("Teste", "conteúdo")
    assert (tmp_path / r["salvo_em"].split("/")[-1]).read_text(encoding="utf-8").startswith("# Teste")
