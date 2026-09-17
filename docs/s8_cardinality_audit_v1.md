# Auditoria quantitativa da composicao S8

## Amostra

Entrada utilizada:

```text
data/processed/bybit/BTCUSDT/5m/20260916T002539Z/candles.csv
```

## Contagens observadas

```text
RAW_CANDLES       = 85
NORMALIZED        = 85
FEATURE_ROWS      = 85
FEATURE_VALID     = 13
TARGET_ROWS       = 73
TARGET_VALID      = 73
INTERSECTION      = 1
BUILDER_OUTPUT    = 1
```

## Explicacao da cardinalidade

As features V1 possuem warm-up determinado pela maior janela causal. O primeiro indice plenamente calculavel e `72`, portanto, nesta serie de 85 candles:

```text
indices de features validas = 72 ... 84
quantidade                   = 13
```

O target exige o horizonte posicional `t+12`. Para 85 candles, os indices validos sao:

```text
indices de target validos = 0 ... 72
quantidade                = 73
```

A intersecao e:

```text
features validas: 72 ... 84
targets validos:  0  ... 72
intersecao:       72
```

Logo:

```text
85 candles
  -> 13 linhas com todas as features calculaveis
  -> 73 linhas com target disponivel
  -> 1 linha na intersecao
```

A cardinalidade final de uma linha e uma propriedade da amostra curta, nao uma regra geral do Builder.

## Conclusao

A reducao `85 -> 73 -> 1` esta explicada pelo warm-up das features e pelo horizonte do target. Nao houve descarte adicional por preco invalido, NaN ou infinito nesta composicao real.
