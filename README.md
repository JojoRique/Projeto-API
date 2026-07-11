# Church Calendar DevOps & MLOps Pipeline 📅⛪

Este repositório contém a implementação prática e incremental de um pipeline de engenharia de dados e MLOps ponta a ponta. O projeto consome dados da API pública do Calendário Litúrgico da Igreja (Church Calendar API), realiza transformações e validações de qualidade de dados, executa treinamento de modelo preditivo rastreado pelo MLflow, monitora drift de dados com Evidently, e serve predições em Kubernetes local (Kind) usando Helm Charts.

[![CI Pipeline](https://github.com/JojoRique/Projeto-API/actions/workflows/ci.yml/badge.svg)](https://github.com/JojoRique/Projeto-API/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](requirements.txt)
[![Kubernetes](https://img.shields.io/badge/kubernetes-v1.30-blue.svg)](k8s-kind-config.yaml)

---

## 🛠️ Arquitetura do Sistema

A arquitetura do projeto segue princípios modernos de Engenharia de Dados e MLOps:

```mermaid
flowchain
    subgraph Data Source
        API["Church Calendar API (calapi.inadiutorium.cz)"]
    end

    subgraph Data & ML Pipeline (Dagster & MLflow)
        Ingest["ingestion.py\n(API -> data/raw/*.json)"]
        Transform["transformation.py\n(Pydantic Validation & Flatten -> clean_calendar.csv)"]
        Train["training.py\n(Random Forest + MLflow Tracking)"]
        Drift["drift_monitoring.py\n(Evidently Data Drift Report)"]
    end

    subgraph Serving Layer
        FastAPI["serving.py\n(FastAPI Prediction API)"]
        Docker["Dockerfile\n(Python-slim Container)"]
    end

    subgraph Infrastructure
        Kind["Kind Cluster\n(Kubernetes Local)"]
        Helm["Helm Chart\n(Release Deployment)"]
    end

    API --> Ingest
    Ingest --> Transform
    Transform --> Train
    Transform --> Drift
    Train --> FastAPI
    FastAPI --> Docker
    Docker --> Helm
    Helm --> Kind
```

1. **Ingestão**: Carrega o histórico mensal litúrgico de 2023 a 2026, salvando-os de forma bruta (`data/raw/`).
2. **Transformação & Data Quality**: Limpa e tipifica os dados brutificados. Filtra e extrai a celebração litúrgica principal baseada na prioridade do `rank_num`. Valida a consistência de tipos e valores em runtime via **Pydantic**.
3. **ML Integration**: Treina um classificador `RandomForestClassifier` para prever a cor litúrgica principal (`colour`) baseado em variáveis temporais (`season`, `season_week`, `weekday`, etc.). Registra hiperparâmetros, métricas (acurácia, F1-score) e artefatos (matriz de confusão, metadados) no **MLflow**.
4. **Data Drift**: Compara dados históricos de 2024 (referência) com 2025/2026 (produção) usando a biblioteca **Evidently** para monitorar eventuais desvios de distribuição de features.
5. **Serving**: API **FastAPI** que carrega o modelo serializado e serve o endpoint de inferência `/predict`.
6. **Deploy & Rollback**: Deploy conteinerizado orquestrado localmente no Kubernetes via **Kind** e empacotado em um **Helm Chart** com probes de health-check e replicação tolerante a falhas.

---

## ⚙️ Decisões de Arquitetura (ADRs)

As decisões de design e trade-offs técnicos encontram-se documentados nos seguintes Architecture Decision Records (ADRs):

*   [ADR 01 — Orquestrador (Dagster)](docs/adr/adr-01-orquestrador.md)
*   [ADR 02 — MLOps (MLflow)](docs/adr/adr-02-mlflow-rastreamento.md)
*   [ADR 03 — Deploy Local (Kind & Helm)](docs/adr/adr-03-deploy-k8s-helm.md)

---

## 🚀 Como Rodar o Projeto

A automação das tarefas locais é gerenciada pelo `Makefile` usando o PowerShell no Windows.

### 1. Pré-requisitos
Instale as dependências locais (Docker Desktop instalado e ativo é obrigatório). Em um terminal PowerShell elevado (Como Administrador), execute:
```bash
make setup-tools
```
Isso instalará `kind`, `make` e `kubernetes-helm` via Chocolatey.

### 2. Configurar Ambiente Python e Dependências
Execute na raiz do projeto:
```bash
make setup-python
```

### 3. Executar o Pipeline de Dados e ML
Rode o pipeline para realizar a ingestão, transformação, treinamento do modelo (registrando no MLflow) e geração do relatório de drift:
```bash
make run-pipeline
```

*   **Para inspecionar o pipeline no Dagster**: Rode `make dagster-ui` e acesse [localhost:3000](http://localhost:3000).
*   **Para analisar métricas no MLflow**: Rode `make mlflow-ui` e acesse [localhost:5000](http://localhost:5000).
*   **Para ver o relatório de Drift**: Abra `data/reports/drift_report.html` diretamente no seu navegador.

### 4. Executar Testes Unitários
Execute os testes unitários e de qualidade de dados usando pytest:
```bash
make run-tests
```

### 5. Executar a API de Serving Localmente
Se desejar rodar a API FastAPI localmente sem Kubernetes:
```bash
make run-serving
```
Ela estará acessível em [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## ☸️ Operação Local no Kubernetes (Kind & Helm)

O deploy da aplicação de serving no Kubernetes local simula perfeitamente um ambiente de produção.

### 1. Subir o Cluster Kubernetes
Crie o cluster local no Docker usando o Kind (com mapeamento da porta 8080 do Windows para a porta 30080 do cluster):
```bash
make cluster-up
```

### 2. Build e Deploy da Aplicação
Compile a imagem Docker da API FastAPI, carregue-a nos nós do Kind e instale a release usando o Helm Chart parametrizado:
```bash
make deploy
```

### 3. Verificar o Status dos Recursos
Monitore o status do deployment, pods e service no namespace `production`:
```bash
make status
```

### 4. Testar a API em Execução no Kubernetes
Você pode testar a inferência da API rodando no Kubernetes fazendo uma requisição HTTP POST para a porta mapeada do host:
```bash
curl -X POST http://localhost:8080/predict `
  -H "Content-Type: application/json" `
  -d '{"date": "2026-07-11", "season": "ordinary", "season_week": 14, "weekday": "saturday"}'
```

### 5. Executar Rollback do Deploy
Caso precise reverter a versão do deploy no Kubernetes para a revisão anterior de forma segura e controlada:
```bash
make rollback
```

### 6. Destruir o Cluster
Para limpar o ambiente Docker e apagar o cluster Kind:
```bash
make cluster-down
```

---

## 🔍 Troubleshooting (Solução de Problemas)

#### Falhas de Permissão com Chocolatey
*   **Problema**: Mensagem "Chocolatey detected you are not running from an elevated command shell".
*   **Solução**: Abra o PowerShell do Windows clicando com o botão direito e selecionando "Executar como Administrador". Rode `make setup-tools`.

#### Erro de conexão ao criar cluster Kind
*   **Problema**: O Kind falha ao se comunicar com o daemon do Docker.
*   **Solução**: Certifique-se de que o Docker Desktop está aberto e rodando em segundo plano.

#### Erros de import do módulo `src` no pytest
*   **Problema**: `ModuleNotFoundError: No module named 'src'`.
*   **Solução**: O comando do Makefile já resolve isso definindo a configuração `-o pythonpath=.` no pytest. Rode os testes usando `make run-tests` ou `.venv\Scripts\pytest -o pythonpath=. -v tests/`.

#### Porta 8080 ocupada no host Windows
*   **Problema**: O Kind falha ao expor a porta 8080 porque outro serviço local está usando-a.
*   **Solução**: Edite o arquivo `k8s-kind-config.yaml` e altere o valor de `hostPort: 8080` para outra porta livre (ex: `8090`). Lembre-se de ajustar a URL de teste correspondente.
