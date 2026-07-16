from datetime import date

from src.config import FonteRSS
from src.fetchers.rss import buscar_rss, checar_fonte, limpar_html
from tests.conftest import RespostaFalsa, SessaoFalsa

JANELA = (date(2026, 7, 9), date(2026, 7, 16))


def _fonte(**kwargs):
    padrao = dict(nome="G1 Goiás", uf="GO", url="https://g1.globo.com/rss/g1/goias/")
    padrao.update(kwargs)
    return FonteRSS(**padrao)


def _sessao_com_fixture(fixtures_dir, url="https://g1.globo.com/rss/g1/goias/"):
    xml = (fixtures_dir / "g1_goias.xml").read_bytes()
    return SessaoFalsa({url: RespostaFalsa(conteudo=xml)})


def test_mapeia_entradas_da_janela(fixtures_dir):
    sessao = _sessao_com_fixture(fixtures_dir)
    itens = buscar_rss(sessao, _fonte(), *JANELA)
    titulos = [i.titulo for i in itens]
    assert "Frigorífico anuncia expansão e 500 empregos em Rio Verde" in titulos
    assert not any("antiga" in t.lower() for t in titulos)  # fora da janela

    destaque = itens[0]
    assert destaque.uf == "GO"
    assert destaque.secao == "noticias"
    assert destaque.publicado_em == date(2026, 7, 14)
    assert "<" not in destaque.resumo and "exportações" in destaque.resumo


def test_item_sem_data_recebe_fim_da_janela(fixtures_dir):
    sessao = _sessao_com_fixture(fixtures_dir)
    itens = buscar_rss(sessao, _fonte(), *JANELA)
    sem_data = [i for i in itens if "sem data" in i.titulo.lower()]
    assert sem_data and sem_data[0].publicado_em == JANELA[1]


def test_fallback_para_url_alternativa(fixtures_dir):
    xml = (fixtures_dir / "g1_goias.xml").read_bytes()
    sessao = SessaoFalsa({
        "https://g1.globo.com/rss/g1/goias/": RespostaFalsa(status=404),
        "http://g1.globo.com/dynamo/goias/rss2.xml": RespostaFalsa(conteudo=xml),
    })
    fonte = _fonte(url_alternativa="http://g1.globo.com/dynamo/goias/rss2.xml")
    itens = buscar_rss(sessao, fonte, *JANELA)
    assert itens


def test_feed_nacional_fica_sem_uf(fixtures_dir):
    xml = (fixtures_dir / "g1_goias.xml").read_bytes()
    sessao = SessaoFalsa({"https://exame.com/feed/": RespostaFalsa(conteudo=xml)})
    fonte = FonteRSS(nome="Exame", url="https://exame.com/feed/", abrangencia="nacional")
    itens = buscar_rss(sessao, fonte, *JANELA)
    assert itens and all(i.uf == "" and i.extra["nacional"] for i in itens)


def test_payload_invalido_retorna_vazio():
    sessao = SessaoFalsa({"https://g1.globo.com": RespostaFalsa(conteudo=b"<html>erro</html>")})
    assert buscar_rss(sessao, _fonte(), *JANELA) == []


def test_checar_fonte(fixtures_dir):
    ok, msg = checar_fonte(_sessao_com_fixture(fixtures_dir), _fonte())
    assert ok and "OK" in msg
    ruim, msg_ruim = checar_fonte(
        SessaoFalsa({"https://g1.globo.com": RespostaFalsa(conteudo=b"nada")}), _fonte()
    )
    assert not ruim


def test_limpar_html():
    assert limpar_html("<p>Ol&aacute; <b>mundo</b></p>") == "Olá mundo"
