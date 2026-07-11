# ADR 02: Uso do MLflow para Rastreamento de Experimentos e Versionamento de Modelos

## Status
Aprovado

## Contexto
O projeto inclui uma etapa de Machine Learning (treinamento e serving). Para garantir a reprodutibilidade dos modelos e auditoria dos experimentos, é fundamental adotar práticas de MLOps que registrem os hiperparâmetros utilizados, as métricas obtidas e o modelo gerado. Sem um sistema de rastreamento, o processo de treinamento e atualização de modelos torna-se opaco e difícil de depurar.

## Decisão
Decidimos utilizar o **MLflow** como ferramenta central de rastreamento de experimentos (tracking) e registro de modelos (Model Registry). 

Os detalhes da implementação incluem:
1. **Rastreamento de Hiperparâmetros**: Registrar os parâmetros de configuração do classificador RandomForest, como `n_estimators` e `max_depth`.
2. **Log de Métricas**: Registrar acurácia, precisão, recall e f1-score do modelo de teste a cada execução.
3. **Artefatos de Validação**: Logar a imagem da matriz de confusão em formato PNG na run do experimento para análise visual rápida.
4. **Armazenamento do Modelo**: Registrar e versionar o modelo resultante usando `mlflow.sklearn.log_model`.

## Consequências
- A pasta local `mlruns/` será gerada na raiz do projeto durante o desenvolvimento (e foi incluída no `.gitignore` para não sobrecarregar o repositório Git).
- O script de serving carrega o arquivo serializado `model.pkl` de uma pasta fixa local exportada pelo script de treino, mantendo a API independente do servidor do MLflow ativo em runtime, o que reduz pontos únicos de falha.
- É possível iniciar a interface visual do MLflow executando `mlflow ui` para analisar graficamente o histórico de execuções.
