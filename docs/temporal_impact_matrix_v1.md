# S2 â€” Matriz de impacto da semantica temporal V1

**Data:** 2026-09-17
**Estado:** auditoria concluida; nenhuma correcao aplicada
**Semantica de referencia:** `decision_ts = candle_close_ts`

## Legenda

- **CONFORME:** representa a semantica S1 ou e compativel sem alteracao.
- **DIVERGENTE:** representa explicitamente `decision_ts = candle_open_ts` ou outra relacao incompatÃ­vel.
- **DEPENDENTE:** possui regra ou contrato que so pode ser avaliado depois da reconciliacao temporal.
- **NAO IMPLEMENTADO:** o consumidor ou comportamento ainda nao existe no codigo.
- **NAO APLICAVEL:** a ocorrencia nao executa ou nao decide a semantica temporal.

## Matriz por camada

| Camada | Arquivo/ocorrencia | Evidencia | Classificacao | Impacto |
|---|---|---|---|---|
| Configuracao | `configs/v1.yaml` `decision_basis: candle_close` | A decisao operacional e baseada no fechamento | CONFORME | Deve ser preservado |
| Configuracao | `configs/v1.yaml` `split.method: chronological` | Split cronologico configurado | DEPENDENTE | A referencia temporal do split ainda precisa ser reconciliada |
| Configuracao | `configs/v1.yaml` `purge_minutes: 60` | Parametro de purge declarado | DEPENDENTE | Nao existe split executado para provar a aplicacao |
| Configuracao | `configs/v1.yaml` `embargo_minutes: 0` | Parametro de embargo declarado | DEPENDENTE | A semantica final de `decision_ts` ainda precisa ser aplicada |
| Documentacao | `docs/data_source_v1.md` `startTime -> candle_open_ts` | Inicio da vela e distinto do fechamento | CONFORME | Base temporal preservada |
| Documentacao | `docs/data_source_v1.md` `candle_close_ts = open + 5m` | Fechamento derivado corretamente | CONFORME | Deve alimentar `decision_ts` |
| Documentacao | `docs/data_source_v1.md` `decision_ts = candle_close_ts` | Decisao no fechamento da vela completa | CONFORME | Contrato historico coerente |
| Documentacao | `docs/v1_prediction_spec.md` `timestamp_close` canonico | Fechamento e instante de decisao | CONFORME | Referencia normativa anterior |
| Documentacao | `docs/v1_prediction_spec.md` `target_ts = decision_ts + 1h` | Horizonte medido a partir da decisao | CONFORME | Depende da decisao no fechamento |
| Documentacao | `docs/dataset_matrix_v1.md` `decision_ts = candle_open_ts` | Builder define decisao como abertura | DIVERGENTE | Precisa ser reconciliado antes do Gate 9 |
| Documentacao | `docs/dataset_matrix_v1.md` saida sem `candle_close_ts`/`target_ts` | Representacao temporal incompleta | DEPENDENTE | S3 deve definir os campos derivados/materializados |
| Documentacao | `docs/target_matrix_v1.md` target posicional `t -> t+12` | Formula e causal na serie de candles | DEPENDENTE | A associacao entre indice `t` e timestamp de decisao precisa ser atualizada |
| Documentacao | `docs/gate8_temporal_incident.md` incidente | Registra conflito e proposta nao aplicada | CONFORME | Evidencia da auditoria, nao implementacao |
| Documentacao | `docs/leakage_audit_v1.md` purge/embargo | Regras declaradas para auditoria | DEPENDENTE | Nao ha split implementado nem evidencia operacional |
| Implementacao | `src/market_predictor/ingestion/normalize.py` `candle_open_ts` | Normaliza abertura em UTC e ordena | CONFORME | Nao define decisao |
| Implementacao | `src/market_predictor/features/technical.py` | Features usam OHLCV da observacao atual | CONFORME | Causal quando `decision_ts` e o fechamento |
| Implementacao | `src/market_predictor/targets/direction.py` | Usa `close(t)` e `close(t+12)` | CONFORME | Formula nao precisa ser alterada por S2 |
| Implementacao | `src/market_predictor/dataset/schema.py` | Valida estrutura, UTC e ordem de `candle_open_ts` | CONFORME | Nao e responsavel por definir decisao |
| Implementacao | `src/market_predictor/dataset/builder.py` | Copia `candle_open_ts` para `decision_ts` | DIVERGENTE | Principal ponto de reconciliacao |
| Implementacao | `src/market_predictor/dataset/builder.py` | Nao materializa `candle_close_ts` nem `target_ts` | DEPENDENTE | S3 deve definir a representacao antes de S4 |
| Implementacao | `src/market_predictor/dataset/split.py` | Arquivo vazio | NAO IMPLEMENTADO | Gate 9 nao pode ser aberto |
| Implementacao | `src/market_predictor/config.py` | Valida split e purge configurados | DEPENDENTE | Valida parametros, nao executa split/purge/embargo |
| DQC | `configs/dqc_v1.yaml` chave primaria `(asset_id, decision_ts)` | Identidade final usa decisao | DEPENDENTE | A coluna esta com semantica divergente no G8 atual |
| DQC | `configs/dqc_v1.yaml` intervalo `candle_close_ts - candle_open_ts = 5m` | Relacao de vela explicitada | CONFORME | Requer ambas as colunas materializadas |
| DQC | `configs/dqc_v1.yaml` DQ-017 `feature_data_max_ts <= decision_ts` | Regra causal declarada | DEPENDENTE | Proveniencia nao e derivada automaticamente |
| DQC | `configs/dqc_v1.yaml` DQ-019 `target_ts - decision_ts = 1h` | Horizonte temporal declarado | DEPENDENTE | G8 atual nao possui `target_ts` |
| DQC | `src/market_predictor/quality/rules.py` DQ-017 | Usa `causal_features` fornecido externamente | DEPENDENTE | Nao calcula `feature_data_max_ts` sozinho |
| DQC | `src/market_predictor/quality/rules.py` DQ-019 | Calcula delta quando `target_ts` existe | DEPENDENTE | Pode detectar erro, mas G8 atual nao fornece a coluna |
| DQC | `src/market_predictor/quality/rules.py` DQ-020/DQ-021 | Valida finitude e sinal do target | CONFORME | Independe da escolha open/close, mas exige target temporal correto |
| DQC | `src/market_predictor/quality/contract.py` campos temporais | Contrato inclui `decision_ts`, `candle_open_ts`, `candle_close_ts`, `target_ts` | CONFORME | Estrutura normativa ja aponta para o modelo S1 |
| Testes | `tests/test_config.py` `decision_basis == candle_close` | Configuracao testada | CONFORME | Evidencia direta da semantica historica |
| Testes | `tests/features/test_causality.py` | Futuro nao altera passado; observacao atual altera feature atual | CONFORME | Compatibilidade depende de decisao no fechamento |
| Testes | `tests/targets/test_direction.py` | Horizonte posicional exato `t+12` | DEPENDENTE | Precisa associar `t` ao fechamento na reconciliacao |
| Testes | `tests/dataset/test_builder.py` G8-T04 | Exige `decision_ts == candle_open_ts` | DIVERGENTE | Deve ser substituido apÃ³s S3 |
| Testes | `tests/dataset/test_builder.py` G8-T21 | Exige indice OHLCV compatÃ­vel com abertura | DEPENDENTE | Identidade do candle permanece, identidade da decisao muda |
| Testes | `tests/dataset/test_builder.py` G8-T22 | Testa alinhamento features/target no mesmo indice | CONFORME | A propriedade deve ser preservada com timestamp de fechamento |
| Testes | `tests/quality/test_dq_matrix.py` | Fixtures usam `decision_ts = candle_close_ts` e `target_ts = decision + 1h` | CONFORME | Testes de qualidade ja refletem S1 |
| Artefato | `data/raw/bybit/...` | Raw preserva `timestamp_open` e resposta da fonte | CONFORME | Evidencia de origem; nao deve ser reescrito |
| Artefato | `data/processed/.../candles.csv` | Canonico contem `candle_open_ts`, sem decisao derivada | DEPENDENTE | Entrada anterior a representacao do dataset |
| Artefato | `data/processed/dataset_v1.parquet` | Possui `decision_ts` derivado da abertura e nao possui close/target timestamps | DIVERGENTE | Pertence ao Gate 8 historico e nao deve ser reutilizado silenciosamente |
| Historico Git | `da731fc`, tag `gate-8`, `origin/master` | Gate 8 publicado com convencao open | DIVERGENTE | Deve ser preservado como evidencia historica |
| Historico Git | commits Gate 2-7 | Contratos anteriores apontam para fechamento | CONFORME | Base da reconciliacao |
| Historico Git | `docs/gate8_temporal_incident.md` nao versionado | Incidente presente no worktree | DEPENDENTE | Ainda nao e evidencia versionada |

## Matriz por termo

| Termo | Configuracao | Documentacao | Implementacao | Testes | DQC | Artefato | Estado S2 |
|---|---|---|---|---|---|---|---|
| `decision_ts` | `candle_close` | conflito G8 open vs V1 close | Builder usa open | G8 fixa open; quality usa close | chave e regras temporais | Parquet usa open | DIVERGENTE |
| `candle_open_ts` | campo de entrada | inicio da vela | normalizado e preservado | coberto | chave raw e gaps | presente no canonico | CONFORME |
| `candle_close_ts` | campo sem materializacao em v1 config | derivado open + 5m | ausente no Builder | fixtures quality possuem | DQ-007 exige | ausente no Parquet G8 | DEPENDENTE |
| `target_ts` | nao declarado operacionalmente | `decision + 1h` | ausente no Builder/target | fixtures quality possuem | DQ-018/019 exigem | ausente no Parquet G8 | DEPENDENTE |
| `split` | configurado cronologico | documentado | `split.py` vazio | somente config | nao executa split | inexistente | NAO IMPLEMENTADO |
| `purge` | 60 minutos configurados | regra documentada | nao implementado | nao testado operacionalmente | relatorio possui campo | inexistente como operacao | NAO IMPLEMENTADO |
| `embargo` | 0 configurado | regra documentada | nao implementado | nao testado operacionalmente | relatorio possui campo | inexistente como operacao | NAO IMPLEMENTADO |

## Respostas ao criterio S2

### Onde a semantica S1 ja esta correta?

- configuracao `decision_basis: candle_close`;
- `docs/data_source_v1.md`;
- `docs/v1_prediction_spec.md`;
- fixtures e testes temporais de `tests/quality`;
- causalidade das features quando interpretada no fechamento;
- formula posicional do target, condicionada a uma decisao corretamente ancorada.

### Onde esta divergente?

- `docs/dataset_matrix_v1.md`;
- `src/market_predictor/dataset/builder.py`;
- G8-T04 e a expectativa correspondente do Builder;
- `data/processed/dataset_v1.parquet` produzido sob o Gate 8 historico.

### Onde nao existe implementacao?

- `src/market_predictor/dataset/split.py`;
- aplicacao efetiva de purge;
- aplicacao efetiva de embargo;
- materializacao de `candle_close_ts` e `target_ts` no dataset Builder;
- derivacao automatica de `feature_data_max_ts` para DQ-017.

### Quais componentes dependem de decisao ainda nao representada?

- DQC temporal DQ-017 e DQ-019;
- target timestamp e auditoria de horizonte;
- split, purge e embargo;
- artefato Parquet reconciliado;
- testes G8 de identidade temporal;
- qualquer Gate 9 baseado em `decision_ts`.

## Conclusao S2

Nenhum consumidor relevante pesquisado ficou sem classificacao. A superficie de impacto esta conhecida.

A proxima etapa e S3: definir a representacao temporal do dataset, incluindo se `candle_close_ts` e `target_ts` serao materializados e como o Builder recebera ou derivara esses valores. Nenhuma alteracao de codigo foi aplicada nesta auditoria.
