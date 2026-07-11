FROM python:3.12-slim

WORKDIR /app

# Instalar dependências básicas do sistema, se necessário
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependências python do projeto
# Nota: --no-cache-dir reduz o tamanho final da imagem
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código-fonte da aplicação e modelo treinado
COPY src/ /app/src/
COPY models/ /app/models/

# Variável de ambiente para garantir que a saída de logs do Python seja impressa imediatamente
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Executar a API via Uvicorn
CMD ["uvicorn", "src.serving:app", "--host", "0.0.0.0", "--port", "8000"]
