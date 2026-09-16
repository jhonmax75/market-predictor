# Gate 8 — matriz do dataset supervisionado V1

**Status:** contrato congelado para implementacao

## Escopo

O Dataset Builder compoe resultados ja calculados pelos Gates anteriores:

```text
OHLCV canonico + features V1 + target V1
                 -> dataset supervisionado V1
```

O Builder nao recalcula features, nao recalcula target e nao aplica limpeza estatistica. O `split.py` permanece fora deste gate.

## Entrada

A entrada deve fornecer, no minimo:

### Identidade temporal

```text
asset_id
candle_open_ts
```

A chave logica da decisao e:

```text
(asset_id, decision_ts)
```

Sem criar um novo instante temporal:

```text
decision_ts = candle_open_ts
```

Uma chamada de `build_dataset()` representa exatamente um `asset_id`. Todos os registros OHLCV da chamada devem possuir o mesmo ativo; qualquer conflito produz erro explicito. Features e target sao alinhados ao ativo e ao indice temporal fornecidos pelo OHLCV.

### Features V1

```text
ret_5m
ret_15m
ret_1h
ret_3h
vol_1h
vol_6h
range_5m
range_1h
volume_rel_1h
volume_trend
```

### Target V1

```text
future_return_1h
target_direction
```

Features e target devem estar alinhados pela mesma decisao `t`. O Builder nao pode transformar `features(t) + target(t+1)` em uma linha final.

## Saida

A saida deve conter exatamente estas 14 colunas, nesta ordem:

```text
asset_id
decision_ts
ret_5m
ret_15m
ret_1h
ret_3h
vol_1h
vol_6h
range_5m
range_1h
volume_rel_1h
volume_trend
future_return_1h
target_direction
```

Cada linha representa uma decisao unica `(asset_id, decision_ts)`.

## Regras de composicao

- `decision_ts` e uma renomeacao semantica de `candle_open_ts`, sem deslocamento temporal;
- nenhuma feature e calculada novamente;
- nenhum target e calculado novamente;
- o target nao e deslocado pelo Builder;
- features futuras nao sao criadas pelo Builder;
- a intersecao valida e `OHLCV ∩ features calculaveis ∩ target disponivel`;
- linhas com qualquer feature `NaN` sao excluidas;
- linhas com target ausente sao excluidas;
- linhas com `NaN` ou `+/-inf` em features ou target sao excluidas;
- nenhuma imputacao, interpolacao, clipping ou correcao silenciosa e permitida;
- dados invalidos nao podem ser transformados artificialmente em uma classe.

O dataset final aceito nao possui `NaN` nem `+/-inf`.

## Chave e ordenacao

- chaves duplicadas `(asset_id, decision_ts)` causam erro explicito;
- `drop_duplicates()` nao e permitido;
- as entradas devem chegar em ordem canonica crescente por `asset_id` e `candle_open_ts`; entrada desordenada produz erro explicito;
- a saida preserva essa ordem por `asset_id` e `decision_ts`;
- conflitos de `asset_id` causam erro;
- timestamps incompativeis com a identidade temporal causam erro;
- a entrada nao e modificada.

A unicidade final da chave pertence ao Builder, enquanto a preservacao de duplicatas pertence ao Gate 4/DQC. Essas responsabilidades nao devem ser confundidas.

## Persistencia

As responsabilidades sao separadas:

```text
build_dataset(...)
    -> DataFrame

write_dataset(...)
    -> data/processed/dataset_v1.parquet
```

`build_dataset()` nao escreve automaticamente no filesystem. O Gate 8 somente sera considerado operacionalmente concluido quando o DataFrame validado e o artefato Parquet forem auditados.

## Matriz normativa de testes

| ID | Propriedade | Criterio |
|---|---|---|
| G8-T01 | schema final | exatamente 14 colunas na ordem normativa |
| G8-T02 | chave logica | `(asset_id, decision_ts)` existe |
| G8-T03 | unicidade | nenhuma chave duplicada |
| G8-T04 | identidade temporal | `decision_ts == candle_open_ts` |
| G8-T05 | alinhamento de features | features pertencem ao mesmo `t` |
| G8-T06 | alinhamento de target | target pertence ao mesmo `t` |
| G8-T07 | target futuro | Builder nao desloca target |
| G8-T08 | features futuras | Builder nao cria features futuras |
| G8-T09 | NaN em feature | decisao invalida e excluida |
| G8-T10 | NaN em target | decisao invalida e excluida |
| G8-T11 | infinito | nenhuma linha final contem `+/-inf` |
| G8-T12 | NaN final | nenhuma linha final contem `NaN` |
| G8-T13 | duplicidade | chave duplicada produz erro |
| G8-T14 | ordenacao | entrada nao canonica/desordenada produz erro; entrada canonica preserva ordem ascendente |
| G8-T15 | nao mutacao | entradas permanecem inalteradas |
| G8-T16 | determinismo | mesma entrada produz mesmo DataFrame |
| G8-T17 | cardinalidade | saida e a intersecao valida |
| G8-T18 | schema invalido | colunas obrigatorias ausentes produzem erro |
| G8-T19 | asset inconsistente | conflito de `asset_id` produz erro |
| G8-T20 | timestamp inconsistente | timestamps incompatíveis produzem erro |
| G8-T21 | identidade do indice OHLCV | `ohlcv.index` corresponde a `candle_open_ts` |
| G8-T22 | identidade temporal | linha de `t` contem features(t) e target(t), nao target(t+1) |

## Teste fundamental de identidade temporal

Construir uma entrada artificial em que `features(t)`, `target(t)` e `target(t+1)` tenham valores deliberadamente diferentes. A linha com `decision_ts=t` deve conter exatamente:

```text
features(t) + target(t)
```

Nunca:

```text
features(t) + target(t+1)
```

Esse teste e a principal barreira contra desalinhamento temporal silencioso.

## Limites de escopo

O Gate 8 nao implementa:

```text
modelo
treinamento
train/validation/test
split temporal
purge
embargo
backtest
metricas
scaling
feature selection
balanceamento
novas features
novo target
imputacao
correcao de OHLCV
deduplicacao silenciosa
```

## Criterio de aceite

O Gate 8 sera aprovado somente quando:

- o Builder produzir exatamente as 14 colunas normativas;
- `decision_ts` preservar `candle_open_ts`;
- features e target estiverem alinhados na mesma decisao;
- duplicidades causarem erro explicito;
- linhas invalidas forem excluidas sem imputacao;
- nenhuma linha final tiver `NaN` ou `+/-inf`;
- a entrada permanecer inalterada;
- a construcao for deterministica;
- G8-T01 a G8-T22 passarem;
- `dataset_v1.parquet` for produzido e auditado;
- a suite completa continuar passando;
- `py_compile` e `git diff --check` permanecerem limpos.
