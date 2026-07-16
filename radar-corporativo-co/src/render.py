"""Renderiza a edição (HTML + Markdown) a partir dos itens filtrados."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .config import RAIZ_PROJETO
from .models import (SECAO_DIARIOS, SECAO_LICITACOES, SECAO_NOTICIAS,
                     UF_BRASIL, Item)

DIRETORIO_TEMPLATES = RAIZ_PROJETO / "templates"

NOMES_UF = {
    "GO": "Goiás",
    "DF": "Distrito Federal",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    UF_BRASIL: "Brasil",
}


@dataclass
class Edicao:
    codigo: str                      # ex.: "2026-S29"
    inicio: date
    fim: date
    radar_internacional: list[Item]  # destaques (todas as UFs + BR)
    por_uf: dict[str, dict]          # UF -> {"nome": ..., "noticias": [...], "diarios": [...]}
    licitacoes_por_uf: dict[str, list[Item]]  # anexo segregado
    fontes_com_erro: list[str]


def _ordenar(itens: list[Item]) -> list[Item]:
    return sorted(itens, key=lambda i: i.publicado_em, reverse=True)


def montar_edicao(itens: list[Item], estados: tuple[str, ...],
                  inicio: date, fim: date,
                  fontes_com_erro: list[str] | None = None) -> Edicao:
    ano, semana, _ = fim.isocalendar()
    radar = _ordenar([i for i in itens if i.secao == SECAO_NOTICIAS and i.internacional])

    por_uf: dict[str, dict] = {}
    for uf in estados:
        noticias = _ordenar([i for i in itens
                             if i.secao == SECAO_NOTICIAS and i.uf == uf
                             and not i.internacional])
        diarios = _ordenar([i for i in itens
                            if i.secao == SECAO_DIARIOS and i.uf == uf])
        if noticias or diarios:
            por_uf[uf] = {"nome": NOMES_UF[uf], "noticias": noticias, "diarios": diarios}

    licitacoes = {uf: _ordenar([i for i in itens
                                if i.secao == SECAO_LICITACOES and i.uf == uf])
                  for uf in estados}
    licitacoes = {uf: lista for uf, lista in licitacoes.items() if lista}

    return Edicao(
        codigo=f"{ano}-S{semana:02d}",
        inicio=inicio,
        fim=fim,
        radar_internacional=radar,
        por_uf=por_uf,
        licitacoes_por_uf=licitacoes,
        fontes_com_erro=fontes_com_erro or [],
    )


def _ambiente() -> Environment:
    ambiente = Environment(
        loader=FileSystemLoader(DIRETORIO_TEMPLATES),
        autoescape=lambda nome: bool(nome) and nome.endswith("html.j2"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    ambiente.filters["data_br"] = lambda d: d.strftime("%d/%m/%Y")
    ambiente.filters["moeda_br"] = _moeda_br
    ambiente.filters["nome_uf"] = lambda uf: NOMES_UF.get(uf, uf)
    return ambiente


def _moeda_br(valor) -> str:
    if valor in (None, ""):
        return "valor não informado"
    inteiro = f"{float(valor):,.2f}"
    return "R$ " + inteiro.replace(",", "_").replace(".", ",").replace("_", ".")


def renderizar(edicao: Edicao, diretorio_saida: Path,
               incluir_licitacoes: bool = True) -> list[Path]:
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    ambiente = _ambiente()
    contexto = {"edicao": edicao, "incluir_licitacoes": incluir_licitacoes}

    gerados = []
    for template, extensao in (("edicao.html.j2", "html"), ("edicao.md.j2", "md")):
        conteudo = ambiente.get_template(template).render(**contexto)
        caminho = diretorio_saida / f"edicao-{edicao.codigo}.{extensao}"
        caminho.write_text(conteudo, encoding="utf-8")
        gerados.append(caminho)
    return gerados
