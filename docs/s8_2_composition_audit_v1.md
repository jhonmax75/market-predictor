# S8.2 — Auditoria da composicao executavel real

**Estado:** concluida; nenhuma regeneracao executada

## Resultado resumido

A composicao funcional em memoria existe e pode ser executada sem criar nova arquitetura:

```text
CSV canonico do Gate 3
  -> pandas.read_csv(parse_dates=["timestamp_open"])
  -> normalize_ohlcv(raw)
  -> indexar por candle_open_ts
  -> build_features(ohlcv)
  -> build_direction_target(ohlcv)
  -> build_dataset(ohlcv, features, target)
  -> write_dataset(dataset, path)
```

Entretanto, o pipeline operacional completo nao existe como comando: `scripts/build_dataset.py` permanece vazio. Portanto, a proveniencia deve continuar sendo descrita como:

```text
PROVENIENCIA FUNCIONAL CONHECIDA
```

nao como pipeline de regeneracao executavel.

## Assinaturas confirmadas

```python
normalize_ohlcv(dataframe, *, asset_id="BTCUSDT") -> DataFrame
build_features(dataframe) -> DataFrame
build_direction_target(dataframe) -> DataFrame
build_dataset(ohlcv, features, target) -> DataFrame
write_dataset(dataset, path) -> None
```

## Responsabilidades confirmadas

- `loader.py`: converte respostas JSON Bybit em DataFrame bruto e preserva `turnover`;
- `normalize.py`: converte timestamps para UTC, ordena e materializa `candle_close_ts`;
- `technical.py`: calcula dez features causais, sem target;
- `direction.py`: calcula target posicional `close(t)`/`close(t+12)`, sem features;
- `builder.py`: valida a cadeia temporal, deriva `decision_ts` e `target_ts`, compoe e filtra linhas invalidas;
- `write_dataset()`: escreve Parquet, separado da composicao;
- `scripts/build_dataset.py`: vazio, sem orquestracao oficial.

## Fonte de entrada escolhida para futura S8.3

O candidato concreto e:

```text
data/processed/bybit/BTCUSDT/5m/20260916T002539Z/candles.csv
```

Esse CSV foi produzido pela coleta do Gate 3 e possui 85 linhas. Ele e uma representacao tabular da coleta raw, nao o Parquet supervisionado antigo.

A futura S8.3 deve ler esse CSV e nao o `dataset_v1.parquet` pre-reconciliacao.

## Saida futura

A saida deve ser gravada somente em:

```text
data/processed/reconciled_v1/dataset_v1.parquet
```

O destino antigo permanece preservado:

```text
data/processed/dataset_v1.parquet
```

A escrita deve falhar caso o novo destino ja exista, para impedir sobrescrita silenciosa. A funcao atual `write_dataset()` cria diretorios e escreve, mas nao oferece por si so a politica `exist_ok=False`; essa protecao pertence ao orquestrador futuro ou a uma decisao posterior de persistencia.

## Invariantes da futura auditoria fisica

Apos a S8.3, o Parquet reconciliado devera ser lido novamente e verificado em quatro camadas:

### Schema

```text
17 colunas na ordem normativa
timestamps UTC
```

### Temporal

```text
candle_close_ts = candle_open_ts + 5min
decision_ts = candle_close_ts
target_ts = decision_ts + 1h
target_ts > decision_ts
```

### Integridade

```text
(asset_id, decision_ts) unico
sem NaN
sem +/-inf
target_direction em {0, 1}
```

### Causalidade e semantica

```text
features pertencem a decision_ts
target representa horizonte futuro
future_return_1h e target_direction nao aparecem nas features
```

S6 fornece a evidencia de causalidade em memoria; S8.3 devera provar o schema e os valores do artefato concreto.

## Bloqueios antes de S8.3

- nenhum comando oficial de regeneracao;
- politica de destino novo ainda nao executada;
- DQC temporal auditado, mas nao ampliado;
- Parquet antigo preservado e nao reconciliado;
- nenhum metadata de regeneracao produzido.

## Conclusao

```text
assinaturas conhecidas              PASS
responsabilidades conhecidas        PASS
CSV de entrada identificado         PASS
composicao em memoria disponivel    PASS
orquestrador oficial                NAO IMPLEMENTADO
novo Parquet                        PENDENTE
artefato antigo preservado          PASS
```

S8.2 esta concluida como auditoria somente leitura. S8.3 podera executar a regeneracao controlada somente quando o destino, metadata e verificacoes pos-geracao forem confirmados.
