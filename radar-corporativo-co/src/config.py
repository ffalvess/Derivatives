"""Carrega e valida ``config/fontes.yaml`` em dataclasses congeladas."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import UFS

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_CONFIG_PADRAO = RAIZ_PROJETO / "config" / "fontes.yaml"


@dataclass(frozen=True)
class FonteRSS:
    nome: str
    url: str
    uf: str | None = None            # None para feeds nacionais
    url_alternativa: str | None = None
    abrangencia: str = "regional"    # "regional" | "nacional"
    verificado: bool = False

    @property
    def nacional(self) -> bool:
        return self.abrangencia == "nacional"


@dataclass(frozen=True)
class ConfigFiltro:
    termos_internacionais: tuple[str, ...]
    termos_corporativos: tuple[str, ...]


@dataclass(frozen=True)
class ConfigPNCP:
    base_url: str
    modalidades: tuple[int, ...]
    tamanho_pagina: int = 50
    max_paginas_por_uf: int = 4
    valor_minimo: float = 0.0


@dataclass(frozen=True)
class ConfigQueridoDiario:
    base_url: str
    territorios: dict[str, tuple[int, ...]]   # UF -> códigos IBGE municipais
    querystring: str
    excerpt_size: int = 400
    number_of_excerpts: int = 2
    size: int = 30


@dataclass(frozen=True)
class Config:
    estados: tuple[str, ...]
    rss: tuple[FonteRSS, ...]
    filtro: ConfigFiltro
    cidades_uf: dict[str, tuple[str, ...]]    # UF -> termos de atribuição
    pncp: ConfigPNCP
    querido_diario: ConfigQueridoDiario


def carregar_config(caminho: Path | str = CAMINHO_CONFIG_PADRAO) -> Config:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)

    estados = tuple(bruto["estados"])
    for uf in estados:
        if uf not in UFS:
            raise ValueError(f"UF desconhecida na config: {uf!r}")

    fontes = []
    for f_rss in bruto["rss"]:
        fonte = FonteRSS(
            nome=f_rss["nome"],
            url=f_rss["url"],
            uf=f_rss.get("uf"),
            url_alternativa=f_rss.get("url_alternativa"),
            abrangencia=f_rss.get("abrangencia", "regional"),
            verificado=bool(f_rss.get("verificado", False)),
        )
        if not fonte.nacional and fonte.uf not in estados:
            raise ValueError(f"Fonte regional sem UF válida: {fonte.nome!r}")
        fontes.append(fonte)

    filtro = ConfigFiltro(
        termos_internacionais=tuple(bruto["filtro"]["termos_internacionais"]),
        termos_corporativos=tuple(bruto["filtro"]["termos_corporativos"]),
    )

    pncp = ConfigPNCP(
        base_url=bruto["pncp"]["base_url"].rstrip("/"),
        modalidades=tuple(bruto["pncp"]["modalidades"]),
        tamanho_pagina=int(bruto["pncp"].get("tamanho_pagina", 50)),
        max_paginas_por_uf=int(bruto["pncp"].get("max_paginas_por_uf", 4)),
        valor_minimo=float(bruto["pncp"].get("valor_minimo", 0)),
    )

    qd_bruto = bruto["querido_diario"]
    querido_diario = ConfigQueridoDiario(
        base_url=qd_bruto["base_url"].rstrip("/"),
        territorios={uf: tuple(cods) for uf, cods in qd_bruto["territorios"].items()},
        querystring=qd_bruto["querystring"],
        excerpt_size=int(qd_bruto.get("excerpt_size", 400)),
        number_of_excerpts=int(qd_bruto.get("number_of_excerpts", 2)),
        size=int(qd_bruto.get("size", 30)),
    )

    return Config(
        estados=estados,
        rss=tuple(fontes),
        filtro=filtro,
        cidades_uf={uf: tuple(termos) for uf, termos in bruto["cidades_uf"].items()},
        pncp=pncp,
        querido_diario=querido_diario,
    )
