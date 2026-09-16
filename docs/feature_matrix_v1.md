# Matriz de features causais V1

Todas as features usam somente dados disponiveis ate `t`, isto e, `D_{<=t}`. O historico insuficiente permanece como `NaN`; nao ha `fillna`, interpolacao, `ffill` ou `bfill`.

| Feature | Formula | Janela | Unidade | Historico minimo |
|---|---|---:|---|---:|
| `ret_5m` | `log(close_t / close_{t-1})` | 1 retorno | log-retorno | 2 candles |
| `ret_15m` | `log(close_t / close_{t-3})` | 3 retornos | log-retorno | 4 candles |
| `ret_1h` | `log(close_t / close_{t-12})` | 12 retornos | log-retorno | 13 candles |
| `ret_3h` | `log(close_t / close_{t-36})` | 36 retornos | log-retorno | 37 candles |
| `vol_1h` | `std(ddof=1)` dos log-retornos de 1 candle | 12 retornos terminando em `t` | desvio-padrao de log-retorno | 13 candles |
| `vol_6h` | `std(ddof=1)` dos log-retornos de 1 candle | 72 retornos terminando em `t` | desvio-padrao de log-retorno | 73 candles |
| `range_5m` | `(high_t - low_t) / close_t` | candle `t` | razao | 1 candle |
| `range_1h` | `(max(high_{t-11:t}) - min(low_{t-11:t})) / close_t` | 12 candles | razao | 12 candles |
| `volume_rel_1h` | `volume_t / mean(volume_{t-12:t-1})` | referencia de 12 candles anteriores | razao | 13 candles |
| `volume_trend` | inclinacao OLS de `log1p(volume)` em `t-11:t` contra `0..11` | 12 candles | log-volume por candle | 12 candles |

A janela de `volume_rel_1h` exclui deliberadamente o volume atual do denominador: a feature compara o candle atual com o historico imediatamente anterior. A inclinacao de `volume_trend` inclui o candle atual, pois ele ja esta disponivel em `t`.

## Regras de causalidade

- nenhuma coluna futura, target ou timestamp de fechamento futuro e consultada;
- a ordem de entrada deve ser a ordem canonica crescente por `candle_open_ts`;
- o DataFrame de entrada nao e mutado;
- as features nao ordenam, deduplicam, preenchem gaps ou corrigem OHLCV;
- valores nao calculaveis por historico insuficiente permanecem `NaN`;
- valores invalidos recebidos do OHLCV propagam `NaN` nos calculos afetados, sem correcao silenciosa.
