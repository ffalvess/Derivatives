from src.config import CAMINHO_CONFIG_PADRAO, carregar_config


def test_config_padrao_carrega():
    cfg = carregar_config(CAMINHO_CONFIG_PADRAO)
    assert cfg.estados == ("GO", "DF", "MT", "MS")
    assert len(cfg.rss) >= 10
    assert cfg.pncp.modalidades
    assert cfg.pncp.valor_minimo > 0
    assert set(cfg.querido_diario.territorios) == set(cfg.estados)
    assert set(cfg.cidades_uf) == set(cfg.estados)


def test_fontes_nacionais_sem_uf():
    cfg = carregar_config()
    nacionais = [f for f in cfg.rss if f.nacional]
    assert {f.nome for f in nacionais} >= {
        "Valor Econômico", "Exame", "Globo Rural", "Notícias Agrícolas", "Canal Rural"
    }
    assert all(f.uf is None for f in nacionais)


def test_polos_do_agro_mt_configurados():
    cfg = carregar_config()
    mt = cfg.querido_diario.territorios["MT"]
    # Sorriso, Sinop e Nova Mutum (códigos IBGE)
    assert {5107925, 5107909, 5106224} <= set(mt)
