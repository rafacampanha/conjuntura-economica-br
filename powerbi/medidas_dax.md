# Medidas DAX do painel

Modelo esperado: tabela fato `Indicadores` (colunas `data`, `indicador`, `valor`), carregada do `data/conjuntura.db` ou dos CSVs, e uma tabela `Calendario` marcada como tabela de datas, ligada por `data`, com a coluna `AnoMes = FORMAT ( Calendario[Date], "YYYYMM" )`.

```dax
Valor = SUM ( Indicadores[valor] )

-- Último valor disponível (para cartões de KPI)
Valor Atual =
VAR UltimaData = CALCULATE ( MAX ( Indicadores[data] ), ALL ( Calendario ) )
RETURN CALCULATE ( [Valor], Calendario[Date] = UltimaData )

-- Variação contra o mês anterior
Var MoM % =
VAR Atual = [Valor]
VAR Anterior = CALCULATE ( [Valor], DATEADD ( Calendario[Date], -1, MONTH ) )
RETURN DIVIDE ( Atual - Anterior, Anterior )

-- Variação contra o mesmo mês do ano anterior
Var YoY % =
VAR Atual = [Valor]
VAR AnoAnterior = CALCULATE ( [Valor], SAMEPERIODLASTYEAR ( Calendario[Date] ) )
RETURN DIVIDE ( Atual - AnoAnterior, AnoAnterior )

-- Inflação acumulada em 12 meses a partir da variação mensal (%)
IPCA 12m % =
VAR Janela =
    DATESINPERIOD ( Calendario[Date], MAX ( Calendario[Date] ), -12, MONTH )
VAR Produto =
    CALCULATE (
        PRODUCTX ( VALUES ( Calendario[AnoMes] ), 1 + [Valor] / 100 ),
        Janela,
        Indicadores[indicador] = "ipca_mensal"
    )
RETURN ( Produto - 1 ) * 100

-- Juro real aproximado (Fisher)
Juro Real % =
VAR Selic = CALCULATE ( [Valor], Indicadores[indicador] = "selic" )
RETURN ( ( 1 + Selic / 100 ) / ( 1 + [IPCA 12m %] / 100 ) - 1 ) * 100

-- Texto dinâmico para títulos: "Atualizado em out/2026"
Titulo Atualizacao =
"Atualizado em " & FORMAT ( CALCULATE ( MAX ( Indicadores[data] ), ALL ( Indicadores ) ), "mmm/yyyy" )
```

**Dicas de layout usadas:** cartões de KPI no topo (valor atual + seta de variação com formatação condicional), linha do tempo com segmentação por período e tooltips com a variação MoM/YoY.
