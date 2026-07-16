"""Coleta de feeds RSS/Atom (regionais e nacionais)."""
from __future__ import annotations

import html
import re
from datetime import date

import feedparser
import requests

from ..config import FonteRSS
from ..models import SECAO_NOTICIAS, Item
from .http import get_com_retry

TAMANHO_RESUMO = 300


def limpar_html(texto: str) -> str:
    """Remove tags, decodifica entidades e colapsa espaços."""
    sem_tags = re.sub(r"<[^>]+>", " ", texto or "")
    return re.sub(r"\s+", " ", html.unescape(sem_tags)).strip()


def _data_entrada(entrada) -> date | None:
    for campo in ("published_parsed", "updated_parsed"):
        st = entrada.get(campo)
        if st:
            return date(st.tm_year, st.tm_mon, st.tm_mday)
    return None


def _parse_feed(conteudo: bytes):
    parsed = feedparser.parse(conteudo)
    return parsed.entries or []


def buscar_rss(sessao: requests.Session, fonte: FonteRSS,
               inicio: date, fim: date) -> list[Item]:
    """Baixa o feed (com fallback para ``url_alternativa``) e mapeia para Itens.

    Entradas fora da janela [inicio, fim] são descartadas; entradas sem data
    são mantidas com a data final da janela (feeds nem sempre datam os itens).
    Se todas as URLs falharem por rede, o erro é propagado para o pipeline
    marcar a fonte como indisponível.
    """
    entradas = []
    ultima_excecao: requests.RequestException | None = None
    for url in filter(None, (fonte.url, fonte.url_alternativa)):
        try:
            resposta = get_com_retry(sessao, url)
            entradas = _parse_feed(resposta.content)
            ultima_excecao = None
        except requests.RequestException as exc:
            ultima_excecao = exc
            entradas = []
        if entradas:
            break
    if ultima_excecao is not None:
        raise ultima_excecao

    itens: list[Item] = []
    for entrada in entradas:
        link = (entrada.get("link") or "").strip()
        titulo = limpar_html(entrada.get("title") or "")
        if not link or not titulo:
            continue
        publicado = _data_entrada(entrada) or fim
        if not (inicio <= publicado <= fim):
            continue
        resumo = limpar_html(entrada.get("summary") or "")[:TAMANHO_RESUMO]
        itens.append(Item(
            secao=SECAO_NOTICIAS,
            uf=fonte.uf or "",
            titulo=titulo,
            url=link,
            resumo=resumo,
            fonte=fonte.nome,
            publicado_em=publicado,
            extra={"nacional": fonte.nacional},
        ))
    return itens


def checar_fonte(sessao: requests.Session, fonte: FonteRSS) -> tuple[bool, str]:
    """Valida um feed: retorna (ok, mensagem) para o modo --checar-fontes."""
    for url in filter(None, (fonte.url, fonte.url_alternativa)):
        try:
            resposta = get_com_retry(sessao, url)
        except requests.RequestException as exc:
            mensagem = f"falha em {url}: {exc}"
            continue
        entradas = _parse_feed(resposta.content)
        if entradas:
            return True, f"OK ({len(entradas)} itens) via {url}"
        mensagem = f"resposta de {url} não parece RSS/Atom"
    return False, mensagem
