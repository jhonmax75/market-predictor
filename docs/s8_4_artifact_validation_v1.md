# S8.4 â€” Read-back e validacao do artefato reconciliado

**Data:** 2026-09-17
**Estado:** PASS

## Artefato novo

```text
data/processed/reconciled_v1/dataset_v1.parquet
```

O arquivo foi produzido em S8.3 somente depois de:

- confirmar que o destino nao existia;
- compor o dataset em memoria;
- validar schema, temporalidade e integridade;
- confirmar o caminho de saida autorizado.

## Resultado do read-back

```text
linhas = 1
colunas = 17
```

Schema validado na ordem normativa:

```text
asset_id
candle_open_ts
candle_close_ts
decision_ts
target_ts
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

## Validacoes aprovadas

```text
SCHEMA_OK          PASS
CARDINALIDADE_OK   PASS
TIMESTAMPS_UTC     PASS
CADEIA_TEMPORAL    PASS
ORDENACAO_TEMPORAL PASS
UNICIDADE          PASS
AUSENCIA_NAN       PASS
AUSENCIA_INF       PASS
NUMERIC_DTYPES     PASS
TARGET_TYPE        PASS
TARGET_VALUES      PASS
READBACK_OK        PASS
```

As relacoes temporais verificadas foram:

```text
candle_close_ts - candle_open_ts == 5min
decision_ts == candle_close_ts
target_ts - decision_ts == 1h
target_ts > decision_ts
```

A chave `(asset_id, decision_ts)` e unica e `target_direction` pertence a `{0, 1}`.

## Preservacao do legado

O artefato antigo permanece em:

```text
data/processed/dataset_v1.parquet
```

SHA-256 verificado antes e depois da regeneracao:

```text
b1d5cab86e3d4a18a7bc24583b664ed006e1d9c02ef48bf6a31ff0eac3fccf88
```

Resultado:

```text
LEGADO_PRESERVADO PASS
```

O Parquet antigo nao foi sobrescrito. Ele continua sendo a evidencia local pre-reconciliacao, enquanto o novo arquivo representa o schema temporal reconciliado.

## Limites da validacao

Este read-back valida o artefato fisico, schema, tipos, invariantes temporais, integridade basica e preservacao do legado. Ele nao substitui:

- DQC temporal completo;
- auditoria de proveniencia automatica;
- split temporal;
- purge;
- embargo;
- modelagem ou backtest.

## Estado

```text
S8.3 regeneracao controlada â€” PASS
S8.4 read-back do artefato â€” PASS
Gate 9 â€” ainda bloqueado
```
