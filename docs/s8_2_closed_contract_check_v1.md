# S8.2 â€” Checagem fechada do contrato de composicao

**Estado:** concluida sem escrita
**Resultado:** composicao em memoria aprovada; escrita controlada ainda pendente

## Writer

Funcao confirmada:

```python
market_predictor.dataset.builder.write_dataset(
    dataset: pd.DataFrame,
    path: str | pathlib.Path,
) -> None
```

Comportamento atual:

- cria o diretorio pai com `mkdir(parents=True, exist_ok=True)`;
- chama `DataFrame.to_parquet(output_path, index=False)`;
- usa PyArrow disponivel no ambiente;
- nao recebe flag `overwrite`;
- nao verifica se o destino ja existe;
- nao valida o schema antes da escrita;
- nao usa arquivo temporario nem troca atomica;
- nao registra metadata adicional.

Conclusao: a funcao escreve Parquet em caminho parametrizavel, mas nao e suficiente sozinha para a politica de nao sobrescrita de S8.3. O executor futuro deve verificar que o destino nao existe antes de chama-la, ou a politica de persistencia precisa ser decidida explicitamente antes da escrita.

## Entrada real

O caminho utilizado na composicao foi:

```text
data/processed/bybit/BTCUSDT/5m/20260916T002539Z/candles.csv
```

O arquivo real possui 85 linhas e o schema:

```text
asset_id
candle_open_ts
open
high
low
close
volume
```

Ele e um CSV canonico do Gate 4, nao o payload bruto do loader. Portanto, a leitura correta para esta composicao e:

```python
pd.read_csv(path, parse_dates=["candle_open_ts"])
```

Nao se deve usar `parse_dates=["timestamp_open"]` neste arquivo. O loader Bybit continua sendo responsavel pelo formato de resposta JSON; ele nao e o leitor deste CSV canonico.

Propriedades observadas:

```text
rows = 85
asset_id = BTCUSDT
candle_open_ts = UTC e crescente
OHLCV presente
```

## Composicao executada em memoria

A sequencia real executada sem escrita foi:

```text
pd.read_csv(parse_dates=["candle_open_ts"])
  -> normalize_ohlcv()
  -> index por candle_open_ts
  -> build_features()
  -> build_direction_target()
  -> build_dataset()
```

Assinaturas confirmadas:

```text
normalize_ohlcv(dataframe, *, asset_id="BTCUSDT") -> DataFrame
build_features(dataframe) -> DataFrame
build_direction_target(dataframe) -> DataFrame
build_dataset(ohlcv, features, target) -> DataFrame
write_dataset(dataset, path) -> None
```

## Resultado da checagem

```text
INPUT_OK rows=85
NORMALIZED_OK rows=85
FEATURE_ROWS=85
TARGET_ROWS=73
COMPOSITION_OK rows=1
SCHEMA_OK columns=17
TEMPORAL_OK
INTEGRITY_OK
OUTPUT_PATH_OK new_exists=False
WRITE=SKIPPED
```

O resultado final possui uma linha porque o warm-up das features e o horizonte do target se sobrepoem na coleta curta. Essa cardinalidade foi medida, nao presumida.

## Schema e invariantes verificadas

- 17 colunas na ordem normativa;
- `candle_close_ts - candle_open_ts == 5min`;
- `decision_ts == candle_close_ts`;
- `target_ts - decision_ts == 1h`;
- `target_ts > decision_ts`;
- chave `(asset_id, decision_ts)` unica;
- nenhum `NaN`;
- nenhum `+/-inf` numerico;
- `target_direction` em `{0, 1}`;
- destino novo ainda inexistente;
- Parquet antigo preservado.

## Decisao S8.2

```text
assinatura do writer conhecida       PASS
CSV real identificado                 PASS
leitura real confirmada               PASS
composicao em memoria                 PASS
schema reconciliado                   PASS
invariantes temporais                 PASS
integridade                           PASS
protecao contra overwrite             PENDENTE no executor
escrita Parquet                       NAO EXECUTADA
S8.3                                   PENDENTE
```

Nenhum arquivo de dados foi criado ou modificado nesta checagem.
