"""Gera os gráficos do README a partir dos CSVs em data/."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .indicadores import painel_mensal

RAIZ = Path(__file__).resolve().parents[1]


def carregar(data_dir: Path = RAIZ / "data") -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p, parse_dates=["data"]) for p in data_dir.glob("*.csv") if p.stem != "painel_mensal"}


def plotar(painel: pd.DataFrame, destino: Path = RAIZ / "img") -> list[Path]:
    destino.mkdir(exist_ok=True)
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
    arquivos = []

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(painel["data"], painel["selic"], label="Selic (% a.a.)", color="#1f4e79")
    ax.plot(painel["data"], painel["ipca_12m"], label="IPCA 12m (%)", color="#c0504d")
    ax.plot(painel["data"], painel["juro_real_aprox"], label="Juro real aprox. (%)", color="#7f7f7f", ls="--")
    ax.set_title("Política monetária x inflação")
    ax.legend(frameon=False)
    arquivos.append(destino / "selic_ipca.png")
    fig.tight_layout(); fig.savefig(arquivos[-1], dpi=150); plt.close(fig)

    if "pim_var_anual" in painel:
        fig, ax = plt.subplots(figsize=(9, 4))
        dados = painel.dropna(subset=["pim_var_anual"])
        cores = ["#2e7d32" if v >= 0 else "#c62828" for v in dados["pim_var_anual"]]
        ax.bar(dados["data"], dados["pim_var_anual"], width=25, color=cores)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title("Produção industrial (PIM-PF) - variação contra o mesmo mês do ano anterior (%)")
        arquivos.append(destino / "producao_industrial.png")
        fig.tight_layout(); fig.savefig(arquivos[-1], dpi=150); plt.close(fig)
    return arquivos


if __name__ == "__main__":
    painel = painel_mensal(carregar())
    painel.to_csv(RAIZ / "data" / "painel_mensal.csv", index=False)
    for a in plotar(painel):
        print("gerado:", a)
