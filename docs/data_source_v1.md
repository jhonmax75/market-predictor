# Fonte de mercado V1

## Decisao

- **Fonte primaria:** Bybit Spot REST API V5
- **Ativo:** `BTCUSDT`
- **Mercado:** Spot
- **Instrumento:** `BTCUSDT`
- **Timeframe:** candles de 5 minutos (`interval=5`)
- **Timezone canonico:** UTC
- **Status do Gate 2:** aprovado para a fonte primaria da V1

A fonte foi escolhida para a V1 por oferecer OHLCV, intervalo de 5 minutos, parametros temporais de consulta e uma semantica explicita de abertura do candle. A ordem reversa da resposta REST e uma transformacao deterministica do normalizador, nao uma falha de reprodutibilidade.

## Endpoint e formato

Endpoint publico usado:

```text
GET https://api.bybit.com/v5/market/kline
```

Parametros V1:

```text
category=spot
symbol=BTCUSDT
interval=5
limit=1000
```

Parametros opcionais para paginas temporais:

```text
start=<epoch_milliseconds>
end=<epoch_milliseconds>
```

A resposta possui a estrutura geral:

```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "category": "spot",
    "symbol": "BTCUSDT",
    "list": [
      [
        "startTime",
        "openPrice",
        "highPrice",
        "lowPrice",
        "closePrice",
        "volume",
        "turnover"
      ]
    ]
  }
}
```

A V1 usa os seis primeiros campos necessarios para OHLCV e registra `turnover` como campo bruto opcional, sem usa-lo como feature do baseline.

## Semantica dos timestamps

O primeiro campo de cada candle e o **timestamp de abertura do intervalo**, em epoch milliseconds UTC. Ele nao representa o fechamento.

Para um candle com `startTime = T`:

```text
candle_open_ts  = T
candle_close_ts = T + 5 minutos
```

Consequentemente:

- o candle `[10:00, 10:05)` possui `candle_open_ts = 10:00`;
- ele so pode ser usado para uma decisao em `decision_ts = 10:05`;
- o timestamp recebido da Bybit nunca deve ser copiado diretamente como `decision_ts`;
- o candle atual/incompleto deve ser excluido da construcao supervisionada;
- o campo `confirm` do WebSocket pode ser usado em ingestao ao vivo para confirmar o fechamento, mas a V1 historica usa a regra temporal acima.

A convencao interna sera:

```text
Bybit startTime         -> candle_open_ts
candle_open_ts + 5m     -> candle_close_ts
candle_close_ts         -> decision_ts do exemplo
```

`candle_close_ts` e uma convencao derivada pela V1; nao e um timestamp fornecido pela resposta REST historica. O codigo nunca deve atribuir diretamente o `startTime` recebido a `decision_ts`.

```text
Bybit startTime
  -> candle_open_ts
  -> + 5 minutos
  -> candle_close_ts
  -> decision_ts
```

Todos os timestamps devem ser convertidos para `datetime64[ns, UTC]` antes do DQC.

## Limites e cobertura

- O endpoint aceita no maximo 1.000 candles por requisicao.
- A janela de observacao de 72 candles inclui o candle cuja `candle_close_ts` constitui o `decision_ts`.
- Portanto, uma linha supervisionada completa requer 72 candles de observacao mais 12 candles posteriores, totalizando 84 candles.
- Uma consulta inicial de 84 candles cobre exatamente essa necessidade minima, sem substituir a validacao de continuidade.
- A cobertura historica efetivamente disponivel deve ser medida durante a ingestao; a existencia do endpoint nao garante ausencia de lacunas em todo o periodo desejado.
- O cliente deve registrar `retCode`, `retMsg`, parametros, quantidade retornada e o intervalo temporal de cada pagina.

## Politica de paginacao

A ingestao historica sera deterministica e baseada em janelas UTC:

1. definir `start` e `end` em epoch milliseconds;
2. consultar no maximo 1.000 candles por pagina;
3. armazenar a resposta bruta antes da normalizacao;
4. converter o timestamp de abertura para UTC;
5. ordenar crescentemente por `asset_id` e `candle_open_ts`;
6. remover o candle duplicado na fronteira somente quando a chave for identica e a resposta vier repetida pela pagina; registrar a ocorrencia;
7. verificar continuidade de 5 minutos antes de construir features;
8. avancar a janela sem depender da ordem reversa retornada pela API.

A resposta REST da Bybit foi observada em ordem decrescente de `startTime`. Essa ordem deve ser tratada como comportamento de transporte: o dataset canonico sempre sera crescente.

## Politica de retries

- Nao repetir automaticamente erros 4xx permanentes, parametros invalidos ou instrumento inexistente.
- Repetir respostas `429`, erros `5xx` e falhas transientes de rede.
- Usar backoff exponencial limitado, com jitter configuravel no cliente.
- Respeitar os headers de rate limit retornados pela API.
- Registrar numero da tentativa, status HTTP, `retCode`, intervalo solicitado e tempo de espera.
- Encerrar com erro apos o numero maximo de tentativas, sem produzir pagina parcialmente aceita.
- A resposta deve ter `retCode == 0`; caso contrario, a pagina fica invalida para o DQC.

## Data da coleta de verificacao

- **Data:** 2026-09-15
- **Endpoint consultado:** `https://api.bybit.com/v5/market/kline`
- **Consulta:** `category=spot&symbol=BTCUSDT&interval=5&limit=84`
- **Retorno:** `retCode=0`, `retMsg=OK`

## Inspecao manual da amostra

Amostra adquirida para o Gate 2:

| Verificacao | Resultado |
|---|---|
| Candles retornados | 84 |
| Campos por candle | 7 |
| Primeiro timestamp recebido | `2026-09-15 20:50:00 UTC` |
| Ultimo timestamp recebido | `2026-09-15 13:55:00 UTC` |
| Ordem REST | decrescente |
| Intervalo minimo observado | 5 minutos |
| Intervalo maximo observado | 5 minutos |
| OHLCV presentes | sim |
| Volume presente | sim |
| Candle atual excluido | regra do normalizador |

A amostra confirma que a API fornece a granularidade e os campos necessarios. Ela nao substitui a validacao DQC da serie historica completa: gaps, duplicidades, candle atual e continuidade permanecem verificacoes obrigatorias.

## Reprodutibilidade

Uma coleta deve ser reproduzivel a partir de:

- fonte e endpoint;
- ativo e categoria;
- intervalo `5m`;
- `start` e `end` UTC;
- parametros completos da requisicao;
- data/hora da coleta;
- resposta bruta preservada;
- versao do normalizador;
- `dataset_version` e `feature_schema_version`.

A V1 nao usara dados de mercado de fontes diferentes na mesma serie. Qualquer troca de fonte, mercado, instrumento ou politica de ajuste exige nova versao do dataset e nova aprovacao do Gate 2.

## Referencia documental

- [Bybit V5 Get Kline](https://bybit-exchange.github.io/docs/v5/market/kline)
- [Bybit V5 WebSocket Public Kline](https://bybit-exchange.github.io/docs/v5/websocket/public/kline)
