import os
import json
import pickle
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# Definir caminhos temporários de teste para o modelo
TEST_MODEL_DIR = "tests/temp_model"
TEST_MODEL_PATH = os.path.join(TEST_MODEL_DIR, "model.pkl")
TEST_METADATA_PATH = os.path.join(TEST_MODEL_DIR, "metadata.json")

@pytest.fixture(scope="module", autouse=True)
def setup_test_model():
    """
    Cria um modelo mínimo dummy e salva localmente para os testes do FastAPI.
    """
    os.makedirs(TEST_MODEL_DIR, exist_ok=True)
    
    # 1. Criar dados sintéticos para treinar um classificador dummy
    # Features: ["season_code", "season_week", "weekday_code", "month", "day", "day_of_year", "is_sunday"]
    X = np.array([
        [0, 14, 5, 7, 11, 192, 0],
        [1, 5, 0, 3, 10, 69, 0],
        [2, 2, 6, 12, 5, 339, 1]
    ])
    y = np.array([0, 1, 2]) # Correspondendo a green, white, violet
    
    clf = RandomForestClassifier(n_estimators=2, max_depth=2, random_state=42)
    clf.fit(X, y)
    
    # 2. Salvar modelo
    with open(TEST_MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
        
    # 3. Salvar metadados
    metadata = {
        "season_map": {"ordinary": 0, "lent": 1, "advent": 2},
        "weekday_map": {"monday": 0, "saturday": 5, "sunday": 6},
        "classes": ["green", "white", "violet"],
        "idx_to_class": {"0": "green", "1": "white", "2": "violet"},
        "class_to_idx": {"green": 0, "white": 1, "violet": 2}
    }
    with open(TEST_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f)
        
    # Patch dos caminhos globais no src.serving
    import src.serving
    src.serving.MODEL_PATH = TEST_MODEL_PATH
    src.serving.METADATA_PATH = TEST_METADATA_PATH
    
    yield
    
    # Limpeza dos arquivos temporários
    if os.path.exists(TEST_MODEL_PATH):
        os.remove(TEST_MODEL_PATH)
    if os.path.exists(TEST_METADATA_PATH):
        os.remove(TEST_METADATA_PATH)
    if os.path.exists(TEST_MODEL_DIR):
        os.rmdir(TEST_MODEL_DIR)

def test_health_endpoint():
    """
    Testa se o endpoint de health check funciona.
    """
    from src.serving import app
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "model_loaded": True}

def test_predict_endpoint_success():
    """
    Testa se a predição retorna o formato correto e status 200 para inputs válidos.
    """
    from src.serving import app
    with TestClient(app) as client:
        payload = {
            "date": "2026-07-11",
            "season": "ordinary",
            "season_week": 14,
            "weekday": "saturday"
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "predicted_colour" in data
        assert data["date"] == "2026-07-11"
        assert "green" in data["probabilities"]

def test_predict_endpoint_invalid_inputs():
    """
    Testa se a API responde com Bad Request (400) para inputs incorretos.
    """
    from src.serving import app
    with TestClient(app) as client:
        # Data inválida
        payload = {
            "date": "11-07-2026",
            "season": "ordinary",
            "season_week": 14,
            "weekday": "saturday"
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 400
        
        # Season inválida
        payload_season = {
            "date": "2026-07-11",
            "season": "DESCONHECIDA",
            "season_week": 14,
            "weekday": "saturday"
        }
        response = client.post("/predict", json=payload_season)
        assert response.status_code == 400
