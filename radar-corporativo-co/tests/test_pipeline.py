"""Teste ponta-a-ponta: CLI -> pipeline -> edição em disco, com HTTP falso."""
import json
from datetime import date

import pytest

from src import cli
from src.config import carregar_config
from src.pipeline import executar
from tests.conftest import RespostaFalsa, SessaoFalsa

INICIO, FIM = date(2026, 7, 9), date(2026, 7, 16)


@pytest.fixture
def sessao(fixtures_dir):
    xml = (fixtures_dir / "g1_goias.xml").read_bytes()
    pncp = json.loads((fixtures_dir / "pncp_publicacao.json").read_text())
    qd = json.loads((fixtures_dir / "qd_gazettes.json").read_text())
    return SessaoFalsa({
        "https://g1.globo.com/rss/g1/goias/": RespostaFalsa(conteudo=xml),
        "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao":
            RespostaFalsa(json_data=pncp),
        "https://queridodiario.ok.org.br/api/gazettes": RespostaFalsa(json_data=qd),
        # demais feeds da config caem em ConnectionError -> rodapé de erros
    })


def test_edicao_completa_ponta_a_ponta(tmp_path, sessao):
    cfg = carregar_config()
    codigo = executar(cfg, INICIO, FIM, diretorio_saida=tmp_path,
                      caminho_vistos=tmp_path / "vistos.json", sessao=sessao)
    assert codigo == 0

    html = (tmp_path / "edicao-2026-S29.html").read_text(encoding="utf-8")
    md = (tmp_path / "edicao-2026-S29.md").read_text(encoding="utf-8")

    # notícia com "exportações à China" vira destaque do Radar Internacional
    assert "Radar Internacional" in html
    assert "Frigorífico anuncia expansão e 500 empregos em Rio Verde" in html
    # notícia cultural foi filtrada
    assert "Festival de música" not in html
    # diários do Querido Diário no bloco de MT
    assert "Diário Oficial de Sorriso" in html
    # licitação do PNCP no anexo segregado
    assert "Anexo — Licitações (PNCP)" in html
    assert "R$ 1.250.000,50" in html
    # feeds não alcançáveis aparecem no rodapé
    assert "Fontes indisponíveis" in html and "Exame" in html
    assert "## Anexo — Licitações (PNCP)" in md


def test_dedup_encolhe_segunda_edicao(tmp_path, sessao):
    cfg = carregar_config()
    vistos = tmp_path / "vistos.json"
    executar(cfg, INICIO, FIM, diretorio_saida=tmp_path / "e1",
             caminho_vistos=vistos, sessao=sessao)
    executar(cfg, INICIO, FIM, diretorio_saida=tmp_path / "e2",
             caminho_vistos=vistos, sessao=sessao)
    primeira = (tmp_path / "e1" / "edicao-2026-S29.html").read_text(encoding="utf-8")
    segunda = (tmp_path / "e2" / "edicao-2026-S29.html").read_text(encoding="utf-8")
    assert "Frigorífico anuncia expansão" in primeira
    assert "Frigorífico anuncia expansão" not in segunda


def test_todas_as_fontes_falhando_retorna_1(tmp_path):
    cfg = carregar_config()
    sessao_morta = SessaoFalsa({})
    codigo = executar(cfg, INICIO, FIM, diretorio_saida=tmp_path,
                      caminho_vistos=tmp_path / "vistos.json", sessao=sessao_morta)
    assert codigo == 1
    assert not list(tmp_path.glob("edicao-*"))


def test_cli_com_flags(tmp_path, sessao, monkeypatch, capsys):
    monkeypatch.setattr("src.pipeline.criar_sessao", lambda: sessao)
    codigo = cli.main([
        "--inicio", "2026-07-09", "--fim", "2026-07-16",
        "--saida", str(tmp_path), "--ignorar-dedup", "--sem-licitacoes",
    ])
    assert codigo == 0
    html = (tmp_path / "edicao-2026-S29.html").read_text(encoding="utf-8")
    assert "Anexo" not in html
    assert str(tmp_path / "edicao-2026-S29.html") in capsys.readouterr().out


def test_cli_janela_invertida_retorna_2(tmp_path):
    codigo = cli.main(["--inicio", "2026-07-20", "--fim", "2026-07-16",
                       "--saida", str(tmp_path)])
    assert codigo == 2


def test_cli_checar_fontes(sessao, monkeypatch, capsys):
    monkeypatch.setattr("src.cli.criar_sessao", lambda: sessao)
    codigo = cli.main(["--checar-fontes"])
    saida = capsys.readouterr().out
    assert codigo == 0  # ao menos o G1 Goiás responde
    assert "OK    G1 Goiás" in saida
    assert "FALHA Exame" in saida
