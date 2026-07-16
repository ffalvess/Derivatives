"""Relevância corporativa e atribuição de UF para itens de feeds nacionais.

Regras (aplicadas só à seção "noticias"; licitações e diários já chegam
pré-filtrados na fonte):

- Item que casa com ``termos_internacionais`` é marcado ``internacional`` e
  ganha destaque na seção "Radar Internacional" da edição.
- Item regional entra se casar com termos internacionais OU corporativos.
- Item de feed nacional entra se mencionar um estado/cidade-chave da região
  (recebe essa UF) ou, sem menção regional, se for internacional (vai para
  a seção "Radar Internacional — Brasil" com UF "BR"). Caso contrário, é
  descartado.

Matching por palavra inteira, sem acentos e sem diferença de caixa.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from .config import ConfigFiltro
from .models import SECAO_NOTICIAS, UF_BRASIL, Item


def normalizar(texto: str) -> str:
    """minúsculas + remoção de acentos (para matching estável)."""
    decomposto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _regex_termos(termos: tuple[str, ...]) -> re.Pattern:
    alternativas = "|".join(re.escape(normalizar(t)) for t in termos)
    return re.compile(rf"\b(?:{alternativas})\b")


class Filtro:
    def __init__(self, cfg: ConfigFiltro, cidades_uf: dict[str, tuple[str, ...]]):
        self._internacionais = _regex_termos(cfg.termos_internacionais)
        self._corporativos = _regex_termos(cfg.termos_corporativos)
        # termos mais longos primeiro: "mato grosso do sul" vence "mato grosso",
        # "lucas do rio verde" vence "rio verde"
        pares = [(normalizar(termo), uf)
                 for uf, termos in cidades_uf.items() for termo in termos]
        self._termos_uf = sorted(pares, key=lambda par: len(par[0]), reverse=True)

    def _atribuir_uf(self, texto: str) -> str | None:
        for termo, uf in self._termos_uf:
            if re.search(rf"\b{re.escape(termo)}\b", texto):
                return uf
        return None

    def aplicar(self, itens: list[Item]) -> list[Item]:
        resultado: list[Item] = []
        for item in itens:
            if item.secao != SECAO_NOTICIAS:
                resultado.append(item)
                continue

            texto = normalizar(f"{item.titulo} {item.resumo}")
            internacional = bool(self._internacionais.search(texto))
            corporativo = bool(self._corporativos.search(texto))

            if item.extra.get("nacional"):
                uf = self._atribuir_uf(texto)
                if uf is None:
                    if not internacional:
                        continue
                    uf = UF_BRASIL
                elif not (internacional or corporativo):
                    continue
                item = replace(item, uf=uf)
            elif not (internacional or corporativo):
                continue

            item.extra["internacional"] = internacional
            resultado.append(item)
        return resultado
