"""Diários oficiais municipais via API pública do Querido Diário.

Endpoint: GET {base}/gazettes com territory_ids (códigos IBGE, repetível),
querystring de busca, janela de datas e excerpts.
"""
from __future__ import annotations

from datetime import date

import requests

from ..config import ConfigQueridoDiario
from ..models import SECAO_DIARIOS, Item
from .http import get_com_retry


def buscar_querido_diario(sessao: requests.Session, cfg: ConfigQueridoDiario,
                          inicio: date, fim: date) -> list[Item]:
    itens: list[Item] = []
    for uf, territorios in cfg.territorios.items():
        params = [
            ("querystring", cfg.querystring),
            ("published_since", inicio.isoformat()),
            ("published_until", fim.isoformat()),
            ("excerpt_size", cfg.excerpt_size),
            ("number_of_excerpts", cfg.number_of_excerpts),
            ("size", cfg.size),
        ] + [("territory_ids", cod) for cod in territorios]
        resposta = get_com_retry(sessao, f"{cfg.base_url}/gazettes", params=params)
        try:
            corpo = resposta.json() or {}
        except ValueError as exc:
            inicio_corpo = resposta.content[:120].decode("utf-8", errors="replace")
            raise requests.RequestException(
                f"resposta de {cfg.base_url}/gazettes não é JSON "
                f"(confira o base_url na config): {inicio_corpo!r}"
            ) from exc
        for gazeta in corpo.get("gazettes") or []:
            url = gazeta.get("url") or gazeta.get("txt_url") or ""
            if not url:
                continue
            data_pub = gazeta.get("date") or ""
            try:
                publicado = date.fromisoformat(data_pub[:10])
            except ValueError:
                publicado = fim
            municipio = gazeta.get("territory_name") or "município"
            excerpts = gazeta.get("excerpts") or []
            itens.append(Item(
                secao=SECAO_DIARIOS,
                uf=uf,
                titulo=f"Diário Oficial de {municipio} — {publicado.strftime('%d/%m/%Y')}",
                url=url,
                resumo=" [...] ".join(excerpts)[:600],
                fonte=f"Querido Diário — {municipio}",
                publicado_em=publicado,
                extra={"territory_id": gazeta.get("territory_id"),
                       "edicao_extra": gazeta.get("is_extra_edition")},
            ))
    return itens
