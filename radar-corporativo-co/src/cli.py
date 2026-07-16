"""Interface de linha de comando do Radar Corporativo Centro-Oeste."""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from .config import CAMINHO_CONFIG_PADRAO, RAIZ_PROJETO, carregar_config
from .fetchers.http import criar_sessao
from .fetchers.rss import checar_fonte
from .pipeline import CAMINHO_VISTOS_PADRAO, FONTES_VALIDAS, executar


def _parse_data(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"data inválida: {valor!r} (use AAAA-MM-DD)") from exc


def _parse_fontes(valor: str) -> tuple[str, ...]:
    fontes = tuple(f.strip() for f in valor.split(",") if f.strip())
    invalidas = [f for f in fontes if f not in FONTES_VALIDAS]
    if invalidas or not fontes:
        raise argparse.ArgumentTypeError(
            f"fontes inválidas: {invalidas} (opções: {', '.join(FONTES_VALIDAS)})")
    return fontes


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Gera a edição semanal do Radar Corporativo Centro-Oeste "
                    "(GO, DF, MT, MS) em HTML e Markdown.")
    parser.add_argument("--inicio", type=_parse_data,
                        help="início da janela (AAAA-MM-DD); padrão: 7 dias atrás")
    parser.add_argument("--fim", type=_parse_data,
                        help="fim da janela (AAAA-MM-DD); padrão: hoje")
    parser.add_argument("--fontes", type=_parse_fontes, default=FONTES_VALIDAS,
                        help="subconjunto de fontes, separado por vírgula: rss,pncp,qd")
    parser.add_argument("--ignorar-dedup", action="store_true",
                        help="não consulta nem grava data/vistos.json")
    parser.add_argument("--sem-licitacoes", action="store_true",
                        help="gera a edição sem o anexo de licitações do PNCP")
    parser.add_argument("--saida", type=Path, default=RAIZ_PROJETO / "output",
                        help="diretório de saída (padrão: output/)")
    parser.add_argument("--config", type=Path, default=CAMINHO_CONFIG_PADRAO,
                        help="caminho do fontes.yaml")
    parser.add_argument("--checar-fontes", action="store_true",
                        help="só valida os feeds RSS configurados e sai")
    return parser


def _checar_fontes(cfg) -> int:
    sessao = criar_sessao()
    falhas = 0
    for fonte in cfg.rss:
        ok, mensagem = checar_fonte(sessao, fonte)
        status = "OK   " if ok else "FALHA"
        print(f"{status} {fonte.nome}: {mensagem}")
        falhas += 0 if ok else 1
    print(f"\n{len(cfg.rss) - falhas}/{len(cfg.rss)} feeds respondendo.")
    return 1 if falhas == len(cfg.rss) else 0


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    cfg = carregar_config(args.config)

    if args.checar_fontes:
        return _checar_fontes(cfg)

    fim = args.fim or date.today()
    inicio = args.inicio or fim - timedelta(days=7)
    if inicio > fim:
        print("--inicio não pode ser depois de --fim", file=sys.stderr)
        return 2

    return executar(
        cfg, inicio, fim,
        fontes=args.fontes,
        usar_dedup=not args.ignorar_dedup,
        incluir_licitacoes=not args.sem_licitacoes,
        diretorio_saida=args.saida,
        caminho_vistos=CAMINHO_VISTOS_PADRAO,
    )
