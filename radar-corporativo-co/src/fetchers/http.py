"""Sessão HTTP compartilhada por todos os fetchers."""
from __future__ import annotations

import time

import requests

USER_AGENT = "radar-corporativo-co/0.1 (+https://github.com/ffalvess/Derivatives)"
TIMEOUT = 20


def criar_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers["User-Agent"] = USER_AGENT
    return sessao


def get_com_retry(sessao: requests.Session, url: str, *, params: dict | list | None = None,
                  timeout: int = TIMEOUT) -> requests.Response:
    """GET com uma única retentativa em erro de rede ou 5xx.

    Erros 4xx não são retentados: o recurso não existe ou o pedido é inválido.
    """
    ultima_excecao: Exception | None = None
    for tentativa in range(2):
        try:
            resposta = sessao.get(url, params=params, timeout=timeout)
            if resposta.status_code >= 500 and tentativa == 0:
                time.sleep(1)
                continue
            resposta.raise_for_status()
            return resposta
        except requests.HTTPError as exc:
            raise exc
        except requests.RequestException as exc:
            ultima_excecao = exc
            if tentativa == 0:
                time.sleep(1)
    raise ultima_excecao  # type: ignore[misc]
