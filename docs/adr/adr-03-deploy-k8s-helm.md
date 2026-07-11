# ADR 03: Deploy em Kubernetes Local com Kind e Helm Charts

## Status
Aprovado

## Contexto
O projeto prático exige a validação do pipeline em ambiente Kubernetes (K8s) local com capacidade de deploy e rollback controlado. Escrever múltiplos manifestos Kubernetes manuais (`deployment.yaml`, `service.yaml`, `hpa.yaml`, etc.) para diferentes ambientes (desenvolvimento, homologação, produção) gera duplicação de código e aumenta a chance de erros de sintaxe ou configuração.

## Decisão
Decidimos utilizar a seguinte combinação tecnológica para a camada de infraestrutura local:
1. **Kind (Kubernetes in Docker)**: Para provisionamento de um cluster Kubernetes leve rodando dentro de containers Docker na máquina de desenvolvimento.
2. **Helm Charts**: Para empacotar e gerenciar todos os manifestos de infraestrutura como uma única release. O chart Helm foi parametrizado sob o diretório `charts/church-calendar`.
3. **Makefile**: Para encapsular a complexidade dos comandos `kubectl` e `helm`, oferecendo uma interface simplificada para desenvolvedores e integração contínua (ex: `make deploy` e `make rollback`).

## Consequências
- A build local da imagem Docker da API FastAPI é carregada diretamente nos nós do Kind (`kind load docker-image`) para evitar o uso de um registry de container externo.
- As atualizações de versão e correções de bugs da infraestrutura de serving são aplicadas via comandos `helm upgrade --install`.
- A capacidade de rollback local é garantida de forma limpa pelo histórico de revisões do Helm (`helm rollback`), permitindo reverter deploys defeituosos instantaneamente.
