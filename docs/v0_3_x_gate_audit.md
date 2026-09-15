# v0.3.x — auditoria operacional e gates

## Estado do escopo

A v0.3.x fica congelada como a etapa de pipeline de dados e dataset V1, com os seguintes limites explícitos:

- Gate 1: configuração operacional fechada
- Gate 2: fonte de mercado fechada
- Gate 3: ingestão de dados ainda não iniciada
- Gates 4 a 12: implementação futura, sem expansão de escopo antes da base estar validada

A regra operacional é simples: nada de feature, target, split ou treinamento antes da ingestão histórica e do DQC canônico estarem em estado auditável.

## Checklist de aceite operacional

### Gate 1 — Configuração operacional

| ID | Critério | Evidência |
|---|---|---|
| G1-01 | `configs/v1.yaml` existe | arquivo presente |
| G1-02 | `timeframe = 5m` | teste de configuração |
| G1-03 | `timezone = UTC` | teste de configuração |
| G1-04 | janela = 72 candles | teste de configuração |
| G1-05 | janela inclui o candle da decisão | documentação + teste |
| G1-06 | horizonte = 12 candles / 60 min | teste de configuração |
| G1-07 | features V1 enumeradas | configuração |
| G1-08 | split temporal definido | configuração |
| G1-09 | `shuffle = false` | teste de configuração |
| G1-10 | purge/gap definido | configuração |
| G1-11 | política de correção silenciosa desabilitada | configuração |

Aceite do Gate 1:

```bash
$env:PYTHONPATH = "src"
python -m pytest tests/test_config.py -q
```

### Gate 2 — Fonte de mercado

| ID | Critério | Evidência |
|---|---|---|
| G2-01 | Bybit Spot definida | docs/data_source_v1.md |
| G2-02 | BTCUSDT definido | documento |
| G2-03 | intervalo 5m confirmado | documento + coleta real |
| G2-04 | timezone UTC | documento |
| G2-05 | significado de `startTime` definido | documento |
| G2-06 | `candle_open_ts` separado de `candle_close_ts` | documento |
| G2-07 | `decision_ts` derivado do fechamento | documento |
| G2-08 | REST descending documentado | documento |
| G2-09 | limite de 1000 documentado | documento |
| G2-10 | paginação documentada | documento |
| G2-11 | retries documentados | documento |
| G2-12 | amostra real inspecionada | registro da coleta |
| G2-13 | 72 + 12 = 84 explicitado | documento |
| G2-14 | jitter configurável | documento |

Aceite do Gate 2:

```bash
git diff --check
```

Com a validação documental do Gate 2, a fonte foi congelada para a V1: Bybit Spot REST API V5, `BTCUSDT`, `interval=5`, UTC e semântica canônica de `startTime`/`candle_open_ts`/`candle_close_ts`/`decision_ts`.

## Fronteira do Gate 3

O Gate 3 começa apenas quando os Gates 1 e 2 estão estabilizados e registrados. O objetivo do Gate 3 é unicamente a ingestão. Não entra ainda:

- features
- target
- split
- modelo
- treinamento

### Escopo permitido do Gate 3

- endpoint configurável
- `category=spot`
- `symbol=BTCUSDT`
- `interval=5`
- `limit <= 1000`
- timeout explícito
- tratamento de HTTP errors
- tratamento de `retCode != 0`
- tratamento de 429
- tratamento de 5xx
- retry limitado
- backoff configurável
- jitter configurável
- paginação por janela temporal
- nenhuma dependência da ordem reversa da API
- resposta bruta preservada

### Escopo proibido do Gate 3

- imputação
- correção silenciosa
- feature engineering
- cálculos de target
- split temporal
- treinamento

## Estrutura de arquivos operacional

```text
src/market_predictor/
├── config.py
├── ingestion/
│   ├── __init__.py
│   ├── client.py
│   ├── loader.py
│   └── normalize.py
├── quality/
│   ├── __init__.py
│   ├── contract.py
│   ├── report.py
│   ├── rules.py
│   └── validator.py
├── dataset/
│   ├── __init__.py
│   ├── schema.py
│   ├── builder.py
│   └── split.py
├── features/
│   ├── __init__.py
│   └── technical.py
├── targets/
│   ├── __init__.py
│   └── direction.py
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py
│   └── backtest.py
├── models/
│   ├── __init__.py
│   ├── baseline.py
│   └── logistic.py
└── __init__.py
```

A correção relevante aqui é que a normalização histórica entra no fluxo de ingestão, mas a limpeza estatística não entra em `normalize.py`. A normalização é um mapeamento canônico, não uma etapa de correção de dados.

## Regra de arquitetura

Os módulos devem permanecer com responsabilidade única:

- `ingestion/client.py`: conversa com a Bybit
- `ingestion/loader.py`: transforma resposta em registro bruto
- `ingestion/normalize.py`: converte para schema canônico
- `dataset/schema.py`: declara o contrato estrutural do dataset
- `dataset/builder.py`: monta o dataset V1 com features e target
- `dataset/split.py`: divide temporalmente sem shuffle
- `features/technical.py`: implementa features causais
- `targets/direction.py`: calcula direção do alvo

Nenhum desses módulos deve estar misturado com responsabilidade de outra camada.

## Procedimento recomendado para seguir

A sequência segura é:

1. confirmar `configs/v1.yaml` como fonte operacional;
2. manter `configs/dqc_v1.yaml` como contrato normativo do DQC;
3. manter `docs/data_source_v1.md` como explicação de semântica da fonte;
4. reservar Gate 3 para `ingestion/client.py` e `ingestion/loader.py`;
5. começar apenas depois da garantia de que `72 + 12 = 84` e `shuffle = false` estão completamente congelados.

## Conclusão

A nossa base atual está alinhada com o que foi decidido no Gate 1 e no Gate 2. O estado operacional do repositório já fornece a base correta para a etapa seguinte, sem extrapolar o escopo de v0.3.x.

O próximo movimento válido é a implementação isolada de `ingestion/client.py`, com a ingestão real mantida separada de features, target e treinamento.
