# Auditoria temporal do Gate 8

**Status:** incidente registrado; reconciliação pendente
**Classificação:** violação causal estrutural e desalinhamento temporal de contrato
**Data da auditoria:** 2026-09-17

## 1. Resumo executivo

O Gate 8 foi implementado e publicado com a convenção:

```text
decision_ts = candle_open_ts
```

Essa convenção conflita com os contratos anteriores da V1, que definem a decisão no fechamento do candle:

```text
decision_ts = candle_close_ts
```

A divergência é material porque as features do Gate 6 utilizam OHLCV do candle atual, incluindo `high`, `low`, `close` e `volume`. Esses valores representam o candle completo e, portanto, somente estão integralmente disponíveis no fechamento do intervalo.

O Builder pode passar integralmente seus testes internos e, ainda assim, produzir um dataset incompatível com a semântica temporal V1 anteriormente congelada.

O Gate 9 permanece bloqueado até que a identidade temporal da decisão seja formalmente reconciliada.

---

## 2. Evidência documental

### 2.1 Configuração operacional

`configs/v1.yaml` define:

```yaml
timestamps:
  open_field: timestamp_open
  close_field: timestamp_close
  decision_field: decision_ts
  decision_basis: candle_close
```

O teste de configuração também fixa:

```text
decision_basis == candle_close
```

Portanto, a configuração operacional anterior é explicitamente baseada no fechamento do candle.

### 2.2 Fonte de mercado

`docs/data_source_v1.md` estabelece, para um candle iniciado às 10:00:

```text
candle_open_ts  = 10:00
candle_close_ts = 10:05
decision_ts     = 10:05
```

O documento também estabelece que o timestamp de abertura identifica o intervalo observado e não constitui, por si só, o instante de decisão.

### 2.3 Especificação de previsão

`docs/v1_prediction_spec.md` define `timestamp_close` como o timestamp canônico de decisão.

A especificação exige ainda que:

```text
último candle completo
        ↓
candle_close_ts == decision_ts
```

e que o horizonte futuro seja medido a partir desse instante.

A semântica congelada anteriormente, portanto, é:

```text
candle_open_ts
      ↓
candle_close_ts
      ↓
decision_ts
      ↓
+ 1 hora
      ↓
target_ts
```

### 2.4 Contrato DQC

O DQC estabelece regras temporais que pressupõem que `decision_ts` represente o instante a partir do qual os dados utilizados na decisão estão disponíveis.

Entre essas regras estão:

```text
feature_data_max_ts <= decision_ts
target_ts - decision_ts == 1 hora
```

Entretanto, é importante registrar uma precisão metodológica: o código atual do DQC não deriva automaticamente `feature_data_max_ts` a partir das features. Parte dessas verificações depende de informações de proveniência e flags fornecidas à validação.

Assim, o ponto demonstrado pela auditoria é uma **incompatibilidade estrutural com a semântica temporal pretendida pelo DQC**, e não a afirmação de que o DQC atual necessariamente detectará sozinho o incidente.

### 2.5 Contrato introduzido no Gate 8

`docs/dataset_matrix_v1.md` introduziu:

```text
decision_ts = candle_open_ts
```

Essa convenção foi incorporada simultaneamente:

* à documentação;
* ao Builder;
* aos testes G8.

Portanto, o problema não é uma simples discrepância entre documentação e implementação do Gate 8. O Gate 8 é internamente consistente.

A inconsistência ocorre entre o novo contrato do Gate 8 e os contratos V1 congelados anteriormente.

---

## 3. Evidência de implementação

### 3.1 Gate 6 — features

`src/market_predictor/features/technical.py` utiliza a observação atual para calcular as features:

```python
features["ret_5m"] = returns
features["range_5m"] = (high - low) / close
features["range_1h"] = (...)
features["volume_trend"] = np.log1p(volume).rolling(...)
```

Consequentemente:

```text
feature(t) depende efetivamente de OHLCV(t)
```

Isso não caracteriza, isoladamente, um erro do Gate 6.

Essa implementação é coerente com uma decisão tomada quando o candle `t` já está completo.

O problema surge quando a mesma observação é identificada pelo seu `candle_open_ts`.

### 3.2 Gate 7 — target

O Gate 7 calcula:

```text
future_return_1h(t)
    = log(close(t+12) / close(t))
```

Para um intervalo de cinco minutos:

```text
t       = candle iniciado às 10:00
close(t) = fechamento às 10:05

t+12
close(t+12) = fechamento às 11:05
```

Logo, o retorno efetivamente representado é:

```text
10:05 → 11:05
```

O cálculo do Gate 7 permanece matematicamente correto em relação à série de candles.

O desalinhamento surge posteriormente quando o Gate 8 identifica a mesma linha como:

```text
decision_ts = 10:00
```

O Gate 7, portanto, não é classificado como incorreto nesta auditoria. O problema está na identificação temporal da decisão feita pelo Gate 8.

### 3.3 Gate 8 — Builder

`src/market_predictor/dataset/builder.py` produz diretamente:

```python
"decision_ts": ohlcv["candle_open_ts"].copy()
```

Essa linha estabelece a origem direta da divergência entre os contratos.

---

## 4. Evidência experimental dos testes

Os testes de causalidade do Gate 6 demonstram que alterar:

```text
close(t)
high(t)
low(t)
volume(t)
```

pode alterar:

```text
features(t)
```

Portanto:

```text
feature(t) depende de OHLCV(t)
```

Isso reforça a interpretação de que essas features representam informação disponível após o fechamento do candle atual.

Os testes do Gate 8, por sua vez, verificam explicitamente:

```text
decision_ts == candle_open_ts
```

e demonstram consistência interna dessa convenção.

Consequentemente:

```text
Gate 6:
features(t) → observação atual completa

Gate 8:
decision_ts(t) → início da observação
```

Essas duas afirmações não são temporalmente compatíveis quando `t` representa um candle de cinco minutos completo.

Os testes G8, portanto, não invalidam o diagnóstico. Eles demonstram que o novo contrato está implementado de forma consistente, mas não que esse contrato seja compatível com a V1 anterior.

---

## 5. Linha temporal dos Gates

A evolução relevante é:

```text
Gate 2
  candle_open_ts
       ↓
  candle_close_ts
       ↓
  decision_ts no fechamento

Gate 4
  OHLCV canônico
  preservação do open
  derivação do fechamento

Gate 5
  DQC temporal baseado na disponibilidade dos dados

Gate 6
  features utilizam OHLCV da observação atual

Gate 7
  target utiliza close(t) e close(t+12)

Gate 8
  decision_ts passa a ser definido como candle_open_ts
```

A incompatibilidade nasce na transição para o Gate 8.

Não foi encontrada evidência de um commit intermediário formal que tenha migrado ou revogado explicitamente a semântica anterior.

---

## 6. Exemplo temporal concreto

Considere o candle:

```text
[10:00, 10:05)
```

Temos:

```text
candle_open_ts  = 10:00
candle_close_ts = 10:05
```

O OHLCV completo desse intervalo somente está disponível ao término do intervalo.

As features atuais utilizam esse OHLCV.

Portanto, sob a semântica anterior:

```text
decision_ts = 10:05
```

O target do Gate 7 utiliza:

```text
close(t)     = close às 10:05
close(t+12)  = close às 11:05
```

Logo:

```text
target efetivo = 10:05 → 11:05
```

Entretanto, o Gate 8 declara:

```text
decision_ts = 10:00
```

Se `target_ts` for posteriormente derivado pela regra:

```text
target_ts = decision_ts + 1 hora
```

o resultado será:

```text
target_ts declarado = 11:00
```

enquanto o target efetivamente calculado pela série termina às:

```text
11:05
```

Isso produz dois desalinhamentos independentes:

1. **Disponibilidade das features**

```text
decision declarada = 10:00
feature information = disponível em 10:05
```

2. **Horizonte temporal do target**

```text
decision declarada = 10:00
target declarado = 11:00
target efetivo = 10:05 → 11:05
```

---

## 7. Classificação do incidente

O incidente é classificado como:

```text
VIOLAÇÃO CAUSAL ESTRUTURAL
+
DESALINHAMENTO TEMPORAL DE CONTRATO
```

A classificação não depende de:

* acurácia;
* performance do modelo;
* backtest;
* retorno financeiro;
* previsão efetivamente produzida.

Ela decorre diretamente da combinação:

```text
features(t) usam OHLCV(t)
```

com:

```text
decision_ts = candle_open_ts
```

O Gate 6 não é classificado como incorreto.

A inconsistência está na identificação temporal adotada pelo Gate 8 para uma observação cujos valores completos são utilizados pelas features.

---

## 8. Impacto sobre leakage

Sob o contrato declarado pelo Gate 8, existe risco estrutural de look-ahead:

```text
decision_ts = 10:00
feature information = até 10:05
```

Assim, a informação utilizada pela linha pode ultrapassar o instante declarado como decisão.

Em termos conceituais:

```text
information_available_time > declared_decision_time
```

Isso caracteriza incompatibilidade causal em relação ao timestamp de decisão.

Importante: essa conclusão não depende de observar uma melhora artificial de performance. O problema é anterior ao treinamento e ao backtest.

---

## 9. Impacto sobre o target

O target do Gate 7 permanece matematicamente correto para a sequência de candles.

Porém, sua interpretação temporal muda sob o contrato do Gate 8.

Com:

```text
decision_ts = 10:00
```

o dataset sugere uma previsão de uma hora posterior a 10:00.

Mas o cálculo efetivo utiliza:

```text
close(10:05) → close(11:05)
```

Portanto, o horizonte efetivo está ancorado no fechamento do candle, enquanto a decisão declarada está ancorada na abertura.

O problema é de **semântica temporal**, não de fórmula matemática do target.

---

## 10. Impacto sobre o DQC

O Gate 8 não deve ser considerado evidência suficiente de conformidade com o contrato temporal anterior do DQC.

A razão é que a semântica de:

```text
decision_ts
```

foi alterada sem que a relação temporal correspondente entre:

```text
features
decision
target
```

tenha sido formalmente reconciliada.

A validação futura deverá verificar explicitamente, conforme a semântica escolhida, pelo menos:

```text
último candle utilizado
        ↓
candle_close_ts
        ↓
decision_ts
```

e:

```text
decision_ts
        ↓
+ 1 hora
        ↓
target_ts
```

---

## 11. Impacto sobre o Gate 9

O Gate 9 permanece bloqueado.

Não é seguro iniciar:

* split temporal;
* purge;
* embargo;
* avaliação final;
* auditoria temporal definitiva;

antes de definir uma única identidade temporal para a decisão.

Qualquer operação baseada em `decision_ts` pode deslocar suas fronteiras em cinco minutos caso a semântica atual permaneça sem reconciliação.

Esse deslocamento é particularmente relevante para:

```text
train / validation / test
purge
embargo
target horizon
temporal ordering
```

---

## 12. Estado do histórico Git

O estado auditado inclui:

```text
da731fc (HEAD -> master, tag: gate-8, origin/master)
feat: implement Gate 8 dataset builder
```

A auditoria confirmou que o commit do Gate 8 alterou:

```text
docs/dataset_matrix_v1.md
src/market_predictor/dataset/builder.py
tests/dataset/test_builder.py
```

Não foram alterados nesse commit:

```text
configs/v1.yaml
docs/data_source_v1.md
docs/v1_prediction_spec.md
docs/v0_3_x_gate_audit.md
tests/test_config.py
```

Também não foi encontrada uma migração formal da semântica temporal anterior.

O histórico publicado deve permanecer preservado.

A reconciliação deve ser realizada mediante novos commits, sem reescrever o histórico do Gate 8.

---

## 13. Proposta de reconciliação — não aplicada

A evidência atualmente acumulada é compatível com a convenção:

```text
decision_ts = candle_close_ts
```

Essa convenção é consistente com:

* `configs/v1.yaml`;
* `docs/data_source_v1.md`;
* `docs/v1_prediction_spec.md`;
* semântica temporal anteriormente congelada;
* disponibilidade efetiva do OHLCV utilizado pelo Gate 6;
* interpretação temporal do target do Gate 7.

Essa é uma **proposta técnica de reconciliação**, não uma alteração já aplicada.

Antes de modificar qualquer código, devem ser formalmente decididos:

1. se o Builder deve receber ou derivar `candle_close_ts`;
2. se `decision_ts` deve representar `candle_close_ts`;
3. como o índice temporal de features e target será alinhado;
4. como `target_ts` será materializado e auditado;
5. quais testes G8 deverão ser modificados;
6. se o Parquet produzido pelo Gate 8 deverá ser regenerado;
7. como os contratos documentais deverão ser versionados;
8. qual nova tag representará a reconciliação;
9. quais evidências deverão ser exigidas antes da abertura do Gate 9.

Nenhuma dessas alterações foi aplicada nesta auditoria.

---

## 14. Decisão de Gate

```text
Gate 8 histórico: PRESERVADO E AUDITÁVEL

Gate 8 interno: CONSISTENTE

Gate 8 temporal em relação à V1 anterior: INCONSISTENTE

Violação causal estrutural: IDENTIFICADA

Desalinhamento do target: IDENTIFICADO

Migração formal de contrato: NÃO ENCONTRADA

Gate 9: BLOQUEADO

Código: NENHUMA CORREÇÃO APLICADA
```

## 15. Conclusão

O incidente está suficientemente demonstrado para impedir a progressão para o Gate 9.

A questão não é determinar se o Builder "funciona". Ele funciona segundo o contrato que o próprio Gate 8 introduziu.

A questão é determinar se esse contrato ainda representa a semântica temporal V1 anteriormente congelada.

A evidência disponível mostra que não.

O estado correto do projeto, portanto, é:

```text
                    HISTÓRICO
                       │
                       ▼
                 Gate 8 preservado
                       │
                       ▼
              incidente temporal
                       │
                       ▼
          decisão formal de semântica
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       reconciliação          revisão
       do contrato            necessária
             │
             ▼
       novo commit/tag
             │
             ▼
      nova matriz de testes
             │
             ▼
       validação temporal
             │
             ▼
          Gate 9
```

Nenhuma correção deve ser aplicada ao código antes da decisão formal sobre a identidade temporal de `decision_ts`.
