# S8.1 — Plano de regeneracao do dataset V1

**Estado:** plano definido; nenhuma regeneracao executada

## Proveniencia disponivel

O artefato local atual e:

```text
data/processed/dataset_v1.parquet
```

Ele e pre-reconciliacao pelo schema observado: possui 14 colunas e somente `decision_ts` entre os campos temporais. Nao ha registro Git desse caminho.

O repositorio nao possui um comando oficial de construcao: `scripts/build_dataset.py` esta vazio. A proveniencia executavel atual e a composicao direta:

```text
raw candles.csv
  -> pandas.read_csv
  -> normalize_ohlcv()
  -> build_features()
  -> build_direction_target()
  -> build_dataset()
  -> write_dataset()
```

A entrada conhecida da coleta e:

```text
data/raw/bybit/BTCUSDT/5m/20260916T002539Z/candles.csv
data/raw/bybit/BTCUSDT/5m/20260916T002539Z/metadata.json
```

O metadata registra 85 linhas brutas e as politicas de nao deduplicacao, nao preenchimento e nao interpolacao.

## Decisao de preservacao

Nao sobrescrever:

```text
data/processed/dataset_v1.parquet
```

Esse arquivo sera preservado como artefato local historico pre-reconciliacao. A nova saida deve usar caminho separado:

```text
data/processed/reconciled_v1/dataset_v1.parquet
```

A separacao evita apagar evidencia e permite comparar os dois schemas. Como `data/processed/*` e ignorado pelo Git, a proveniencia deve ser registrada em metadata ou relatorio associado ao artefato.

## Pipeline controlado proposto

A regeneracao futura deve executar exatamente:

```text
raw candles.csv
  -> read raw
  -> normalize_ohlcv()
       produz candle_open_ts e candle_close_ts
  -> indexar por candle_open_ts
  -> build_features()
  -> build_direction_target()
  -> build_dataset()
       produz decision_ts = candle_close_ts
       produz target_ts = decision_ts + 1h
  -> write_dataset()
       novo caminho reconciliado
```

O Builder nao deve recalcular features ou target. O script operacional que eventualmente encapsular esse fluxo deve apenas orquestrar as funcoes ja testadas.

## Schema esperado do novo artefato

A saida reconciliada deve conter 17 colunas:

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

## Invariantes imediatas pos-geracao

Apos escrever o Parquet, ler o arquivo novamente e verificar:

```text
schema exato de 17 colunas
candle_close_ts - candle_open_ts == 5min
decision_ts == candle_close_ts
target_ts - decision_ts == 1h
target_ts > decision_ts
chave (asset_id, decision_ts) unica
sem NaN
sem +/-inf em features e target
target_direction pertence a {0, 1}
ordem temporal crescente
```

Tambem comparar:

```text
raw_rows
normalized_rows
feature_rows
candidate_target_rows
final_dataset_rows
excluded_rows
```

A expectativa para a coleta conhecida de 85 candles e:

```text
85 candles brutos
73 decisoes com horizonte t+12
menos o warm-up das features
= dataset final reconciliado
```

A quantidade final deve ser medida, nao presumida.

## Evidencia de reprodutibilidade

Registrar junto ao experimento:

- caminho da entrada raw;
- hash ou metadata da coleta;
- caminho do novo Parquet;
- commit/versao do codigo reconciliado;
- schema final;
- contagens por etapa;
- primeira e ultima `decision_ts`;
- primeira e ultima `target_ts`;
- resultado das invariantes;
- data da regeneracao.

A execucao deve ocorrer em novo caminho e falhar se o destino ja existir, evitando sobrescrita silenciosa.

## Ordem de execucao

1. confirmar este plano;
2. construir o comando de orquestracao, se necessario;
3. verificar o destino novo inexistente;
4. executar o pipeline reconciliado;
5. auditar o Parquet lido do disco;
6. registrar contagens e invariantes;
7. somente depois decidir o tratamento/versionamento do artefato antigo.

## Bloqueios preservados

S8.1 nao executa:

- DQC temporal novo;
- split;
- purge;
- embargo;
- modelo;
- commit/tag;
- sobrescrita do artefato antigo.

## Criterio de passagem de S8.1

```text
proveniencia conhecida              PASS
comando oficial                     NAO IMPLEMENTADO
saida reconciliada definida         PASS
saida antiga preservada             PASS
invariantes pos-geracao definidas   PASS
regeneracao executada               PENDENTE
Gate 9                              BLOQUEADO
```
