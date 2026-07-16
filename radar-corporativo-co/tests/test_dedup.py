import json
from datetime import date

from src.dedup import carregar_vistos, filtrar_novos, registrar_e_podar, salvar_vistos
from src.models import Item

HOJE = date(2026, 7, 16)


def _item(url):
    return Item(secao="noticias", uf="GO", titulo="t", url=url, resumo="",
                fonte="Teste", publicado_em=HOJE)


def test_primeira_execucao_mantem_tudo_e_segunda_deduplica(tmp_path):
    caminho = tmp_path / "vistos.json"
    itens = [_item("https://ex.com/a"), _item("https://ex.com/b")]

    vistos = carregar_vistos(caminho)
    assert vistos == {}
    novos = filtrar_novos(itens, vistos)
    assert len(novos) == 2
    salvar_vistos(caminho, registrar_e_podar(vistos, novos, HOJE))

    vistos2 = carregar_vistos(caminho)
    itens2 = itens + [_item("https://ex.com/c")]
    novos2 = filtrar_novos(itens2, vistos2)
    assert [i.url for i in novos2] == ["https://ex.com/c"]


def test_poda_entradas_com_mais_de_90_dias(tmp_path):
    antigos = {"idvelho": "2026-01-01", "idinvalido": "não-é-data"}
    atualizado = registrar_e_podar(antigos, [_item("https://ex.com/novo")], HOJE)
    assert "idvelho" not in atualizado
    assert "idinvalido" not in atualizado
    assert len(atualizado) == 1


def test_estado_corrompido_degrada_para_vazio(tmp_path):
    caminho = tmp_path / "vistos.json"
    caminho.write_text("{corrompido", encoding="utf-8")
    assert carregar_vistos(caminho) == {}
    caminho.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert carregar_vistos(caminho) == {}
