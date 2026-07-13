# Pricer de Forwards FX + Simulador de Hedge (USD/BRL)

![Distribuição da receita com e sem hedge](assets/hist_hedged_vs_unhedged.png)

## O problema

Uma exportadora brasileira vai receber **USD 1 milhão em 90 dias úteis**. Se o dólar cair até lá, a receita em reais encolhe — e a empresa não controla o câmbio. Este projeto precifica o forward de USD/BRL, marca o contrato a mercado ao longo da vida e quantifica, via Monte Carlo, quanto risco o hedge elimina.

## O que o projeto faz

- **Precifica forwards** via paridade coberta de juros com convenção brasileira (base 252 para o CDI)
- **Marca o contrato a mercado (MTM)** em qualquer data entre o fechamento e o vencimento
- **Simula 20.000 trajetórias** do USD/BRL por movimento browniano geométrico
- **Compara a receita com e sem hedge** — total, parcial (0%–100%) e **em camadas** (1/3 da exposição travado por mês, como tesourarias fazem na prática)
- Testes em `pytest` cobrindo preço, MTM e propriedades do hedge

## Resultado-chave

| Estratégia | Receita média | Desvio-padrão |
|---|---|---|
| Sem hedge | R$ 5,00 mi | **R$ 446 mil** |
| Hedge em camadas (1/3 ao mês) | R$ 5,09 mi | R$ 164 mil |
| Hedge 100% no dia 0 | R$ 5,12 mi | **R$ 0** |

O hedge de 100% **eliminou toda a volatilidade da receita** — e ainda elevou a média, porque o diferencial de juros BRL×USD faz o dólar a termo negociar com prêmio de 2,3% sobre o spot: no Brasil, o exportador **é pago para se proteger**. O hedge em camadas eliminou 63% da volatilidade mantendo flexibilidade.

<p>
  <img src="assets/pnl_by_hedge_ratio.png" width="49%" alt="Receita por hedge ratio">
  <img src="assets/mtm_evolution.png" width="49%" alt="Evolução do MTM do forward">
</p>

## Como rodar

```bash
pip install -r requirements.txt
pytest tests/                          # roda os testes
jupyter notebook notebooks/demo.ipynb  # caso completo, do preço ao P&L
```

## Estrutura

```
fx-forward-hedge/
├── src/
│   ├── pricing.py   # forward_price, forward_mtm
│   ├── hedge.py     # simulação Monte Carlo, P&L hedged/unhedged, hedge em camadas
│   └── plots.py     # histograma, MTM, P&L por hedge ratio
├── notebooks/
│   └── demo.ipynb   # notebook narrativo com o caso da exportadora
└── tests/
    └── test_pricing.py
```

## Conceitos aplicados

- **Paridade coberta de juros** — o forward como preço de não-arbitragem, não como aposta (Hull, cap. 5)
- **Marcação a mercado** — valor presente da diferença entre forward contratado e vigente (Hull, caps. 2–3)
- **Movimento browniano geométrico** — simulação do câmbio com drift zero (martingale)
- **Hedge ratio** — trade-off linear entre incerteza e travamento (Hull, cap. 6)
- **Hedge em camadas e basis risk** — prática de tesouraria e os riscos residuais que o modelo idealiza

## Próximos passos

- Cotações reais de USD/BRL e DI via API do Banco Central (SGS)
- NDF com ajuste financeiro em BRL, como o mercado brasileiro de fato opera
