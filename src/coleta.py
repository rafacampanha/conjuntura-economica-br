"""Coleta de indicadores macroeconômicos em APIs públicas (BCB/SGS e IBGE/SIDRA).

Uso:
    python -m src.coleta              # baixa tudo e salva em data/
    python -m src.coleta --inicio 01/01/2020
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd
import requests

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SIDRA_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos/{periodos}/variaveis/{variavel}"

# Séries do Sistema Gerenciador de Séries Temporais (SGS) do Banco Central
SERIES_BCB = {
    "selic": 4189,            # Selic acumulada no mês, anualizada (% a.a.) - mensal
    "ipca_mensal": 433,       # IPCA - variação mensal (%)
    "inpc_mensal": 188,       # INPC - variação mensal (%)
    "dolar_ptax_venda": 1,    # Dólar comercial (venda) - diária
    "ibc_br": 24364,          # IBC-Br dessazonalizado (índice)
}

# Produção Industrial Mensal (PIM-PF) - Indústria geral, número-índice
SIDRA_PIM = {"tabela": 8888, "variavel": 12606, "classificacao": "544[129314]"}

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TIMEOUT = 60


def buscar_serie_bcb(codigo: int, inicio: str | None = None, fim: str | None = None,
                     sessao: requests.Session | None = None) -> pd.DataFrame:
    """Retorna DataFrame [data, valor] de uma série do SGS/BCB.

    `inicio`/`fim` no formato dd/mm/aaaa. Séries diárias aceitam no máximo
    10 anos por consulta, por isso o padrão é pegar desde 2015.
    """
    sessao = sessao or requests.Session()
    params = {"formato": "json", "dataInicial": inicio or "01/01/2015"}
    if fim:
        params["dataFinal"] = fim
    resp = sessao.get(BCB_URL.format(codigo=codigo), params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return normalizar_bcb(resp.json())


def normalizar_bcb(payload: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(payload)
    if df.empty:
        return pd.DataFrame(columns=["data", "valor"])
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df.dropna().sort_values("data").reset_index(drop=True)


def buscar_pim_sidra(periodos: str = "-120", sessao: requests.Session | None = None) -> pd.DataFrame:
    """Produção industrial (PIM-PF) via API de agregados do IBGE."""
    sessao = sessao or requests.Session()
    url = SIDRA_URL.format(tabela=SIDRA_PIM["tabela"], periodos=periodos, variavel=SIDRA_PIM["variavel"])
    params = {"localidades": "N1[all]", "classificacao": SIDRA_PIM["classificacao"]}
    resp = sessao.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return normalizar_sidra(resp.json())


def normalizar_sidra(payload: list[dict]) -> pd.DataFrame:
    serie = payload[0]["resultados"][0]["series"][0]["serie"]
    df = pd.DataFrame({"periodo": list(serie.keys()), "valor": list(serie.values())})
    df["data"] = pd.to_datetime(df["periodo"], format="%Y%m")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")  # "..." vira NaN
    return df[["data", "valor"]].dropna().sort_values("data").reset_index(drop=True)


def salvar(series: dict[str, pd.DataFrame], destino: Path = DATA_DIR) -> None:
    """Salva cada série em CSV e tudo junto num SQLite (fácil de ligar no Power BI)."""
    destino.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(destino / "conjuntura.db") as con:
        for nome, df in series.items():
            df.to_csv(destino / f"{nome}.csv", index=False)
            df.assign(indicador=nome).to_sql(nome, con, if_exists="replace", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", default="01/01/2015", help="data inicial dd/mm/aaaa")
    args = parser.parse_args()

    sessao = requests.Session()
    series = {}
    for nome, codigo in SERIES_BCB.items():
        print(f"BCB  {nome:<18} (SGS {codigo})")
        series[nome] = buscar_serie_bcb(codigo, inicio=args.inicio, sessao=sessao)
    print("IBGE pim_pf             (SIDRA 8888)")
    series["pim_pf"] = buscar_pim_sidra(sessao=sessao)
    salvar(series)
    print(f"OK - arquivos em {DATA_DIR}")


if __name__ == "__main__":
    main()
