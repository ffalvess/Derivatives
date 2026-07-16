from datetime import date

from src.models import Item
from src.render import montar_edicao, renderizar

INICIO, FIM = date(2026, 7, 9), date(2026, 7, 16)
ESTADOS = ("GO", "DF", "MT", "MS")


def _itens():
    return [
        Item(secao="noticias", uf="GO", titulo="Frigorífico amplia exportação <b>à China</b>",
             url="https://ex.com/frigorifico", resumo="Planta em Rio Verde",
             fonte="G1 Goiás", publicado_em=date(2026, 7, 14),
             extra={"internacional": True}),
        Item(secao="noticias", uf="MT", titulo="Cooperativa de Sorriso investe em armazéns",
             url="https://ex.com/cooperativa", resumo="Capacidade dobra",
             fonte="Canal Rural", publicado_em=date(2026, 7, 13),
             extra={"internacional": False}),
        Item(secao="diarios", uf="MT", titulo="Diário Oficial de Sorriso — 14/07/2026",
             url="https://qd.org/sorriso", resumo="Recuperação judicial deferida...",
             fonte="Querido Diário — Sorriso", publicado_em=date(2026, 7, 14)),
        Item(secao="licitacoes", uf="GO", titulo="Pregão Eletrônico: máquinas agrícolas",
             url="https://pncp.gov.br/app/editais/1/2026/45", resumo="",
             fonte="PNCP", publicado_em=date(2026, 7, 13),
             extra={"valor": 1250000.5, "municipio": "Goiânia"}),
    ]


def test_montar_edicao_separa_secoes():
    edicao = montar_edicao(_itens(), ESTADOS, INICIO, FIM)
    assert edicao.codigo == "2026-S29"
    assert [i.url for i in edicao.radar_internacional] == ["https://ex.com/frigorifico"]
    # a notícia internacional não se repete no bloco do estado
    assert "GO" not in edicao.por_uf
    assert [i.url for i in edicao.por_uf["MT"]["noticias"]] == ["https://ex.com/cooperativa"]
    assert len(edicao.por_uf["MT"]["diarios"]) == 1
    assert list(edicao.licitacoes_por_uf) == ["GO"]


def test_renderiza_html_e_markdown(tmp_path):
    edicao = montar_edicao(_itens(), ESTADOS, INICIO, FIM,
                           fontes_com_erro=["Exame"])
    gerados = renderizar(edicao, tmp_path)
    html = (tmp_path / "edicao-2026-S29.html").read_text(encoding="utf-8")
    md = (tmp_path / "edicao-2026-S29.md").read_text(encoding="utf-8")
    assert len(gerados) == 2

    assert "Radar Internacional" in html
    assert "Mato Grosso" in html
    assert "Anexo — Licitações (PNCP)" in html
    assert "R$ 1.250.000,50" in html
    assert "&lt;b&gt;" in html  # título com HTML malicioso é escapado
    assert "Exame" in html      # rodapé de fontes com erro

    assert "## 🌍 Radar Internacional" in md
    assert "[Cooperativa de Sorriso investe em armazéns](https://ex.com/cooperativa)" in md
    assert "## Anexo — Licitações (PNCP)" in md
    assert "R$ 1.250.000,50" in md


def test_flag_sem_licitacoes(tmp_path):
    edicao = montar_edicao(_itens(), ESTADOS, INICIO, FIM)
    renderizar(edicao, tmp_path, incluir_licitacoes=False)
    html = (tmp_path / "edicao-2026-S29.html").read_text(encoding="utf-8")
    md = (tmp_path / "edicao-2026-S29.md").read_text(encoding="utf-8")
    assert "Anexo" not in html and "Anexo" not in md
