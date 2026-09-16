# Gate 7 — matriz do target supervisionado V1

## Contrato normativo

O modulo `targets/direction.py` devera expor:

```python
def build_direction_target(dataframe: pd.DataFrame) -> pd.DataFrame:
    ...
```

### Entrada

DataFrame OHLCV canonico contendo, no minimo:

```text
asset_id
candle_open_ts
open
high
low
close
volume
```

A funcao nao deve depender das features do Gate 6 nem de colunas de target preexistentes.

### Saida

DataFrame com exatamente estas colunas:

```text
future_return_1h
target_direction
```

A saida deve manter o indice original das decisoes que possuem `t+12`. As ultimas 12 decisoes sem futuro suficiente nao aparecem na saida. O indice preservado fornece a correspondencia temporal com a decisao `t` sem adicionar colunas fora do contrato.

Os tipos esperados sao:

```text
future_return_1h: float
target_direction: integer binario em {0, 1}
```

### Formula

```text
future_return_1h(t) = log(close(t + 12) / close(t))
target_direction(t) = 1 se future_return_1h(t) > 0
                      0 caso contrario
```

O horizonte e fixado em `12` candles e o threshold em `0.0` pelo contrato V1. Esses valores nao sao parametros da funcao publica e nao podem ser substituidos silenciosamente.

### Invariantes

- usa exatamente `close(t)` e `close(t+12)`;
- nao consulta `t+1` ate `t+11` para calcular o retorno;
- nao consulta dados posteriores a `t+12`;
- nao recebe nem produz features;
- nao usa `fillna`, `ffill`, `bfill` ou `interpolate`;
- exclui decisoes sem `t+12` em vez de atribuir classe artificial;
- exige que `close(t)` e `close(t+12)` sejam finitos e estritamente positivos;
- exclui decisoes com preco invalido, sem converte-las em classe `0`;
- preserva a ordem cronologica e o indice das decisoes validas;
- nao modifica o DataFrame de entrada;
- e deterministico para a mesma entrada.

## Matriz de testes

| ID | Caso | Evidencia esperada |
|---|---|---|
| G7-T01 | horizonte exato | o valor em `t` usa `close(t+12)`, nao `t+11` nem `t+13` |
| G7-T02 | retorno positivo | retorno `> 0` e direcao `1` |
| G7-T03 | retorno negativo | retorno `< 0` e direcao `0` |
| G7-T04 | retorno zero | retorno `0` e direcao `0` |
| G7-T05 | trecho final sem futuro | ultimas 12 decisoes excluidas |
| G7-T06 | ausencia de dependencia do passado | alterar antes de `t` nao altera o target de `t` |
| G7-T07 | dependencia de `close(t)` | alterar `close(t)` altera o retorno e pode alterar o sinal |
| G7-T08 | dependencia de `close(t+12)` | alterar `close(t+12)` altera o retorno e pode alterar o sinal |
| G7-T09 | ausencia de dependencia de `t+13` | alterar somente `close(t+13)` preserva o target de `t` |
| G7-T10 | separacao de features | targets nao pertencem a `FEATURE_COLUMNS` |
| G7-T11 | nao mutacao | entrada antes e depois permanece identica |
| G7-T12 | determinismo | duas execucoes produzem frames identicos |
| G7-T13 | `close(t)` invalido | decisao de `t` excluida |
| G7-T14 | `close(t+12)` invalido | decisao de `t` excluida |
| G7-T15 | preco zero | decisao nao produz target |
| G7-T16 | preco negativo | decisao nao produz target |
| G7-T17 | preco infinito | decisao nao produz target |

Para uma entrada com 20 candles, somente os indices `0` a `7` possuem target valido. Os indices `8` a `19` devem ser excluidos, e nunca convertidos artificialmente em classe `0`.

## Tratamento normativo de precos invalidos

Para calcular `log(close(t+12) / close(t))`, ambos os precos devem ser presentes, finitos e estritamente positivos. Sao invalidos `NaN`, `+infinito`, `-infinito`, zero e valores negativos.

O Gate 7 nao corrige, substitui, interpola ou preenche precos invalidos. Quando `close(t)` ou `close(t+12)` for invalido, a decisao `t` e excluida da saida supervisionada. Preco invalido nunca pode ser convertido em `target_direction = 0`.

A deteccao primaria pertence ao DQC; esta verificacao no Gate 7 e uma barreira de seguranca contra targets matematicamente invalidos.

## Teste central de dependencia

Para uma decisao `t`, os testes devem demonstrar simultaneamente:

```text
output(t) = f(close(t), close(t+12))
output(t) nao depende de close(t+1 ... t+11)
output(t) nao depende de close(t+13 ...)
```

A implementacao do Gate 7 deve permanecer restrita a `targets/direction.py` e `tests/targets/test_direction.py`. Nao entram neste gate features novas, split, purge, embargo, modelo, previsao, backtest ou metricas.
