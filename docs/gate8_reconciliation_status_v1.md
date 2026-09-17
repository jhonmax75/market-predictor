# Estado atual da reconciliacao temporal do Gate 8

**Data:** 2026-09-17
**Status:** reconciliacao implementada, testada e materializada

## Leitura do historico

Os documentos abaixo permanecem como registros de estados anteriores e nao devem ser reescritos retroativamente:

- `docs/temporal_impact_matrix_v1.md`: diagnostico S2;
- `docs/temporal_representation_v1.md`: especificacao S3;
- `docs/gate8_temporal_incident.md`: incidente historico do Gate 8;
- `docs/s8_regeneration_plan_v1.md`: plano S8.1;
- `docs/s8_2_composition_audit_v1.md`: fotografia historica da S8.2;
- `docs/s8_2_closed_contract_check_v1.md`: checagem pre-write da S8.2.

As referencias a divergencia, pendencia ou bloqueio nesses documentos descrevem o estado no momento em que foram produzidas.

## Estado reconciliado atual

A reconciliacao posterior implementa:

```text
candle_close_ts = candle_open_ts + 5min
decision_ts = candle_close_ts
target_ts = decision_ts + 1h
```

A representacao fisica atual foi validada em:

```text
data/processed/reconciled_v1/dataset_v1.parquet
```

O artefato antigo permanece preservado em:

```text
data/processed/dataset_v1.parquet
```

Ele continua sendo evidencia local do estado pre-reconciliacao e nao foi sobrescrito.

## Evidencias atuais

### Implementacao e testes

- normalizacao materializa `candle_close_ts`;
- Builder materializa `decision_ts` e `target_ts`;
- o schema final reconciliado possui 17 colunas;
- causalidade ponta a ponta em memoria foi testada em S6;
- DQC temporal foi auditado sem alteracao de comportamento;
- a cardinalidade real `85 -> 13 features validas, 73 targets, 1 intersecao` foi registrada.

### Artefato

S8.3 e S8.4 foram concluidas:

```text
novo Parquet: existe e foi relido
schema: 17 colunas
cadeia temporal: PASS
integridade: PASS
legado: preservado por SHA-256
```

A evidencia detalhada esta em [docs/s8_4_artifact_validation_v1.md](s8_4_artifact_validation_v1.md).

## Limites ainda vigentes

Este fechamento nao afirma que o Gate 9 foi executado ou que todos os componentes futuros existem. Permanecem fora do escopo:

- split temporal implementado;
- purge executado;
- embargo executado;
- scaler train-only auditado por objeto real;
- DQC com derivacao automatica de `feature_data_max_ts`;
- modelo, backtest e metricas.

Portanto, o estado correto e:

```text
Gate 8 temporal reconciliado       PASS
artefato reconciliado              PASS
artefato legado preservado         PASS
Gate 9 executado                   NAO
Gate 9 elegivel                    PENDENTE DE REAVALIACAO
```

## Candidato a commit

O proximo commit deve agrupar somente a reconciliacao temporal, seus testes e a cadeia documental de evidencia. Nenhum documento historico deve ser reescrito para substituir o estado que registrava.

Antes do commit, executar a auditoria Git final e revisar explicitamente os arquivos que serao incluidos. Nenhum `git add`, commit ou tag foi executado como parte deste fechamento documental.
