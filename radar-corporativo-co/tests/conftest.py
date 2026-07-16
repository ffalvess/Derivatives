from pathlib import Path

import pytest
import requests

FIXTURES = Path(__file__).parent / "fixtures"


class RespostaFalsa:
    def __init__(self, conteudo: bytes = b"", json_data=None, status=200, headers=None):
        self.content = conteudo
        self._json = json_data
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class SessaoFalsa:
    """Sessão que responde por URL (prefixo). Registra as chamadas feitas."""

    def __init__(self, respostas: dict):
        # respostas: prefixo de URL -> RespostaFalsa | lista de RespostaFalsa | Exception
        self.respostas = respostas
        self.chamadas = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.chamadas.append((url, params))
        for prefixo, resposta in self.respostas.items():
            if url.startswith(prefixo):
                if isinstance(resposta, list):
                    resposta = resposta.pop(0) if resposta else RespostaFalsa(status=404)
                if isinstance(resposta, Exception):
                    raise resposta
                return resposta
        raise requests.ConnectionError(f"sem resposta cadastrada para {url}")


@pytest.fixture
def fixtures_dir():
    return FIXTURES


@pytest.fixture(autouse=True)
def sem_sleep(monkeypatch):
    monkeypatch.setattr("src.fetchers.http.time.sleep", lambda _s: None)
    monkeypatch.setattr("src.fetchers.pncp.time.sleep", lambda _s: None)
