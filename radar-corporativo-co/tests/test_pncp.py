import json
from datetime import date

from src.config import ConfigPNCP
from src.fetchers.pncp import buscar_pncp
from tests.conftest import RespostaFalsa, SessaoFalsa

JANELA = (date(2026, 7, 9), date(2026, 7, 16))
CFG = ConfigPNCP(
    base_url="https://pncp.gov.br/api/consulta",
    modalidades=(6,),
    tamanho_pagina=50,
    max_paginas_por_uf=4,
    valor_minimo=500000,
)


def _sessao(fixtures_dir):
    pagina = json.loads((fixtures_dir / "pncp_publicacao.json").read_text())
    return SessaoFalsa({
        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao":
            RespostaFalsa(json_data=pagina),
    })


def test_mapeia_e_filtra_por_valor_minimo(fixtures_dir):
    sessao = _sessao(fixtures_dir)
    itens = buscar_pncp(sessao, CFG, ("GO",), *JANELA)

    # só a licitação de R$ 1,25 mi passa; a de R$ 12 mil fica abaixo do mínimo
    assert len(itens) == 1
    item = itens[0]
    assert item.secao == "licitacoes"
    assert item.uf == "GO"
    assert item.titulo.startswith("Pregão Eletrônico: Aquisição de máquinas agrícolas")
    assert "Secretaria de Estado da Agricultura de Goiás" in item.titulo
    assert item.url == "https://pncp.gov.br/app/editais/01612092000123/2026/45"
    assert item.publicado_em == date(2026, 7, 13)
    assert item.extra["valor"] == 1250000.5
    assert item.extra["municipio"] == "Goiânia"


def test_parametros_da_consulta(fixtures_dir):
    sessao = _sessao(fixtures_dir)
    buscar_pncp(sessao, CFG, ("GO",), *JANELA)
    _url, params = sessao.chamadas[0]
    assert params["dataInicial"] == "20260709"
    assert params["dataFinal"] == "20260716"
    assert params["codigoModalidadeContratacao"] == 6
    assert params["uf"] == "GO"
    assert params["pagina"] == 1


def test_paginacao_para_em_pagina_vazia(fixtures_dir):
    pagina = json.loads((fixtures_dir / "pncp_publicacao.json").read_text())
    # 50 registros na página 1 força a busca da página 2, que vem vazia
    pagina_cheia = dict(pagina, data=pagina["data"] * 25)
    sessao = SessaoFalsa({
        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao": [
            RespostaFalsa(json_data=pagina_cheia),
            RespostaFalsa(json_data={"data": []}),
        ],
    })
    buscar_pncp(sessao, CFG, ("GO",), *JANELA)
    paginas = [params["pagina"] for _u, params in sessao.chamadas]
    assert paginas == [1, 2]


def test_429_espera_e_tenta_de_novo(fixtures_dir):
    pagina = json.loads((fixtures_dir / "pncp_publicacao.json").read_text())
    sessao = SessaoFalsa({
        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao": [
            RespostaFalsa(status=429, headers={"Retry-After": "2"}),
            RespostaFalsa(json_data=pagina),
        ],
    })
    itens = buscar_pncp(sessao, CFG, ("GO",), *JANELA)
    assert len(itens) == 1  # segunda tentativa (pós rate-limit) funcionou


def test_erro_em_uma_uf_nao_descarta_as_demais(fixtures_dir):
    pagina = json.loads((fixtures_dir / "pncp_publicacao.json").read_text())
    sessao = SessaoFalsa({
        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao": [
            RespostaFalsa(json_data=pagina),      # GO ok
            RespostaFalsa(status=404),            # MT falha
        ],
    })
    itens = buscar_pncp(sessao, CFG, ("GO", "MT"), *JANELA)
    assert [i.uf for i in itens] == ["GO"]


def test_deduplica_registros_repetidos(fixtures_dir):
    pagina = json.loads((fixtures_dir / "pncp_publicacao.json").read_text())
    cfg = ConfigPNCP(base_url=CFG.base_url, modalidades=(6, 8), valor_minimo=500000)
    sessao = SessaoFalsa({
        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao":
            RespostaFalsa(json_data=pagina),
    })
    itens = buscar_pncp(sessao, cfg, ("GO",), *JANELA)
    assert len(itens) == 1  # mesmo edital retornado nas duas modalidades conta uma vez
