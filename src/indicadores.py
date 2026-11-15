"""Cálculos usados no painel: acumulado 12 meses, variações e médias mensais."""
from __future__ import annotations

import pandas as pd


def mensalizar(df: pd.DataFrame, como: str = "mean") -> pd.DataFrame:
    """Converte série diária (Selic, dólar) em mensal (média ou último valor do mês)."""
    s = df.set_index("data")["valor"].resample("MS")
    s = s.last() if como == "last" else s.mean()
    return s.dropna().reset_index()


def acumulado_12m(variacao_mensal_pct: pd.Series) -> pd.Series:
    """Inflação acumulada em 12 meses a partir da variação mensal em %.

    (1 + v1/100) * ... * (1 + v12/100) - 1, em %.
    """
    fatores = 1 + variacao_mensal_pct / 100
    return (fatores.rolling(12).apply(lambda x: x.prod(), raw=True) - 1) * 100


def variacao_pct(serie: pd.Series, periodos: int = 1) -> pd.Series:
    """Variação % contra `periodos` atrás (1 = MoM, 12 = YoY em série mensal)."""
    return serie.pct_change(periods=periodos) * 100


def painel_mensal(series: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Junta tudo numa tabela mensal única (uma linha por mês)."""
    ipca = series["ipca_mensal"].set_index("data")["valor"]
    out = pd.DataFrame({"ipca_mensal": ipca, "ipca_12m": acumulado_12m(ipca)})
    if "inpc_mensal" in series:
        inpc = series["inpc_mensal"].set_index("data")["valor"]
        out["inpc_mensal"] = inpc
        out["inpc_12m"] = acumulado_12m(inpc)
    out["selic"] = mensalizar(series["selic"], "last").set_index("data")["valor"]
    if "dolar_ptax_venda" in series:
        out["dolar_medio"] = mensalizar(series["dolar_ptax_venda"]).set_index("data")["valor"]
    if "pim_pf" in series:
        pim = series["pim_pf"].set_index("data")["valor"]
        out["pim_indice"] = pim
        out["pim_var_anual"] = variacao_pct(pim, 12)
    if "ibc_br" in series:
        out["ibc_br"] = series["ibc_br"].set_index("data")["valor"]
    out["juro_real_aprox"] = ((1 + out["selic"] / 100) / (1 + out["ipca_12m"] / 100) - 1) * 100
    out.index.name = "data"
    return out.reset_index()
