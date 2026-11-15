import json
from pathlib import Path

import pandas as pd
import pytest

from src.coleta import normalizar_bcb, normalizar_sidra
from src.indicadores import acumulado_12m, mensalizar, painel_mensal, variacao_pct

FIX = Path(__file__).parent / "fixtures"


def test_normalizar_bcb_converte_datas_e_valores():
    df = normalizar_bcb([{"data": "02/01/2026", "valor": "15.00"}, {"data": "01/01/2026", "valor": "14.75"}])
    assert df["data"].iloc[0] == pd.Timestamp("2026-01-01")
    assert df["valor"].tolist() == [14.75, 15.0]


def test_normalizar_sidra_le_formato_da_api():
    payload = json.loads((FIX / "sidra_pim.json").read_text())
    df = normalizar_sidra(payload)
    assert len(df) == 2
    assert df["valor"].iloc[-1] == pytest.approx(109.08932)


def test_acumulado_12m_de_1pct_ao_mes():
    s = pd.Series([1.0] * 12)
    assert acumulado_12m(s).iloc[-1] == pytest.approx((1.01 ** 12 - 1) * 100)


def test_variacao_pct_yoy():
    s = pd.Series(range(100, 113))
    assert variacao_pct(s, 12).iloc[-1] == pytest.approx(12.0)


def test_mensalizar_last_e_mean():
    df = pd.DataFrame({"data": pd.to_datetime(["2026-01-02", "2026-01-30", "2026-02-10"]), "valor": [10, 20, 30]})
    assert mensalizar(df, "last")["valor"].tolist() == [20, 30]
    assert mensalizar(df)["valor"].tolist() == [15, 30]


def test_painel_mensal_monta_colunas():
    meses = pd.date_range("2025-01-01", periods=14, freq="MS")
    mensal = pd.DataFrame({"data": meses, "valor": 0.5})
    series = {
        "ipca_mensal": mensal, "inpc_mensal": mensal,
        "selic": pd.DataFrame({"data": meses, "valor": 15.0}),
        "dolar_ptax_venda": pd.DataFrame({"data": meses, "valor": 5.4}),
    }
    p = painel_mensal(series)
    assert {"ipca_12m", "juro_real_aprox", "dolar_medio"} <= set(p.columns)
    assert p["juro_real_aprox"].dropna().iloc[-1] == pytest.approx((1.15 / 1.005 ** 12 - 1) * 100)
