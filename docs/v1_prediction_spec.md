# Especificacao V1: previsao da direcao no proximo horizonte

## Status

- **Versao:** V1
- **Status:** especificacao inicial
- **Objetivo:** definir uma tarefa preditiva simples, temporal e auditavel
- **Escopo:** demonstrar ganho preditivo fora da amostra antes de adicionar hipoteses experimentais

## 1. Objetivo operacional

O app devera estimar, no instante de decisao `T`, a probabilidade de o retorno acumulado de um ativo ser positivo em um horizonte futuro definido:

$$
P\left(Y_T^{(H)} = 1 \mid X_T\right)
$$

onde:

- $T$ e o fechamento do ultimo candle completo disponivel;
- $X_T$ contem somente informacoes disponiveis ate $T$;
- $H$ e o horizonte em numero de candles;
- $P_T$ e o preco de referencia no instante de decisao;
- $P_{T+H}$ e o preco de referencia no fim do horizonte;
- $\epsilon$ e o limiar minimo de retorno, inicialmente igual a zero.

O retorno futuro e:

$$
r_T^{(H)} = \ln\left(\frac{P_{T+H}}{P_T}\right)
$$

E o alvo binario e:

$$
Y_T^{(H)} =
\begin{cases}
1, & \text{se } r_T^{(H)} > \epsilon \\
0, & \text{caso contrario}
\end{cases}
$$

Na V1:

$$
\epsilon = 0
$$

Portanto, a tarefa nao e prever o preco exato. Ela e estimar a probabilidade de o preco terminar acima do preco observado em `T` ao final do horizonte.

## 2. Unidade temporal e horizonte V1

A unidade temporal da V1 sera o candle de **5 minutos**, com timestamp de abertura. Um candle com `timestamp_open = 10:00` representa o intervalo `[10:00, 10:05)` e so estara completo no instante `10:05`.

O timestamp de abertura identifica o intervalo observado; o timestamp de fechamento representa o instante em que os dados podem ser usados para gerar a previsao.

O horizonte inicial sera de **1 hora**. Para candles de 5 minutos:

$$
H = \frac{60}{5} = 12\ candles
$$

O modelo usara como observacao os ultimos 6 horas de candles completos:

Logo:

$$
W = 6 \times 12 = 72\ candles
$$

O fluxo no instante `T` sera:

$$
X_T = \{C_{T-W+1}, \ldots, C_T\}
\longrightarrow P\left(Y_T^{(12)}=1 \mid X_T\right)
$$

A previsao sera produzida a cada 5 minutos, usando sempre o candle mais recentemente fechado. A pergunta operacional da V1 sera:

> Com os dados disponiveis no fechamento `T`, qual e a probabilidade de o retorno acumulado dos proximos 60 minutos ser positivo?

`W` e `H` devem ser configuraveis no codigo, mas os valores padrao da V1 serao 72 e 12, respectivamente.

## 3. Informacao permitida e causalidade

As features devem respeitar a regra de disponibilidade temporal:

$$
X_T \subseteq D_{\leq T}
$$

Nenhuma feature pode depender, direta ou indiretamente, de:

$$
D_{>T}
$$

Isso inclui vazamento por:

- normalizacao calculada usando o dataset inteiro;
- imputacao ajustada com dados futuros;
- indicadores calculados depois do instante `T`;
- selecao de features usando o conjunto de teste;
- janelas que ultrapassem `T`;
- qualquer agregacao que use observacoes posteriores.

O futuro usado para construir $Y_T^{(H)}$ existe exclusivamente para avaliacao posterior e nunca pode entrar nas features de `T`.

### Features previstas para a V1

O baseline supervisionado inicial usara exatamente estas 10 features:

| Feature | Definicao |
|---|---|
| `ret_5m` | retorno do ultimo candle |
| `ret_15m` | retorno acumulado dos ultimos 15 minutos |
| `ret_1h` | retorno acumulado dos ultimos 60 minutos |
| `ret_3h` | retorno acumulado dos ultimos 3 horas |
| `vol_1h` | volatilidade dos ultimos 60 minutos |
| `vol_6h` | volatilidade dos ultimos 6 horas |
| `volume_rel_1h` | volume atual relativo a media recente de volume |
| `range_5m` | `(high - low) / close` do ultimo candle |
| `range_1h` | amplitude de preco do periodo de 1 hora |
| `volume_trend` | tendencia do volume recente |

Cada feature deve ser uma funcao causal dos dados disponiveis:

$$
X_T = f(D_{\leq T})
$$

Nenhuma feature pode consultar $D_{>T}$. As janelas devem deslocar-se com `T`, e o primeiro exemplo so pode ser construido quando houver historico suficiente para todas as features e para a janela minima de 72 candles. Nao deve haver preenchimento artificial do passado.

Toda feature derivada deve ser calculada causalmente, com uma janela que se desloca junto com `T`. E proibido calcular features sobre o dataset inteiro e somente depois dividir treino, validacao e teste.

### Extensoes posteriores

As seguintes familias nao fazem parte do modelo inicial:

- $R_t$;
- informacao mutua calculada em janela passada;
- caracteristicas de TDA;
- $\Omega_H(t)$.

Essas extensoes deverao ser adicionadas individualmente, mantendo a mesma divisao temporal e o mesmo protocolo de avaliacao.

## 4. Divisao temporal e purge

A avaliacao deve preservar a ordem cronologica:

```text
passado                                  futuro
|-------------- treino --------------|-- validacao --|---- teste ---->
                                     tuning          avaliacao final
```

Divisao inicial:

- 60% mais antigo: treino;
- 20% seguinte: validacao;
- 20% mais recente: teste final.

Como o alvo usa um horizonte de 60 minutos, cada fronteira entre conjuntos deve reservar um **purge temporal minimo de 60 minutos** quando exemplos do conjunto anterior ainda tiverem rotulos que alcancem o periodo seguinte.

```text
TREINO                  PURGE                  VALIDACAO
|-------------------|<------ 60 min ------>|-------------------|
```

O mesmo cuidado deve ser aplicado entre validacao e teste. O purge remove exemplos da borda; ele nao altera a ordem cronologica nem permite reutilizar o futuro.

O conjunto de teste deve permanecer intocado ate que:

1. o pipeline de features esteja definido;
2. o baseline esteja treinado;
3. hiperparametros tenham sido escolhidos usando treino e validacao;
4. a especificacao da comparacao esteja congelada.

### Proibido

- embaralhar observacoes antes da divisao;
- fazer split aleatorio de treino e teste;
- ajustar transformacoes com dados de validacao ou teste;
- usar o teste para escolher features, hiperparametros ou modelos.

### Evolucao planejada

Depois do holdout temporal inicial, a avaliacao devera evoluir para walk-forward validation, com treino, validacao e teste respeitando a ordem temporal em cada janela.

## 5. Schema temporal minimo

Cada registro de candle devera conter, no minimo:

| Campo | Semantica |
|---|---|
| `timestamp_open` | inicio do intervalo de 5 minutos, em UTC |
| `timestamp_close` | instante de fechamento do candle, em UTC |
| `open` | preco de abertura |
| `high` | maior preco do intervalo |
| `low` | menor preco do intervalo |
| `close` | preco no fechamento do intervalo |
| `volume` | volume negociado no intervalo |

Regras temporais do schema:

- timestamps devem ser representados internamente em UTC;
- `timestamp_close` e o timestamp canonico de decisao;
- para um candle iniciado em `10:00`, `timestamp_close` e `10:05`;
- a linha de previsao em `T` usa somente candles cujo fechamento seja menor ou igual a `T`;
- o label de `T` usa o preco em `T+H` e nao e uma feature.

Uma linha experimental deve ser interpretavel como:

```text
dados disponiveis ate T -> modelo -> P(Y em T+1h)
                              |
                              +-> futuro T ate T+1h, usado somente no label
```

## 6. Sobreposicao dos horizontes

Com previsoes a cada 5 minutos, os horizontes se sobrepoem:

```text
10:00 -> 11:00
10:05 -> 11:05
10:10 -> 11:10
```

Isso e permitido para o fluxo de producao, mas cria dependencia entre observacoes. A avaliacao nao deve tratar todos os erros como completamente independentes. Nas etapas posteriores, deverao ser considerados:

- walk-forward validation;
- erros agrupados por periodo;
- intervalos de confianca robustos;
- uma analise de sensibilidade com pontos nao sobrepostos.

## 7. Baselines obrigatorios

### Baseline 0: probabilidade historica

O primeiro ponto de comparacao sera um baseline ingenuo que estima uma probabilidade constante a partir do treino:

$$
p_0 = \frac{\sum_{T \in Train} Y_T}{N_{Train}}
$$

Para todas as observacoes de validacao e teste:

$$
\hat{p}_T = p_0
$$

Esse modelo nao usa features e responde qual probabilidade atribuir com base apenas na frequencia historica de altas.

### Baseline 1: regressao logistica

O primeiro modelo supervisionado sera uma regressao logistica com as 10 features definidas acima e regularizacao L2. O modelo deve produzir diretamente:

$$
\hat{p}_T = P\left(Y_T^{(H)}=1 \mid X_T\right)
$$

A regressao logistica foi escolhida por ser simples, interpretavel, rapida, probabilistica e adequada como referencia para extensoes posteriores.

Antes do treinamento, as features continuas serao padronizadas usando somente estatisticas do conjunto de treino:

$$
z_T = \frac{x_T - \mu_{train}}{\sigma_{train}}
$$

Os mesmos $\mu_{train}$ e $\sigma_{train}$ serao aplicados a validacao e teste. Media e desvio nunca serao recalculados usando dados futuros ou o conjunto de teste.

Nenhum modelo posterior sera considerado bem-sucedido sem superar o Baseline 0 fora da amostra.

## 8. Sequencia de ablacoes

A comparacao sera incremental:

| Modelo | Informacao adicionada |
|---|---|
| B0 | Probabilidade historica |
| B1 | Regressao logistica L2 + 10 features causais |
| B1 + R | B1 + $R_T$ |
| B1 + R + I | B1 + $R_T$ + informacao mutua |
| B1 + R + I + TDA | Modelo anterior + caracteristicas TDA |
| Completo + $\Omega_H$ | Modelo anterior + $\Omega_H$ |

Cada camada deve ser avaliada isoladamente para responder se ela acrescenta informacao preditiva. A inclusao de uma feature nao deve alterar a regra de divisao temporal nem o conjunto de metricas.

Se uma feature for escolhida por ter melhorado o resultado no teste, ela devera ser tratada como uma nova hipotese e reavaliada em um novo ciclo temporal. O teste nao pode se transformar, mesmo inadvertidamente, em conjunto de treinamento.

## 9. Metricas

### Principal

**Log Loss** sera a metrica principal:

$$
LL = -\frac{1}{N}\sum_{i=1}^{N}
\left[y_i\log(p_i) + (1-y_i)\log(1-p_i)\right]
$$

Valores menores sao melhores. As probabilidades devem ser limitadas numericamente antes do calculo para evitar `log(0)`.

### Secundarias

- **Brier Score:**

  $$
  BS = \frac{1}{N}\sum_{i=1}^{N}(p_i-y_i)^2
  $$

- AUC-ROC;
- acuracia;
- balanced accuracy;
- matriz de confusao.

Acuracia e balanced accuracy serao tratadas como referencias de classificacao, nao como criterio principal de sucesso.

## 10. Criterio de sucesso

O criterio inicial sera melhoria fora da amostra em relacao ao Baseline 0, e nao um limiar arbitrario de acuracia.

Para log loss:

$$
\Delta LL = LL_{baseline} - LL_{modelo}
$$

Interpretacao:

- $\Delta LL > 0$: o modelo melhora o baseline;
- $\Delta LL = 0$: nao ha melhoria;
- $\Delta LL < 0$: o modelo piora o baseline.

Para Brier Score:

$$
\Delta BS = BS_{B0} - BS_{modelo}
$$

Para a comparacao principal entre B0 e B1, a evidencia inicial de ganho exige:

$$
\Delta LL > 0 \quad \land \quad \Delta BS > 0
$$

O mesmo criterio incremental sera usado para avaliar as extensoes. Cada etapa deve demonstrar ganho fora da amostra em relacao ao modelo imediatamente anterior e continuar sendo comparada ao B0.

Uma melhoria observada nao sera considerada suficiente por si so. A analise devera incluir:

- intervalos de confianca;
- consistencia entre periodos;
- sensibilidade a hiperparametros;
- verificacao contra sobreajuste;
- posteriormente, validacao walk-forward.

## 11. Custos e utilidade economica

A primeira fase avalia capacidade preditiva estatistica. Custos de operacao serao incluidos em uma segunda camada de avaliacao, depois que houver evidencia preditiva fora da amostra.

O retorno liquido sera definido como:

$$
retorno\ liquido = retorno\ bruto - custos
$$

Os custos deverao contemplar, conforme disponibilidade dos dados:

- spread;
- taxas;
- slippage;
- custos de execucao.

Um modelo pode melhorar a metrica preditiva e ainda ser economicamente inutil. Por isso, desempenho estatistico e desempenho liquido devem permanecer como resultados distintos.

## 12. Fluxo auditavel

A sequencia da V1 e:

$$
D_{\leq T}
\longrightarrow X_T
\longrightarrow P\left(Y_T^{(H)}=1\right)
\longrightarrow avaliacao\ temporal
$$

A extensao experimental segue:

$$
X_T
\longrightarrow [R_T, I_T, H_k, \Omega_H]
\longrightarrow P\left(Y_T^{(H)}=1\right)
$$

Cada extensao deve ser comparada ao modelo imediatamente anterior e ao baseline original.

## 13. Decisoes e limites da V1

- O alvo e binario e baseado no retorno logaritmico futuro.
- O limiar inicial e $\epsilon=0$.
- A granularidade e 5 minutos.
- Timestamps sao armazenados em UTC.
- O timestamp canonico de decisao e `timestamp_close`.
- A janela historica padrao e `W=72` candles completos, ou 6 horas.
- O horizonte padrao e 1 hora.
- Para candles de 5 minutos, o horizonte e 12 candles.
- A previsao ocorre a cada 5 minutos.
- Features devem usar somente informacoes disponiveis ate `T`.
- A divisao inicial e 60% treino, 20% validacao e 20% teste.
- O purge minimo nas fronteiras e de 60 minutos quando houver sobreposicao de rotulos.
- Horizontes sobrepostos sao permitidos, mas exigem tratamento estatistico posterior.
- O teste final fica reservado para a avaliacao final.
- Log loss e a metrica principal.
- O baseline historico e obrigatorio.
- $\Omega_H$ e uma extensao experimental, nao uma premissa de utilidade.
- Custos entram em avaliacao economica posterior.

## 14. Proximos passos tecnicos

1. Fechar o contrato OHLCV e a validacao de qualidade dos dados.
2. Implementar o schema temporal com UTC e timestamps de abertura e fechamento.
3. Implementar a construcao causal de janelas com `W=72`.
4. Implementar a construcao do alvo com `H=12`.
5. Implementar o split temporal sem embaralhamento e com purge.
6. Implementar o baseline historico.
7. Implementar o modelo supervisionado simples.
8. Implementar log loss, Brier Score, AUC-ROC, balanced accuracy e matriz de confusao.
9. Produzir um relatorio comparando baseline e modelo fora da amostra.
10. Adicionar extensoes experimentais uma por vez.

## 15. Contrato do dataset de decisoes

O dataset supervisionado nao representa simplesmente candles. Cada linha representa uma decisao de previsao para uma chave unica:

```text
(asset_id, decision_ts)
```

As colunas sao separadas por funcao:

| Grupo | Colunas V1 |
|---|---|
| Identidade temporal | `asset_id`, `decision_ts`, `candle_open_ts`, `candle_close_ts`, `target_ts` |
| Observacao OHLCV | `open`, `high`, `low`, `close`, `volume` |
| Features causais | `ret_5m`, `ret_15m`, `ret_1h`, `ret_3h`, `vol_1h`, `vol_6h`, `range_5m`, `range_1h`, `volume_rel_1h`, `volume_trend` |
| Auditoria do futuro | `future_return_1h`, `target_direction` |
| Versionamento | `dataset_version`, `feature_schema_version` |

`future_return_1h` e `target_direction` sao campos de auditoria e rotulo. Nunca podem fazer parte de `FEATURE_COLUMNS`. O dataset de inferencia pode omitir esses dois campos quando o futuro ainda nao estiver disponivel.

As listas canonicas devem ser mantidas explicitamente no codigo:

```text
FEATURE_COLUMNS = [
  ret_5m, ret_15m, ret_1h, ret_3h,
  vol_1h, vol_6h,
  range_5m, range_1h,
  volume_rel_1h, volume_trend,
]

TARGET_COLUMNS = [future_return_1h, target_direction]

AUDIT_COLUMNS = [
  asset_id, decision_ts, candle_open_ts,
  candle_close_ts, target_ts,
  dataset_version, feature_schema_version,
]
```

## 16. Regras de construcao de cada linha

Uma linha supervisionada em `T` so pode ser criada quando todas as condicoes abaixo forem satisfeitas:

1. O candle mais recente tem `candle_close_ts <= decision_ts`.
2. Os 72 candles de observacao estao completos e em ordem cronologica.
3. O `candle_close_ts` do ultimo candle e exatamente `decision_ts`.
4. Os 12 candles futuros necessarios para o alvo existem e estao completos.
5. `target_ts = decision_ts + 1 hora`.
6. Nao ha lacunas na sequencia esperada de 5 minutos.
7. Todos os campos necessarios para as features e o alvo passam o DQC.

Se o futuro ainda nao existir, a linha pode ser produzida para inferencia, mas deve permanecer fora do dataset supervisionado de treino, validacao e teste.

Nao deve haver preenchimento artificial de OHLCV ou features de mercado. Em particular, sao proibidos `ffill`, `bfill`, media global e zero arbitrario. Uma feature nao calculavel deve permanecer como `NaN` e a linha deve ser rejeitada pelo contrato do modelo antes do treinamento.

## 17. Contrato DQC V1

O contrato operacional, incluindo a matriz DQ-001 a DQ-030, estados, severidades e efeitos, esta em [dqc_v1_contract.md](dqc_v1_contract.md). A fonte normativa da numeracao e [configs/dqc_v1.yaml](../configs/dqc_v1.yaml); esta especificacao nao duplica a matriz.

`DQ-006` deve capturar ausencia antes de qualquer verificacao de finitude dependente; regras posteriores que dependem de uma pre-condicao falha devem ser marcadas como nao avaliaveis, e nao como novas falhas independentes.

## 18. Protocolo de particionamento temporal

O particionamento deve ser feito por limites temporais, nunca por embaralhamento. Para cada ativo, o dataset final deve obedecer:

```text
decision_ts crescente
    |
    v
TRAIN | PURGE | VALIDATION | PURGE | TEST
 60%             20%                 20%
```

O procedimento V1 e:

1. Ordenar por `asset_id` e `decision_ts`.
2. Determinar os limites de tempo usando somente `decision_ts`.
3. Definir os blocos cronologicos de 60%, 20% e 20%.
4. Remover da borda de cada bloco exemplos cujo intervalo de rotulo atravesse o limite seguinte.
5. Aplicar purge minimo de 60 minutos, equivalente a `H=12` candles.
6. Ajustar o scaler e treinar o modelo somente no treino restante.
7. Usar validacao para escolhas de modelo e hiperparametros.
8. Avaliar no teste apenas depois de congelar todas as decisoes.

O purge e medido em tempo de decisao. Se `T_train + 1 hora` alcancar ou ultrapassar o inicio da validacao, o exemplo de treino deve ser removido. A mesma regra vale entre validacao e teste. Se houver multiplos ativos, o corte deve ser aplicado por ativo ou por uma fronteira temporal global previamente documentada; nao se deve misturar exemplos de ativos para encobrir uma violacao temporal.

O embargo e um intervalo adicional opcional apos o purge. Na V1, seu valor padrao sera zero alem do purge de 1 hora, mas ele deve ser configuravel para experimentos com maior dependencia temporal.

## 19. Walk-forward validation

Depois do holdout inicial, o protocolo walk-forward devera usar janelas crescentes ou deslizantes:

```text
treino 1       validacao 1  teste 1
|------------|------------|---------->

treino 2            validacao 2  teste 2
|-----------------|------------|---------->
```

Para cada janela:

- o treino ocorre apenas no passado da janela;
- o scaler e ajustado novamente no treino daquela janela;
- features e rotulos sao recalculados ou filtrados com a mesma regra causal;
- purge e embargo sao aplicados antes do ajuste;
- o teste da janela nao participa de selecao ou recalibracao;
- as previsoes sao agregadas somente depois de todas as janelas terminarem.

Como os horizontes de 1 hora se sobrepoem, os intervalos de confianca nao devem assumir independencia simples entre todas as previsoes. A V1 deve registrar o numero de observacoes, o numero de janelas, os periodos cobertos e a politica usada para agrupar erros.

## 20. Criterios de liberacao do dataset

Um dataset supervisionado so pode ser consumido pelo treinamento se:

- todas as regras DQ obrigatorias tiverem passado;
- nao houver duplicidade na chave primaria;
- nao houver lacunas dentro das janelas usadas;
- o primeiro e o ultimo `decision_ts` de cada particao estiverem registrados;
- o purge aplicado estiver registrado;
- `dataset_version` e `feature_schema_version` estiverem preenchidos;
- as listas de features, targets e auditoria estiverem congeladas;
- houver uma contagem auditavel de linhas aceitas e rejeitadas por regra.

O relatorio de qualidade deve distinguir pelo menos:

```text
accepted_rows
rejected_rows
rejection_count_by_rule
train_rows
validation_rows
test_rows
purged_rows
first_decision_ts
last_decision_ts
dataset_version
feature_schema_version
```

Sem esse relatorio, o dataset nao deve ser tratado como pronto para modelagem.
