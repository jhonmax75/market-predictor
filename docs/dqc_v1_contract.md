# Data Quality Contract V1

## Status

- **Versao:** DQC V1
- **Status:** contrato normativo para implementacao
- **Dataset:** decisoes de previsao OHLCV de 5 minutos
- **Fonte normativa:** [../configs/dqc_v1.yaml](../configs/dqc_v1.yaml)
- **Implementacao:** [../src/market_predictor/quality/contract.py](../src/market_predictor/quality/contract.py)

## 1. Finalidade

Uma linha so pode entrar no dataset supervisionado se for:

- temporalmente coerente;
- numericamente valida;
- causalmente utilizavel;
- suficientemente completa para construir features e target;
- auditavel e versionada.

A validade do dataset e definida por:

$$
D_{V1} \in D_{valid}
$$

Nao e permitido corrigir silenciosamente dados problematicos. Toda ocorrencia deve produzir um registro de auditoria, uma decisao e, quando aplicavel, uma contagem por regra.

## 2. Decisoes de qualidade

Cada regra deve produzir uma decisao com um destes estados:

| Estado | Significado | Efeito |
|---|---|---|
| `REJECT` | Falha estrutural ou de contrato no lote, segmento ou registro bruto | interromper a etapa ou rejeitar a unidade afetada |
| `EXCLUDE_ROW` | O dado bruto pode existir, mas a linha nao e utilizavel para V1 | excluir a linha do dataset supervisionado |
| `ACCEPT` | A regra passou | permitir a proxima camada |
| `FLAG` | Anomalia observavel, sem prova suficiente de erro | manter e registrar para investigacao |
| `NOT_EVALUABLE` | Pre-condicao de uma regra anterior falhou | nao criar uma segunda falha para o mesmo sintoma |

Severidade operacional:

| Severidade | Uso |
|---|---|
| `ERROR` | produz `REJECT` ou `EXCLUDE_ROW` |
| `WARNING` | produz `FLAG`, sem excluir automaticamente |
| `INFO` | registra contexto ou contagem |

## 3. Identidade e timezone

As chaves sao:

- candle bruto: `(asset_id, candle_open_ts)`;
- linha de decisao: `(asset_id, decision_ts)`.

Cada chave deve ser unica. Duplicatas nao podem ser resolvidas escolhendo arbitrariamente a primeira ou a ultima linha.

Todos os timestamps internos devem ser `datetime64[ns, UTC]`. Timestamp sem timezone deve produzir `TIMEZONE_UNKNOWN` e ficar fora da construcao ate que o timezone da fonte seja conhecido. Somente uma fonte com timezone conhecido pode ser convertida para UTC:

```text
timestamp original
    -> interpretacao no timezone conhecido da fonte
    -> UTC
```

Nunca assumir UTC para um timestamp ingenuo.

## 4. Camadas da auditoria

A auditoria deve seguir esta ordem:

```text
RAW
  -> STRUCTURAL
  -> TEMPORAL
  -> SEMANTIC
  -> CAUSAL
  -> V1 DATASET
```

### RAW

Registrar origem, arquivo ou lote, colunas, tipos, periodo, ativo e politica de timezone.

### STRUCTURAL

Validar duplicatas, colunas obrigatorias, tipos numericos, nulos e finitude. Um `NaN` deve ser classificado como ausencia antes de ser considerado nao finito.

### TEMPORAL

Validar timezone, ordenacao, intervalo de 5 minutos, continuidade, historico minimo e disponibilidade do futuro.

### SEMANTIC

Validar preco positivo, relacao OHLC, volume nao negativo e coerencia do target.

### CAUSAL

Demonstrar que cada feature usa somente dados disponiveis em `decision_ts` e que target e campos futuros nao entram em scaling, imputacao, selecao ou treinamento.

## 5. Regras normativas DQ

O arquivo [../configs/dqc_v1.yaml](../configs/dqc_v1.yaml) e a unica fonte normativa da numeracao DQ-001 a DQ-030. O contrato Python deve permanecer alinhado a ele. Esta documentacao nao redefine nomes, IDs ou agrupamentos.

| ID | Regra normativa |
|---|---|
| DQ-001 | `asset_id` obrigatorio |
| DQ-002 | `decision_ts` obrigatorio |
| DQ-003 | Timestamps em UTC |
| DQ-004 | Unicidade da chave primaria |
| DQ-005 | Ordenacao temporal |
| DQ-006 | Duplicidade de candle |
| DQ-007 | Intervalo do candle de 5 minutos |
| DQ-008 | Continuidade temporal |
| DQ-009 | Lacuna temporal fora da janela |
| DQ-010 | Precos positivos |
| DQ-011 | Consistencia OHLC |
| DQ-012 | Volume nao negativo |
| DQ-013 | Volume igual a zero |
| DQ-014 | Valores OHLCV finitos |
| DQ-015 | Features finitas |
| DQ-016 | Historico minimo |
| DQ-017 | Causalidade das features |
| DQ-018 | Target disponivel |
| DQ-019 | Target temporalmente posterior |
| DQ-020 | `future_return_1h` finito |
| DQ-021 | `target_direction` consistente |
| DQ-022 | Target ausente das features |
| DQ-023 | Ausencia de dados futuros nas features |
| DQ-024 | Scaler ajustado somente no treinamento |
| DQ-025 | Retorno extremo |
| DQ-026 | Volume extremo |
| DQ-027 | Ausencia de NaN nas features finais |
| DQ-028 | Tipos de dados |
| DQ-029 | Degeneracao da variavel alvo |
| DQ-030 | Relatorio de auditoria obrigatorio |

Qualquer mudanca nessa matriz exige atualizar o YAML, o contrato Python, os testes e a versao do contrato de forma coordenada.

Regras de precedencia:

1. `DQ-006` avalia ausencia antes de `DQ-008` avaliar finitude.
2. Se uma pre-condicao falhar, regras dependentes ficam `NOT_EVALUABLE`.
3. Duplicatas nunca sao deduplicadas silenciosamente.
4. Lacunas nao devem ser preenchidas com `ffill`, `bfill`, interpolacao ou zero arbitrario.
5. Violacao de causalidade e sempre `ERROR` e exige investigacao do pipeline.

## 6. Lacunas e anomalias

Uma lacuna e detectada quando dois candles consecutivos do mesmo ativo nao estao separados por 5 minutos. A auditoria deve registrar:

```text
gap_start
gap_end
gap_duration
market_schedule_status
```

A politica da V1 e:

- mercado deveria estar aberto: `ERROR` e segmento inelegivel;
- periodo oficialmente sem negociacao: `INFO` ou `FLAG`, conforme a fonte;
- horario desconhecido: `WARNING` e segmento pendente de resolucao.

Nenhuma lacuna deve gerar candle sintetico.

Retorno, volume ou volatilidade extremos nao causam exclusao automatica. Eles devem ser marcados como `FLAG` quando houver uma regra estatistica de monitoramento, pois podem representar eventos reais do mercado. `ANOMALY` nao significa automaticamente `ERROR`.

Mudanca de escala, split ou politica de ajuste nao documentada deve produzir `ADJUSTMENT_UNKNOWN` e tornar o segmento inelegivel ate a politica ser identificada. A serie nao pode misturar precos ajustados e nao ajustados sem registro explicito.

Volume zero nao e erro automatico. Deve gerar uma contagem `ZERO_VOLUME` e permanecer sujeito a analise da fonte.

## 7. Validacao da linha supervisionada

Para cada `(asset_id, decision_ts)`:

1. o ultimo candle completo termina em `decision_ts`;
2. existem 72 candles historicos completos e contiguos;
3. existem 12 candles futuros completos para o target;
4. `target_ts = decision_ts + 1 hora`;
5. `future_return_1h` e calculado somente com precos validos;
6. `target_direction = 1` se `future_return_1h > 0`, e `0` caso contrario;
7. nenhuma feature consulta `D_{>decision_ts}`.

Se o futuro nao estiver disponivel, a observacao pode ser usada para inferencia, mas nao para treino, validacao ou teste supervisionados.

Target igual a zero pertence a classe `0`. Uma futura classe neutra exige uma nova versao do contrato e do schema.

## 8. Separacao anti-leakage

As colunas abaixo nunca podem entrar em `FEATURE_COLUMNS`:

```text
future_return_1h
target_direction
```

Tambem nao podem participar de:

- scaling;
- normalizacao;
- imputacao;
- selecao de features;
- ajuste de hiperparametros.

Qualquer scaler deve ser ajustado somente no treino de cada particao ou janela walk-forward e aplicado sem novo ajuste na validacao e no teste.

## 9. Relatorio de auditoria

Cada execucao deve produzir um relatorio estruturado, por exemplo `audit_report.json`, contendo no minimo:

```text
contract_version
dataset_version
feature_schema_version
source
asset
period_start
period_end
raw_rows
accepted_rows
excluded_rows
rejected_rows
purged_rows
rejection_count_by_rule
duplicate_candles
duplicate_keys
timezone_errors
timestamp_errors
gaps_detected
critical_gaps
invalid_ohlc
invalid_prices
invalid_volume
zero_volume
nan_features
infinite_features
missing_history
missing_target
causal_violations
train_rows
validation_rows
test_rows
first_decision_ts
last_decision_ts
purge_duration
embargo_duration
audit_status
```

`audit_status` deve assumir apenas:

| Status | Condicao |
|---|---|
| `PASS` | nenhuma regra `ERROR` e dataset autorizado |
| `PASS_WITH_FLAGS` | nenhuma regra `ERROR`, mas existem anomalias `FLAG` documentadas |
| `FAIL` | existe regra `ERROR`, violacao causal, inconsistencia de schema ou relatorio incompleto |

`PASS_WITH_FLAGS` nao autoriza ignorar flags. O relatorio deve acompanhar o artefato e ser revisado antes da modelagem.

## 10. Invariante final

> Nenhuma linha entra no conjunto supervisionado da V1 apenas porque suas colunas numericas parecem validas. A linha precisa ter uma posicao temporal inequivoca, pertencer a uma sequencia coerente, possuir historico suficiente, possuir target futuro verificavel e demonstrar que todas as features sao calculaveis exclusivamente com informacao disponivel ate o instante de decisao.

## 11. Pipeline autorizado

```text
FONTE BRUTA
    -> normalizacao UTC
    -> validacao estrutural
    -> deteccao de duplicatas
    -> validacao temporal
    -> deteccao de lacunas
    -> validacao OHLCV
    -> verificacao de continuidade
    -> construcao causal das features
    -> construcao do target
    -> auditoria anti-leakage
    -> DATASET V1
    -> split temporal com purge
    -> modelo
    -> relatorio de avaliacao
```

A implementacao Python deve transformar cada regra em teste automatizado e preservar o `audit_report.json` junto do dataset produzido.
