"""Licitações públicas via API de consulta do PNCP (sem autenticação).

Endpoint: GET {base}/v1/contratacoes/publicacao
Parâmetros obrigatórios: dataInicial/dataFinal (yyyyMMdd), codigoModalidadeContratacao, pagina.
A modalidade é obrigatória, então iteramos sobre a lista configurada.
"""
from __future__ import annotations

from datetime import date

import requests

from ..config import ConfigPNCP
from ..models import SECAO_LICITACOES, Item
from .http import get_com_retry


def _url_edital(registro: dict) -> str:
    orgao = registro.get("orgaoEntidade") or {}
    cnpj = orgao.get("cnpj")
    ano = registro.get("anoCompra")
    sequencial = registro.get("sequencialCompra")
    if cnpj and ano and sequencial:
        return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"
    return "https://pncp.gov.br/app/editais"


def _mapear(registro: dict, uf: str) -> Item:
    orgao = registro.get("orgaoEntidade") or {}
    unidade = registro.get("unidadeOrgao") or {}
    modalidade = registro.get("modalidadeNome") or "Licitação"
    objeto = (registro.get("objetoCompra") or "").strip()
    razao_social = orgao.get("razaoSocial") or ""
    titulo = f"{modalidade}: {objeto[:120]}"
    if razao_social:
        titulo += f" — {razao_social}"
    data_pub = registro.get("dataPublicacaoPncp") or ""
    try:
        publicado = date.fromisoformat(data_pub[:10])
    except ValueError:
        publicado = date.today()
    return Item(
        secao=SECAO_LICITACOES,
        uf=uf,
        titulo=titulo,
        url=_url_edital(registro),
        resumo=objeto[:300],
        fonte="PNCP",
        publicado_em=publicado,
        extra={
            "valor": registro.get("valorTotalEstimado"),
            "orgao": razao_social,
            "municipio": unidade.get("municipioNome"),
            "modalidade": modalidade,
        },
    )


def buscar_pncp(sessao: requests.Session, cfg: ConfigPNCP, ufs: tuple[str, ...],
                inicio: date, fim: date) -> list[Item]:
    itens: list[Item] = []
    vistos: set[str] = set()
    for uf in ufs:
        for modalidade in cfg.modalidades:
            for pagina in range(1, cfg.max_paginas_por_uf + 1):
                params = {
                    "dataInicial": inicio.strftime("%Y%m%d"),
                    "dataFinal": fim.strftime("%Y%m%d"),
                    "codigoModalidadeContratacao": modalidade,
                    "uf": uf,
                    "pagina": pagina,
                    "tamanhoPagina": cfg.tamanho_pagina,
                }
                resposta = get_com_retry(
                    sessao, f"{cfg.base_url}/v1/contratacoes/publicacao", params=params
                )
                corpo = resposta.json() or {}
                registros = corpo.get("data") or []
                if not registros:
                    break
                for registro in registros:
                    valor = registro.get("valorTotalEstimado") or 0
                    if valor < cfg.valor_minimo:
                        continue
                    item = _mapear(registro, uf)
                    if item.url in vistos:
                        continue
                    vistos.add(item.url)
                    itens.append(item)
                if len(registros) < cfg.tamanho_pagina:
                    break
    return itens
