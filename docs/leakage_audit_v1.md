# Leakage audit V1

## Objetivo

Validar que o pipeline de dados e de dataset da V1 preserva causalidade temporal. O critério principal não é apenas "os testes passam", mas "o pipeline não usa futuro em nenhuma etapa anterior ao target".

## Regras centrais

1. Features não podem consultar `D_{>T}`.
2. O target não pode entrar nas features.
3. O scaler, quando existir, deve ser ajustado somente no treino.
4. O split temporal deve preservar ordem e não permitir contaminação.
5. Qualquer imputação ou correção deve ser feita sem usar informação do futuro.
6. O `DQ-024` continua sendo especialmente importante no contexto de leakage.

## Propriedades verificáveis

### Features

Se alterarmos `t + 1`, então:

```text
features(t)
```

devem permanecer inalterado. Isso torna a causalidade uma propriedade verificável.

### Target

O target deve ser construído somente após a janela causal de observação e o horizonte de futuro:

```text
decision_ts(t)
  -> close(t)
  -> close(t + 12)
  -> future_return_1h
  -> target_direction
```

O cálculo do alvo nunca deve depender de valores de features calculadas a partir de dados futuros.

### Split temporal

A validade temporal exige:

```text
max(train) < min(validation)
max(validation) < min(test)
```

Além disso:

```text
shuffle = false
```

Sem esse comportamento, a janela temporal deixa de representar uma sequência causal real.

## Checklist de auditoria

- feature usa futuro? Não
- target entra nas features? Não
- scaler vê validation/test no fit? Não
- split temporal contaminado? Não
- imputação usa futuro? Não
- overlap indevido? Não
- dados de teste influenciam treinamento? Não
- purge aplicado conforme configuração? Sim
- embargo respeitado? Sim

## Política de purge

Na V1, a política mínima de purge entre conjuntos é de 60 minutos, correspondente ao horizonte de target ou à janela mínima em tempo de decisão. O purge deve ser aplicado antes da etapa final de dataset e sempre registrado no relatório de qualidade.

## Resultado esperado

A auditoria de leakage deve concluir que:

```text
sem vazamento temporal
sem contaminação do split
sem futura informação em features
sem escalonamento com dados fora do treino
```

A falha deste critério deve ser tratada como `FAIL` de pipeline, independentemente do desempenho do modelo.

## Artefato de evidência

O relatório final deve registrar:

- conjuntos train/validation/test e suas fronteiras temporais;
- quantidade de linhas removidas por purge;
- qualquer janela de embargo;
- confirmação de que a ordem cronológica foi preservada;
- confirmação de que `DQ-024` foi respeitado;
- conclusão da auditoria em termos de "pass" ou "fail".

O leakage audit não é um checklist opcional. Ele é parte do contrato de validade da V1.
