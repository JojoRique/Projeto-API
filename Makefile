# Configuração de shell para garantir compatibilidade no Windows (PowerShell)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

.PHONY: help setup-tools setup-python run-pipeline run-serving run-tests cluster-up cluster-down build-image deploy rollback status clean

help:
	@echo "Comandos disponíveis:"
	@echo "  make setup-tools    - Instala kind, make e helm via Chocolatey (requer Privilégios de Admin)"
	@echo "  make setup-python   - Instala as dependências Python no ambiente virtual (.venv)"
	@echo "  make run-pipeline   - Executa sequencialmente o pipeline de dados (ingestão -> transformação -> treino -> drift)"
	@echo "  make dagster-ui     - Inicia a interface gráfica do Dagster"
	@echo "  make mlflow-ui      - Inicia a interface gráfica do MLflow"
	@echo "  make run-serving    - Inicia a API FastAPI de Serving localmente"
	@echo "  make run-tests      - Executa os testes unitários e de qualidade de dados via Pytest"
	@echo "  make cluster-up     - Cria o cluster Kubernetes local com o Kind (mapeando a porta 8080)"
	@echo "  make cluster-down   - Deleta o cluster Kubernetes local do Kind"
	@echo "  make build-image    - Reconstrói a imagem Docker da API FastAPI"
	@echo "  make deploy         - Envia a imagem para o Kind e instala o Helm Chart"
	@echo "  make rollback       - Reverte a revisão do deploy no Kubernetes para a versão anterior via Helm"
	@echo "  make status         - Exibe o status dos recursos no Kubernetes local"
	@echo "  make clean          - Limpa caches locais, modelos temporários e dados"

setup-tools:
	@echo "Instalando ferramentas via Chocolatey (Certifique-se de estar rodando como Administrador)..."
	choco install -y kind make kubernetes-helm

setup-python:
	@echo "Instalando dependências Python no ambiente virtual..."
	python -m venv .venv
	.venv\Scripts\pip install -r requirements.txt

run-pipeline:
	@echo "Executando o pipeline de dados e MLOps..."
	.venv\Scripts\python src/ingestion.py
	.venv\Scripts\python src/transformation.py
	.venv\Scripts\python src/training.py
	.venv\Scripts\python src/drift_monitoring.py

dagster-ui:
	@echo "Iniciando Dagster Webserver..."
	$env:DAGSTER_HOME="dagster_home"; if (!(Test-Path dagster_home)) { New-Item -ItemType Directory -Path dagster_home -Force }; .venv\Scripts\dagster-webserver -f src/pipeline.py -h 127.0.0.1 -p 3000

mlflow-ui:
	@echo "Iniciando MLflow UI..."
	.venv\Scripts\mlflow ui --host 127.0.0.1 --port 5000

run-serving:
	@echo "Iniciando a API de Serving localmente..."
	.venv\Scripts\uvicorn src.serving:app --host 127.0.0.1 --port 8000 --reload

run-tests:
	@echo "Executando testes unitários e qualidade de dados..."
	.venv\Scripts\pytest -v --cov=src tests/

cluster-up:
	@echo "Criando cluster Kubernetes no Kind..."
	kind create cluster --name church-calendar-cluster --config k8s-kind-config.yaml
	kubectl cluster-info --context kind-church-calendar-cluster

cluster-down:
	@echo "Destruindo cluster Kubernetes no Kind..."
	kind delete cluster --name church-calendar-cluster

build-image:
	@echo "Construindo imagem Docker da API FastAPI..."
	docker build -t church-calendar-serving:latest .

deploy: build-image
	@echo "Carregando imagem Docker no cluster Kind..."
	kind load docker-image church-calendar-serving:latest --name church-calendar-cluster
	@echo "Executando deploy do Helm Chart..."
	helm upgrade --install church-calendar charts/church-calendar --create-namespace --namespace production

rollback:
	@echo "Executando rollback da release Helm no namespace production..."
	helm rollback church-calendar --namespace production

status:
	@echo "Status do cluster (Namespace: production)..."
	kubectl get all -n production

clean:
	@echo "Limpando caches e arquivos temporários..."
	if (Test-Path __pycache__) { Remove-Item -Recurse -Force __pycache__ }
	if (Test-Path src\__pycache__) { Remove-Item -Recurse -Force src\__pycache__ }
	if (Test-Path tests\__pycache__) { Remove-Item -Recurse -Force tests\__pycache__ }
	if (Test-Path .pytest_cache) { Remove-Item -Recurse -Force .pytest_cache }
	if (Test-Path .coverage) { Remove-Item -Force .coverage }
	if (Test-Path data) { Remove-Item -Recurse -Force data }
	if (Test-Path models) { Remove-Item -Recurse -Force models }
