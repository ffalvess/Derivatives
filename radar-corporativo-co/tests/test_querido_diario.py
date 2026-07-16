import json
from datetime import date

from src.config import ConfigQueridoDiario
from src.fetchers.querido_diario import buscar_querido_diario
from tests.conftest import RespostaFalsa, SessaoFalsa

JANELA = (date(2026, 7, 9), date(2026, 7, 16))
CFG = ConfigQueridoDiario(
    base_url="https://queridodiario.ok.org.br/api",
    territorios={"MT": (5103403, 5107925)},
    querystring='"recuperação judicial" OR "falência"',
)


def _sessao(fixtures_dir):
    corpo = json.loads((fixtures_dir / "qd_gazettes.json").read_text())
    return SessaoFalsa({
        "https://queridodiario.ok.org.br/api/gazettes": RespostaFalsa(json_data=corpo),
    })


def test_mapeia_gazetas(fixtures_dir):
    itens = buscar_querido_diario(_sessao(fixtures_dir), CFG, *JANELA)
    assert len(itens) == 2
    sorriso = itens[0]
    assert sorriso.secao == "diarios"
    assert sorriso.uf == "MT"
    assert sorriso.titulo == "Diário Oficial de Sorriso — 14/07/2026"
    assert sorriso.fonte == "Querido Diário — Sorriso"
    assert "recuperação judicial" in sorriso.resumo
    assert " [...] " in sorriso.resumo  # excerpts concatenados
    assert sorriso.publicado_em == date(2026, 7, 14)


def test_parametros_incluem_territorios_e_janela(fixtures_dir):
    sessao = _sessao(fixtures_dir)
    buscar_querido_diario(sessao, CFG, *JANELA)
    _url, params = sessao.chamadas[0]
    pares = dict(p for p in params if p[0] != "territory_ids")
    territorios = [v for k, v in params if k == "territory_ids"]
    assert pares["published_since"] == "2026-07-09"
    assert pares["published_until"] == "2026-07-16"
    assert pares["querystring"] == CFG.querystring
    assert territorios == [5103403, 5107925]


def test_gazeta_sem_url_e_descartada(fixtures_dir):
    corpo = json.loads((fixtures_dir / "qd_gazettes.json").read_text())
    for gazeta in corpo["gazettes"]:
        gazeta["url"] = ""
        gazeta["txt_url"] = ""
    sessao = SessaoFalsa({
        "https://queridodiario.ok.org.br/api/gazettes": RespostaFalsa(json_data=corpo),
    })
    assert buscar_querido_diario(sessao, CFG, *JANELA) == []
