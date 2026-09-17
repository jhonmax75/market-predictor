# S7 â€” Auditoria do DQC temporal V1

**Escopo:** DQ-017 a DQ-024
**Estado:** auditoria concluida; nenhum patch aplicado
**Distincao central:** teste de causalidade nao e prova automatica do DQC

## Classificacao

| Regra | Pergunta | Comportamento atual | Classificacao |
|---|---|---|---|
| DQ-017 | O DQC calcula que features nao ultrapassam `decision_ts`? | `rules.py` aceita `causal_features=True/False/None`; nao calcula `feature_data_max_ts` nem inspeciona proveniencia | GARANTIA EXTERNA / NOT_EVALUABLE sem flag |
| DQ-018 | O futuro do target existe? | Exige `target_ts`, `future_return_1h` e `target_direction`; verifica `target_ts.notna()` quando target e requerido | CALCULADO PARCIALMENTE |
| DQ-019 | `target_ts = decision_ts + 1h` e verificado? | Calcula a diferenca temporal e rejeita delta diferente de uma hora quando timestamps UTC existem | CALCULADO |
| DQ-020 | `future_return_1h` e finito? | Usa `np.isfinite` e rejeita valores nao finitos | CALCULADO |
| DQ-021 | `target_direction` corresponde ao retorno? | Recalcula o sinal `future_return_1h > 0` e compara com a coluna recebida | CALCULADO |
| DQ-022 | Target esta fora de `FEATURE_COLUMNS`? | Verifica intersecao entre target columns e lista de features recebida | CALCULADO SOBRE O SCHEMA DECLARADO |
| DQ-023 | Existe operacao futura contaminando features? | Aceita `causal_features=True`; sem garantia fica `NOT_EVALUABLE`; nao analisa grafo/proveniencia | GARANTIA EXTERNA / NOT_EVALUABLE sem flag |
| DQ-024 | Scaler e train-only? | Aceita `scaler_fitted_on_train=True/False/None`; nao inspeciona scaler ou particoes | GARANTIA EXTERNA / NAO IMPLEMENTADO |

## O que o DQC prova automaticamente

O codigo atual calcula diretamente:

```text
DQ-019  target_ts - decision_ts == 1h
DQ-020  future_return_1h finito
DQ-021  target_direction == (future_return_1h > 0)
DQ-022  targets ausentes de FEATURE_COLUMNS
```

DQ-018 tambem calcula a presenca e a nulidade dos campos de target, mas nao prova sozinho que `target_ts` corresponde ao candle futuro correto. Essa parte depende de DQ-019 e da representacao temporal anterior.

## O que depende de garantia externa

### DQ-017

O resultado `PASS` e produzido quando o chamador fornece `causal_features=True`. Isso e uma assercao de pipeline, nao uma derivacao de `feature_data_max_ts` a partir do dataset.

O teste de S6 que altera candles futuros e observa features passadas prova uma propriedade da implementacao testada. Ele nao transforma automaticamente DQ-017 em uma verificacao dinamica para qualquer dataset recebido em runtime.

### DQ-023

A regra tambem depende de `causal_features=True`. Ela nao examina operacoes, dependencias de colunas, timestamps de proveniencia ou o historico de transformacao.

### DQ-024

A regra depende de `scaler_fitted_on_train=True`. Como o split ainda nao esta implementado, nao existe objeto de scaler ou particao que o DQC possa auditar diretamente.

## Relacao com S6

S6 prova em memoria:

```text
normalize -> features/target -> builder
```

As propriedades demonstradas sao:

- `candle_close_ts` deriva de `candle_open_ts`;
- `decision_ts` e o fechamento;
- a vela atual pode influenciar features atuais;
- candles posteriores nao influenciam features anteriores;
- `t+12` pode influenciar o target;
- `t+13` nao influencia o target.

Essas evidencias sao pre-condicoes fortes para uma futura garantia de DQ-017/DQ-023, mas nao substituem um mecanismo de proveniencia no validator.

## Estado das regras e implicacoes

```text
DQ-017  nao calculado automaticamente
DQ-018  presenca/nulidade calculada; validade temporal depende de outras regras
DQ-019  calculado quando target_ts e UTC
DQ-020  calculado
DQ-021  calculado
DQ-022  calculado sobre schema/lista declarada
DQ-023  nao calculado automaticamente
DQ-024  nao implementado como auditoria de scaler
```

Nenhuma destas conclusoes justifica alterar as regras nesta etapa. S7 primeiro separa evidencia interna de assercao externa. Qualquer melhoria futura deve ser uma mudanca coordenada no YAML, contrato Python, rules, validator e testes.

## Limites

S7 nao implementa:

- novo mecanismo de proveniencia de features;
- split temporal;
- purge;
- embargo;
- scaler;
- regeneracao do Parquet;
- abertura do Gate 9.

## Criterio de conclusao da auditoria

A auditoria S7 e considerada concluida quando cada regra temporal estiver classificada como calculada, parcialmente calculada, garantia externa, nao implementada ou nao avaliavel. O estado atual satisfaz esse criterio sem alterar o comportamento do DQC.
