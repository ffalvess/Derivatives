from datetime import date

from src.config import ConfigFiltro
from src.filtro import Filtro, normalizar
from src.models import Item

CFG = ConfigFiltro(
    termos_internacionais=("exportação", "comércio exterior", "china",
                           "investimento estrangeiro"),
    termos_corporativos=("empresa", "falência", "agronegócio", "soja"),
)
CIDADES = {
    "GO": ("goiás", "goiânia", "rio verde"),
    "DF": ("distrito federal", "brasília"),
    "MT": ("mato grosso", "cuiabá", "sorriso", "sinop", "nova mutum",
           "lucas do rio verde"),
    "MS": ("mato grosso do sul", "campo grande", "dourados"),
}


def _noticia(titulo, resumo="", nacional=False, uf="GO"):
    return Item(secao="noticias", uf="" if nacional else uf, titulo=titulo,
                url=f"https://ex.com/{abs(hash(titulo))}", resumo=resumo,
                fonte="Teste", publicado_em=date(2026, 7, 14),
                extra={"nacional": nacional})


def _filtro():
    return Filtro(CFG, CIDADES)


def test_normalizar_remove_acentos():
    assert normalizar("FALÊNCIA às pressas") == "falencia as pressas"


def test_regional_corporativa_entra_e_cultural_sai():
    itens = _filtro().aplicar([
        _noticia("Empresa goiana amplia produção"),
        _noticia("Festival de música no parque"),
    ])
    assert [i.titulo for i in itens] == ["Empresa goiana amplia produção"]


def test_match_insensivel_a_acentos_e_caixa():
    itens = _filtro().aplicar([_noticia("Justiça decreta FALENCIA de atacadista")])
    assert len(itens) == 1


def test_termo_internacional_marca_destaque():
    itens = _filtro().aplicar([
        _noticia("Exportação de carne bate recorde"),
        _noticia("Empresa local contrata"),
    ])
    assert itens[0].internacional and not itens[1].internacional


def test_nacional_com_mencao_regional_recebe_uf():
    itens = _filtro().aplicar([
        _noticia("Empresa de Sorriso amplia esmagamento de soja", nacional=True),
    ])
    assert itens[0].uf == "MT"


def test_nacional_ms_nao_vira_mt():
    itens = _filtro().aplicar([
        _noticia("Frigorífico do Mato Grosso do Sul retoma exportação", nacional=True),
    ])
    assert itens[0].uf == "MS"


def test_lucas_do_rio_verde_nao_vira_goias():
    itens = _filtro().aplicar([
        _noticia("Agronegócio cresce em Lucas do Rio Verde", nacional=True),
    ])
    assert itens[0].uf == "MT"


def test_nacional_internacional_sem_mencao_vai_para_br():
    itens = _filtro().aplicar([
        _noticia("China amplia compras de soja do Brasil", nacional=True),
    ])
    assert itens[0].uf == "BR" and itens[0].internacional


def test_nacional_sem_mencao_e_sem_foco_internacional_e_descartado():
    itens = _filtro().aplicar([
        _noticia("Empresa paulista lança aplicativo", nacional=True),
    ])
    assert itens == []


def test_licitacoes_e_diarios_passam_direto():
    licitacao = Item(secao="licitacoes", uf="GO", titulo="Pregão qualquer",
                     url="https://pncp.gov.br/x", resumo="", fonte="PNCP",
                     publicado_em=date(2026, 7, 14))
    assert _filtro().aplicar([licitacao]) == [licitacao]


def test_palavra_inteira_nao_casa_substring():
    # "china" não deve casar dentro de "machina" nem "tarifa" dentro de "tarifaço"
    itens = _filtro().aplicar([_noticia("Deus ex machina no teatro municipal")])
    assert itens == []
