# S8 â€” Auditoria do artefato fisico antes da regeneracao

**Data:** 2026-09-17
**Estado:** auditoria concluida; regeneracao ainda nao executada

## Artefato encontrado

```text
C:\Users\JHON\market-predictor\data\processed\dataset_v1.parquet
```

O arquivo existe no filesystem, possui 8.781 bytes e foi modificado em 2026-09-16 20:21:51 UTC.

Nao foi encontrada entrada correspondente no historico Git consultado para `data/processed/dataset_v1.parquet`. O artefato e local e nao deve ser tratado como evidÃªncia versionada por commit.

## Schema armazenado

O Parquet possui uma linha e 14 colunas:

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

Tipos observados:

```text
asset_id             string
decision_ts          datetime64[us, UTC]
features             float64
target               float64/int64
```

A linha armazenada possui:

```text
asset_id = BTCUSDT
decision_ts = 2026-09-15 19:00:00 UTC
target_direction = 0
```

## Verificacao da representacao temporal S3

O artefato contem somente:

```text
decision_ts
```

Nao contem:

```text
candle_open_ts
candle_close_ts
target_ts
```

Portanto, nao e possivel verificar no proprio arquivo as invariantes S3:

```text
candle_close_ts = candle_open_ts + 5min
decision_ts = candle_close_ts
target_ts = decision_ts + 1h
```

A estrutura confirma que o arquivo foi produzido sob o contrato anterior do Gate 8, no qual `decision_ts` era derivado de `candle_open_ts`. Ele nao e um artefato produzido pelo Builder reconciliado da S4.

## Classificacao

```text
artefato existe                         SIM
schema temporal reconciliado            NAO
candle_open_ts materializado             NAO
candle_close_ts materializado            NAO
decision_ts verificavel contra close    NAO
target_ts materializado                  NAO
artefato pre-reconciliacao               SIM
regeneracao executada                    NAO
```

## Decisao operacional

O arquivo existente deve ser preservado como artefato local historico do Gate 8 anterior. Ele nao deve ser sobrescrito silenciosamente.

A regeneracao S8 sera uma operacao posterior e controlada, depois que:

1. a auditoria deste artefato for registrada;
2. a entrada canonica e a versao reconciliada do Builder estiverem confirmadas;
3. o novo caminho ou estrategia de versionamento do Parquet for definido;
4. o novo artefato puder ser distinguido do artefato pre-reconciliacao;
5. o DQC temporal aplicavel estiver decidido em S7.

## Resultado

```text
S8 pre-regeneracao â€” PASS
artefato anterior identificado â€” PASS
sem sobrescrita silenciosa â€” PASS
artefato reconciliado â€” PENDENTE
```

Nenhum dado foi alterado nesta auditoria.
