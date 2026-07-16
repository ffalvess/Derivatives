"""Modelo comum de item da newsletter.

Todo fetcher devolve ``list[Item]``; filtro, dedup e render só conhecem ``Item``.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

SECAO_NOTICIAS = "noticias"
SECAO_LICITACOES = "licitacoes"
SECAO_DIARIOS = "diarios"

UFS = ("GO", "DF", "MT", "MS")
UF_BRASIL = "BR"  # itens nacionais sem UF atribuída, mas com foco internacional


def item_id(url: str) -> str:
    """Identificador estável do item (sha1 da URL)."""
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()


@dataclass
class Item:
    secao: str            # noticias | licitacoes | diarios
    uf: str               # GO/DF/MT/MS ou BR
    titulo: str
    url: str
    resumo: str
    fonte: str            # ex.: "G1 Goiás", "PNCP", "Querido Diário — Goiânia"
    publicado_em: date
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return item_id(self.url)

    @property
    def internacional(self) -> bool:
        return bool(self.extra.get("internacional"))
