"""T1 — config loader Fase B."""
import shutil

from observador.config_loader import load_evolution_config


def test_loader_eurusd_y_xauusd():
    for asset in ("EURUSD", "XAUUSD"):
        cfg = load_evolution_config(asset)
        assert cfg["version"] == "evolution_v1"
        assert cfg["vars"] == ["continuity", "pressure", "energy",
                               "volatility", "spread"]
        assert cfg["capture"]["dimensions"] == [
            "structural", "pressure", "energy", "direction", "volatility"]
        assert cfg["capture"]["asset"]  # per-asset block presente
        assert cfg["summary"]["quality_formula"] == "v1"


def test_bump_de_version_se_refleja(tmp_path):
    import observador.config_loader as cl
    src = cl._config_path()
    dst = tmp_path / "evolution_v2.yaml"
    text = open(src, encoding="utf-8").read().replace(
        "version: evolution_v1", "version: evolution_v2")
    dst.write_text(text, encoding="utf-8")
    cfg = load_evolution_config("EURUSD", path=str(dst))
    assert cfg["version"] == "evolution_v2"


def test_activo_desconocido_usa_default():
    cfg = load_evolution_config("GBPJPY")
    default = load_evolution_config("EURUSD")
    assert cfg["capture"]["asset"] == default["capture"]["asset"]
    assert cfg["capture"]["asset"]["silence_meaning"] == \
        "all_dimensions_unchanged"
