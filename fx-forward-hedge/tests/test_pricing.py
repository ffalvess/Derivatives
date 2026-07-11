"""Testes de precificação e de sanidade do hedge."""

import numpy as np
import pytest

from src.hedge import (
    hedge_effectiveness,
    layered_hedge,
    pnl_hedged,
    pnl_unhedged,
    simulate_spot_paths,
)
from src.pricing import forward_mtm, forward_price


class TestForwardPrice:
    def test_bate_com_calculo_manual(self):
        # S=5.00, CDI 12% a.a., USD 5% a.a., 90 dias úteis:
        # F = 5.00 * (1.12)^(90/252) / (1.05)^(90/252) = 5.1170...
        expected = 5.0 * (1.12 ** (90 / 252)) / (1.05 ** (90 / 252))
        assert forward_price(5.0, 0.12, 0.05, 90) == pytest.approx(expected)

    def test_prazo_zero_retorna_spot(self):
        assert forward_price(5.0, 0.12, 0.05, 0) == pytest.approx(5.0)

    def test_juro_domestico_maior_implica_premio(self):
        # Com CDI acima da taxa americana, o forward negocia acima do spot.
        assert forward_price(5.0, 0.12, 0.05, 90) > 5.0

    def test_juros_iguais_forward_igual_spot(self):
        assert forward_price(5.0, 0.08, 0.08, 90) == pytest.approx(5.0)

    def test_spot_invalido(self):
        with pytest.raises(ValueError):
            forward_price(-1.0, 0.12, 0.05, 90)


class TestForwardMtm:
    def test_mtm_zera_no_inicio(self):
        # No fechamento, o forward de mercado é o próprio preço contratado.
        F = forward_price(5.0, 0.12, 0.05, 90)
        assert forward_mtm(F, F, 1_000_000, 0.12, 90) == pytest.approx(0.0)

    def test_converge_para_payoff_no_vencimento(self):
        # No vencimento (0 dias restantes) o forward de mercado é o spot
        # e o MTM long vale exatamente (S_T - F) * notional, sem desconto.
        F, s_T, notional = 5.10, 5.30, 1_000_000
        mtm = forward_mtm(F, s_T, notional, 0.12, 0)
        assert mtm == pytest.approx((s_T - F) * notional)

    def test_short_e_espelho_do_long(self):
        mtm_long = forward_mtm(5.10, 5.30, 1_000_000, 0.12, 45, "long")
        mtm_short = forward_mtm(5.10, 5.30, 1_000_000, 0.12, 45, "short")
        assert mtm_short == pytest.approx(-mtm_long)

    def test_desconto_reduz_valor_absoluto(self):
        # O mesmo ganho vale menos quanto mais distante o vencimento.
        perto = forward_mtm(5.10, 5.30, 1_000_000, 0.12, 5)
        longe = forward_mtm(5.10, 5.30, 1_000_000, 0.12, 200)
        assert abs(longe) < abs(perto)


class TestHedge:
    @pytest.fixture
    def paths(self):
        return simulate_spot_paths(5.0, 0.15, 90, 5_000, seed=42)

    def test_paths_comecam_no_spot(self, paths):
        assert np.allclose(paths[:, 0], 5.0)

    def test_hedge_total_elimina_incerteza(self, paths):
        revenue = pnl_hedged(paths, 1_000_000, F_contratado=5.11, hedge_ratio=1.0)
        assert np.std(revenue) == pytest.approx(0.0)
        assert np.allclose(revenue, 5.11 * 1_000_000)

    def test_hedge_zero_equivale_a_sem_hedge(self, paths):
        hedged = pnl_hedged(paths, 1_000_000, F_contratado=5.11, hedge_ratio=0.0)
        unhedged = pnl_unhedged(paths, 1_000_000)
        assert np.allclose(hedged, unhedged)

    def test_hedge_parcial_reduz_volatilidade(self, paths):
        unhedged = pnl_unhedged(paths, 1_000_000)
        hedged = pnl_hedged(paths, 1_000_000, F_contratado=5.11, hedge_ratio=0.8)
        assert np.std(hedged) < np.std(unhedged)
        # Com 80% travado, sobra ~20% da volatilidade original.
        assert np.std(hedged) == pytest.approx(0.2 * np.std(unhedged))

    def test_layered_hedge_fica_entre_extremos(self, paths):
        unhedged = pnl_unhedged(paths, 1_000_000)
        layered = layered_hedge(
            paths, 1_000_000,
            schedule=[(0, 1 / 3), (30, 1 / 3), (60, 1 / 3)],
            r_dom=0.12, r_for=0.05,
        )
        assert 0 < np.std(layered) < np.std(unhedged)

    def test_layered_hedge_rejeita_fracao_acima_de_um(self, paths):
        with pytest.raises(ValueError):
            layered_hedge(paths, 1_000_000, [(0, 0.7), (30, 0.7)], 0.12, 0.05)

    def test_hedge_effectiveness_total(self, paths):
        unhedged = pnl_unhedged(paths, 1_000_000)
        hedged = pnl_hedged(paths, 1_000_000, 5.11, 1.0)
        assert hedge_effectiveness(unhedged, hedged) == pytest.approx(1.0)
