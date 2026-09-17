# S6 â€” Auditoria de causalidade temporal ponta a ponta

**Escopo:** teste ponta a ponta entre normalizacao, features, target e Builder
**DQC:** nao alterado nesta fase
**Gate 9:** continua bloqueado

Este documento registra a causalidade cross-gate do pipeline em memoria. O teste
que monta o Builder nao move o Builder para o Gate 6; ele verifica uma
propriedade temporal conjunta usando componentes de Gates diferentes.

## O que S5 prova

S5 prova a representacao temporal produzida pelo dataset:

```text
candle_close_ts = candle_open_ts + 5min
decision_ts = candle_close_ts
target_ts = decision_ts + 1h
```

S5 nao prova que a implementacao de features foi limitada pela disponibilidade temporal nem que a fronteira futura do target foi respeitada ponta a ponta.

## O que ja esta provado pelo Gate 6

Os testes existentes provam que:

- alterar dados futuros nao altera features anteriores;
- alterar a observacao atual pode alterar as features da propria observacao;
- as janelas tecnicas sao causais em relacao a ordem dos candles;
- o OHLCV atual participa deliberadamente das features atuais.

Isso e compativel com a semantica S1 porque a decisao ocorre em `candle_close_ts`.

## O que S6 precisa provar

Para uma vela iniciada em `10:00` e encerrada em `10:05`:

```text
candle_open_ts = 10:00
candle_close_ts = 10:05
decision_ts = 10:05
```

As features da decisao podem usar o OHLCV da vela `[10:00, 10:05)`, mas nao podem usar dados de qualquer vela cujo fechamento seja posterior a `10:05`.

O target e diferente: pode usar o futuro autorizado. Para uma decisao em `decision_ts(t)`, `close(t+12)` e permitido e representa o fim do horizonte. Dados posteriores a esse ponto nao sao permitidos.

## Matriz de propriedades

| ID | Propriedade | Estado antes de S6 | Teste S6 |
|---|---|---|---|
| S6-T01 | normalizacao materializa `candle_close_ts` | parcialmente provado em S5 | fixture real de normalizacao |
| S6-T02 | `decision_ts == candle_close_ts` | provado em S5 | cadeia no Builder |
| S6-T03 | feature atual usa somente dados ate `decision_ts` | provado por Gate 6 em ordem posicional | mutacao da proxima vela nao altera feature atual |
| S6-T04 | features podem usar OHLCV da vela atual | provado pelo Gate 6 | mutacao da vela atual altera feature atual |
| S6-T05 | dados posteriores nao alteram features anteriores | provado parcialmente por Gate 6 | mutacoes em varias posicoes |
| S6-T06 | target usa futuro autorizado | provado posicionalmente por Gate 7 | target na fronteira `t+12` |
| S6-T07 | target nao usa futuro alem de `t+12` | nao provado ponta a ponta | mutacao em `t+13` preserva target de `t` |
| S6-T08 | Builder preserva o alinhamento temporal | provado internamente no G8 | linha final com features, decisao e target |
| S6-T09 | dados futuros nao mudam decisao anterior | nao aplicavel a um timestamp derivado | decisao e funcao somente do candle atual |

## Testes de causalidade

### S6-T01 â€” cadeia temporal ponta a ponta

Normalizar OHLCV, construir features e target, e montar o dataset. Para uma linha, verificar:

```text
candle_open_ts
candle_close_ts
decision_ts
target_ts
```

com as relacoes de S1.

### S6-T02 â€” proxima vela nao altera features atuais

Alterar OHLCV da vela `t+1`. Recalcular features e Builder. As features na decisao `t` devem permanecer iguais.

### S6-T03 â€” varias posicoes futuras nao alteram features passadas

Alterar candles em `t+1`, `t+5`, `t+12`, `t+36` e `t+72`. Para cada alteracao, todas as features anteriores ao candle alterado devem permanecer iguais.

### S6-T04 â€” vela atual pode alterar features atuais

Alterar `close`, `high`, `low` e `volume` da vela `t`. As features da decisao em `candle_close_ts(t)` devem poder mudar.

### S6-T05 â€” futuro autorizado altera target na fronteira

Alterar `close(t+12)` mantendo `close(t)` constante. O target da decisao `t` pode mudar.

### S6-T06 â€” futuro alÃ©m do horizonte nÃ£o altera target

Alterar somente `close(t+13)`. O target da decisao `t` deve permanecer igual.

### S6-T07 â€” separacao de efeitos

Uma alteracao futura pode alterar um target anterior se estiver dentro do horizonte permitido, mas nunca pode alterar as features anteriores:

```text
features(t) <- somente dados <= decision_ts(t)
target(t)   <- close(t) e close(t+12)
```

## Propriedades ainda nao provadas por S6

S6 nao prova automaticamente:

- que o DQC calcula `feature_data_max_ts` em vez de receber uma assercao externa;
- que `target_ts` foi validado pelo DQC em todos os fluxos;
- que split, purge e embargo sao implementados;
- que o dataset real regenerado passou pelo DQC temporal;
- que a causalidade estatistica implica ausencia de qualquer erro de proveniencia externo.

Esses pontos pertencem a S7 ou S8.

## Criterio de encerramento

S6 sera considerado aprovado quando os testes demonstrarem:

```text
feature(t) usa dados <= decision_ts(t)
target(t) usa exatamente close(t) e close(t+12)
target(t) nao usa close(t+13)
decision_ts(t) == candle_close_ts(t)
```

Nenhuma alteracao de DQC, split, purge, embargo ou Parquet faz parte desta fase.
