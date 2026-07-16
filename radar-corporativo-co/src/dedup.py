"""Deduplicação entre edições via ``data/vistos.json`` ({sha1(url): "YYYY-MM-DD"})."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Item

DIAS_RETENCAO = 90


def carregar_vistos(caminho: Path) -> dict[str, str]:
    """Estado ausente ou corrompido degrada para vazio (nunca derruba a edição)."""
    try:
        with open(caminho, encoding="utf-8") as f:
            bruto = json.load(f)
        return {str(k): str(v) for k, v in bruto.items()}
    except (OSError, json.JSONDecodeError, AttributeError, ValueError):
        return {}


def filtrar_novos(itens: list[Item], vistos: dict[str, str]) -> list[Item]:
    return [item for item in itens if item.id not in vistos]


def registrar_e_podar(vistos: dict[str, str], itens: list[Item],
                      hoje: date) -> dict[str, str]:
    """Adiciona os itens da edição e poda entradas com mais de 90 dias."""
    atualizado = dict(vistos)
    for item in itens:
        atualizado[item.id] = hoje.isoformat()
    limite = hoje - timedelta(days=DIAS_RETENCAO)
    podado = {}
    for id_item, data_str in atualizado.items():
        try:
            recente = date.fromisoformat(data_str) >= limite
        except ValueError:
            recente = False
        if recente:
            podado[id_item] = data_str
    return podado


def salvar_vistos(caminho: Path, vistos: dict[str, str]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(vistos, f, indent=1, sort_keys=True)
