import os
import json
import pickle
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

MODEL_DIR = "models/liturgical_model"
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")

# Estruturas em memória para armazenar o modelo e mapeamentos
model = None
metadata = {}
season_map = {}
weekday_map = {}
idx_to_class = {}

class PredictRequest(BaseModel):
    date: str = Field(..., example="2026-07-11", description="Data no formato YYYY-MM-DD")
    season: str = Field(..., example="ordinary", description="Tempo litúrgico (ordinary, lent, advent, easter, christmas)")
    season_week: int = Field(..., example=14, description="Número da semana no tempo litúrgico")
    weekday: str = Field(..., example="saturday", description="Dia da semana por extenso em inglês")

class PredictResponse(BaseModel):
    date: str
    predicted_colour: str
    probabilities: dict

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Carrega o modelo de ML e os metadados do mapeamento de categorias na inicialização do serviço.
    """
    global model, metadata, season_map, weekday_map, idx_to_class
    
    logger.info("Iniciando carregamento do modelo de ML...")
    if not os.path.exists(MODEL_PATH) or not os.path.exists(METADATA_PATH):
        logger.error("Arquivos de modelo ou metadados não encontrados localmente. O serviço rodará sem capacidade de predição.")
    else:
        try:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            season_map = metadata.get("season_map", {})
            weekday_map = metadata.get("weekday_map", {})
            # Converter chaves do idx_to_class de string para int (pois o JSON converte chaves em string)
            raw_idx_to_class = metadata.get("idx_to_class", {})
            idx_to_class = {int(k): v for k, v in raw_idx_to_class.items()}
            
            logger.info("Modelo e metadados carregados com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao carregar o modelo: {e}")
            
    yield
    logger.info("Encerrando serviço de ML...")

app = FastAPI(
    title="Church Calendar ML Serving API",
    description="API para servir predições de cor litúrgica baseadas no calendário da Igreja.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", summary="Verificação de Saúde")
def health_check():
    """
    Verifica a saúde do serviço de ML, incluindo se o modelo está carregado.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo de Machine Learning não carregado no servidor.")
    return {"status": "healthy", "model_loaded": True}

@app.post("/predict", response_model=PredictResponse, summary="Predição de Cor Litúrgica")
def predict(payload: PredictRequest):
    """
    Prediz a cor litúrgica principal para uma data e época litúrgica específica.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo de Machine Learning não disponível no servidor.")
        
    try:
        # 1. Processar a data para extrair as features numéricas
        dt = datetime.strptime(payload.date, "%Y-%m-%d")
        month = dt.month
        day = dt.day
        day_of_year = dt.timetuple().tm_yday
        is_sunday = 1 if payload.weekday.lower() == "sunday" else 0
        
        # 2. Codificar variáveis categóricas
        season_code = season_map.get(payload.season.lower(), -1)
        weekday_code = weekday_map.get(payload.weekday.lower(), -1)
        
        if season_code == -1:
            raise HTTPException(status_code=400, detail=f"Tempo litúrgico inválido: {payload.season}")
        if weekday_code == -1:
            raise HTTPException(status_code=400, detail=f"Dia da semana inválido: {payload.weekday}")
            
        # 3. Montar vetor de features na mesma ordem do treinamento:
        # ["season_code", "season_week", "weekday_code", "month", "day", "day_of_year", "is_sunday"]
        features = [
            season_code,
            payload.season_week,
            weekday_code,
            month,
            day,
            day_of_year,
            is_sunday
        ]
        
        # 4. Executar inferência
        prediction_idx = int(model.predict([features])[0])
        probabilities = model.predict_proba([features])[0]
        
        # Obter nome da cor prevista
        predicted_colour = idx_to_class.get(prediction_idx, "desconhecida")
        
        # Mapear probabilidades para as respectivas classes
        prob_map = {idx_to_class.get(int(i), f"classe_{i}"): float(prob) for i, prob in enumerate(probabilities)}
        
        return PredictResponse(
            date=payload.date,
            predicted_colour=predicted_colour,
            probabilities=prob_map
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro durante a predição: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar predição.")
