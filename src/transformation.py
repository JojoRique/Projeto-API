import os
import glob
import json
import logging
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
PROCESSED_FILE_PATH = os.path.join(PROCESSED_DATA_DIR, "clean_calendar.csv")

# ==========================================
# SCHEMAS PYDANTIC PARA VALIDAÇÃO DE DADOS
# ==========================================

class CelebrationSchema(BaseModel):
    title: str = Field(default="")
    colour: str = Field(..., description="Cor litúrgica da celebração")
    rank: str = Field(..., description="Rank textual da celebração")
    rank_num: float = Field(..., description="Peso numérico de importância da celebração")

    @field_validator("colour")
    @classmethod
    def validate_colour(cls, v: str) -> str:
        valid_colours = {"green", "white", "red", "violet", "purple", "rose", "black"}
        v_lower = v.lower()
        if v_lower not in valid_colours:
            logger.warning(f"Cor litúrgica desconhecida ou rara: {v}")
        return v_lower

class DaySchema(BaseModel):
    date: str = Field(..., description="Data no formato YYYY-MM-DD")
    season: str = Field(..., description="Tempo litúrgico")
    season_week: int = Field(..., description="Semana do tempo litúrgico")
    weekday: str = Field(..., description="Dia da semana")
    celebrations: List[CelebrationSchema] = Field(default=[], description="Lista de celebrações do dia")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Data deve estar no formato YYYY-MM-DD")
        return v

# ==========================================
# FUNÇÕES DE TRANSFORMAÇÃO
# ==========================================

def load_raw_data(raw_dir: str) -> List[dict]:
    """
    Carrega todos os arquivos JSON de dados crus do diretório especificado.
    """
    json_files = glob.glob(os.path.join(raw_dir, "*.json"))
    all_days = []
    
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_days.extend(data)
                else:
                    logger.warning(f"Formato inválido no arquivo {file_path}. Ignorando.")
        except Exception as e:
            logger.error(f"Erro ao carregar {file_path}: {e}")
            
    logger.info(f"Carregados {len(all_days)} registros de dias brutos.")
    return all_days

def transform_and_validate(raw_days: List[dict]) -> pd.DataFrame:
    """
    Valida os dados brutos usando Pydantic e os transforma em um DataFrame estruturado.
    """
    valid_records = []
    invalid_count = 0
    
    for idx, day_data in enumerate(raw_days):
        try:
            # Validação via Pydantic
            validated_day = DaySchema(**day_data)
            
            # Se não houver celebrações, definimos uma celebração ferial padrão (verde no tempo comum, etc.)
            if not validated_day.celebrations:
                # Criar celebração padrão
                main_celebration = {
                    "celebration_title": "Ferial",
                    "colour": "green" if validated_day.season == "ordinary" else "violet",
                    "rank": "ferial",
                    "rank_num": 1.0
                }
            else:
                # A celebração principal do dia é aquela com maior rank_num
                # (ex: solenidade supera memória opcional)
                best_cel = max(validated_day.celebrations, key=lambda c: c.rank_num)
                main_celebration = {
                    "celebration_title": best_cel.title if best_cel.title else "Ferial",
                    "colour": best_cel.colour,
                    "rank": best_cel.rank,
                    "rank_num": best_cel.rank_num
                }
            
            # Engenharia de Features Temporais
            dt = datetime.strptime(validated_day.date, "%Y-%m-%d")
            
            record = {
                "date": validated_day.date,
                "year": dt.year,
                "month": dt.month,
                "day": dt.day,
                "day_of_year": dt.timetuple().tm_yday,
                "weekday": validated_day.weekday,
                "is_sunday": 1 if validated_day.weekday == "sunday" else 0,
                "season": validated_day.season,
                "season_week": validated_day.season_week,
                "celebration_title": main_celebration["celebration_title"],
                "colour": main_celebration["colour"],
                "rank": main_celebration["rank"],
                "rank_num": main_celebration["rank_num"]
            }
            
            valid_records.append(record)
            
        except Exception as e:
            invalid_count += 1
            if invalid_count <= 5:
                logger.warning(f"Registro inválido no índice {idx}: {e}")
                
    logger.info(f"Validação concluída: {len(valid_records)} válidos, {invalid_count} inválidos.")
    
    df = pd.DataFrame(valid_records)
    return df

def run_transformation():
    """
    Executa o fluxo completo de transformação e qualidade de dados.
    """
    if not os.path.exists(RAW_DATA_DIR) or not os.listdir(RAW_DATA_DIR):
        logger.error(f"Diretório de entrada raw {RAW_DATA_DIR} vazio ou inexistente. Execute a ingestão primeiro.")
        return
        
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    
    # 1. Carregar dados brutos
    raw_days = load_raw_data(RAW_DATA_DIR)
    
    # 2. Validar e transformar
    df = transform_and_validate(raw_days)
    
    if df.empty:
        logger.error("Nenhum dado válido extraído após a transformação.")
        return
        
    # 3. Salvar os dados transformados
    df.to_csv(PROCESSED_FILE_PATH, index=False, encoding="utf-8")
    logger.info(f"Dados transformados salvos com sucesso em {PROCESSED_FILE_PATH} ({len(df)} linhas).")

if __name__ == "__main__":
    logger.info("Iniciando processo de transformação...")
    run_transformation()
    logger.info("Transformação concluída!")
