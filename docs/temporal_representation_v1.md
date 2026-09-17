# S3 â€” Representacao temporal fisica do dataset V1

**Status:** especificacao congelada para reconciliacao
**Semantica:** `decision_ts = candle_close_ts`
**Gate 9:** bloqueado ate S4-S8

## Campos temporais materializados

O dataset supervisionado V1 reconciliado materializara os quatro campos:

```text
candle_open_ts
candle_close_ts
decision_ts
target_ts
```

Cada campo possui significado distinto, mesmo quando duas relacoes produzem igualdade de valores:

- `candle_open_ts`: inicio do intervalo da vela;
- `candle_close_ts`: fim do intervalo da vela;
- `decision_ts`: instante da decisao no fechamento da ultima vela completa;
- `target_ts`: fim do horizonte futuro supervisionado.

## Fonte de verdade temporal

Existe uma unica origem primaria:

```text
candle_open_ts
```

A cadeia normativa e:

```text
candle_close_ts = candle_open_ts + 5 minutos
decision_ts = candle_close_ts
target_ts = decision_ts + 1 hora
```

Consequentemente:

```text
target_ts = candle_open_ts + 65 minutos
```

Nenhum campo temporal deve ser calculado a partir de uma fonte independente ou de um deslocamento posicional alternativo.

## Proprietario da derivacao

A auditoria estrutural da arquitetura atual encontrou:

- `ingestion/loader.py`: le respostas Bybit e cria tabela bruta;
- `ingestion/normalize.py`: converte `timestamp_open`, conhece UTC e o timeframe de 5 minutos;
- `dataset/schema.py`: declara e valida o schema OHLCV;
- `dataset/builder.py`: compoe features e target, mas nao conhece hoje `candle_close_ts` nem `target_ts`;
- nao existe uma camada temporal intermediaria dedicada.

A responsabilidade normativa fica definida em duas etapas, sem criar um novo componente nesta S3:

1. `ingestion/normalize.py` sera o proprietario da derivacao de `candle_close_ts`, porque e a camada que conhece a semantica da vela e o intervalo de 5 minutos;
2. `dataset/builder.py` consumira `candle_close_ts` e derivara somente:

```text
decision_ts = candle_close_ts
target_ts = decision_ts + 1 hora
```

O Builder nao deve reconstruir `candle_close_ts` diretamente de `candle_open_ts` depois que a representacao canonica temporal existir.

## Associacao do target

A linha com `decision_ts = T` representa uma decisao tomada no fechamento da vela completa. O target deve representar:

```text
future_return_1h = log(close(target_ts) / close(decision_ts))
```

A formula posicional do Gate 7 permanece preservada, desde que o indice `t` seja associado ao `decision_ts` derivado do fechamento:

```text
decision_ts(t) = candle_close_ts(t)
target_ts(t) = decision_ts(t) + 1 hora
```

O Builder nao desloca, recalcula ou altera o target recebido.

## Schema temporal do dataset reconciliado

A saida temporal deve conter:

```text
asset_id
candle_open_ts
candle_close_ts
decision_ts
target_ts
```

seguida pelas dez features V1 e pelos dois campos de target. A ordem final e uma decisao de S4, mas os quatro campos temporais sao obrigatorios para auditoria e rastreabilidade.

## Invariantes verificaveis

```text
candle_close_ts - candle_open_ts == 5 minutos
decision_ts == candle_close_ts
target_ts - decision_ts == 1 hora
target_ts > decision_ts
```

A ordem cronologica deve ser preservada por ativo. As features devem usar somente informacao disponivel ate `decision_ts`. O target pode usar o futuro posterior a `decision_ts` exclusivamente como variavel supervisionada.

## DQC habilitado pela representacao

A representacao permite verificar explicitamente:

- fechamento derivado do inicio da vela;
- decisao igual ao fechamento;
- horizonte do target igual a uma hora;
- target posterior a decisao;
- separacao entre features e target;
- proveniencia temporal das features, quando fornecida;
- coerencia entre target recebido e seus timestamps.

A implementacao ou revisao das regras DQC pertence a S7, nao a esta especificacao.

## Invariantes do Gate 8 preservados

A reconciliacao deve preservar:

- alinhamento features/target pela mesma observacao logica;
- rejeicao de entrada temporalmente incompatÃ­vel;
- unicidade da chave de decisao;
- exclusao de linhas com `NaN` ou `+/-inf`;
- nao mutacao das entradas;
- determinismo;
- escrita Parquet separada da composicao;
- ausencia de split, purge, embargo, modelo e backtest nesta etapa.

A alteracao semantica especifica e somente:

```text
decision_ts = candle_open_ts
```

para:

```text
decision_ts = candle_close_ts
```

## Estado S3

```text
campos temporais                 CONGELADOS
fonte de verdade                 candle_open_ts
candle_close_ts                  derivado na normalizacao
decision_ts                      derivado no Builder a partir do fechamento
target_ts                        derivado no Builder a partir da decisao
camada temporal intermediaria    nao necessaria no estado atual
Gate 8 historico                 preservado
Gate 9                          bloqueado
```

A S3 esta encerrada como especificacao. Nenhuma alteracao de codigo, teste, configuracao ou artefato foi aplicada nesta fase.
