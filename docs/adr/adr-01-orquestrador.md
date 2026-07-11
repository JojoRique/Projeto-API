# ADR 01: Escolha do Dagster como Orquestrador de Dados

## Status
Aprovado

## Contexto
O projeto exige a implementação de um pipeline de dados ponta a ponta (ingestão de API -> transformação -> data quality -> ML integration). Tradicionalmente, o Apache Airflow é utilizado para orquestrar fluxos de trabalho usando DAGs baseadas em tarefas (Task-Based). No entanto, o paradigma moderno de engenharia de dados foca na governança dos dados em si e na sua linhagem (Data-Centric / Software-Defined Assets), onde cada etapa do pipeline produz um ativo físico de dados no storage.

Além disso, para operações e testes locais em ambiente de desenvolvimento (Windows com Docker/Kind), a infraestrutura do Airflow pode ser excessivamente pesada (exigindo containers de Postgres, Redis, Webserver, Scheduler e Worker), o que consome muitos recursos locais.

## Decisão
Decidimos utilizar o **Dagster** como o orquestrador do pipeline de dados e MLOps. 

Os fatores decisivos foram:
1. **Ativos Definidos por Software (Software-Defined Assets)**: O Dagster nos permite declarar cada etapa (ingestão, transformação, modelo treinado e drift report) como um ativo que depende de outros, fornecendo linhagem e rastreabilidade natural.
2. **Leveza Local**: O Dagster Webserver roda diretamente em Python localmente com pouquíssima sobrecarga de memória e CPU, facilitando testes locais e no CI.
3. **Métricas de Qualidade Integradas**: Ele permite logar metadados detalhados de cada execução diretamente na UI do Dagster (por exemplo, contagem de linhas e distribuição de classes de cores).

## Consequências
- A orquestração está centralizada em `src/pipeline.py`.
- O ambiente local de desenvolvimento precisa instalar os pacotes `dagster` e `dagster-webserver` via `requirements.txt`.
- O fluxo de dados é facilmente testável usando o módulo nativo de teste de assets do Dagster.
