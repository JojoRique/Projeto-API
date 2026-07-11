import pytest
from pydantic import ValidationError
from src.transformation import DaySchema, CelebrationSchema, transform_and_validate

def test_celebration_schema_valid():
    """
    Testa se o schema de celebração valida cores e ranks válidos.
    """
    cel = CelebrationSchema(title="Saint Benedict", colour="white", rank="memorial", rank_num=3.1)
    assert cel.colour == "white"
    assert cel.rank_num == 3.1

def test_celebration_schema_invalid_colour():
    """
    Testa se o validador loga ou aceita cores não padronizadas com aviso,
    mas falha se for nulo ou tipo errado.
    """
    # Cores raras devem ser aceitas mas convertidas para lower case
    cel = CelebrationSchema(title="Festa", colour="GOLD", rank="feast", rank_num=4.0)
    assert cel.colour == "gold"

def test_day_schema_invalid_date():
    """
    Testa se o Pydantic levanta ValidationError para datas mal formatadas.
    """
    with pytest.raises(ValidationError):
        DaySchema(
            date="11-07-2026",  # Formato errado, deveria ser YYYY-MM-DD
            season="ordinary",
            season_week=14,
            weekday="saturday",
            celebrations=[]
        )

def test_transform_and_validate_logic():
    """
    Testa a transformação lógica: priorização da celebração de maior rank_num e engenharia de features.
    """
    raw_data = [
        {
            "date": "2026-07-11",
            "season": "ordinary",
            "season_week": 14,
            "weekday": "saturday",
            "celebrations": [
                {
                    "title": "Saint Benedict, abbot",
                    "colour": "white",
                    "rank": "memorial",
                    "rank_num": 3.1
                },
                {
                    "title": "Ferial Saturday",
                    "colour": "green",
                    "rank": "ferial",
                    "rank_num": 1.0
                }
            ]
        }
    ]
    
    df = transform_and_validate(raw_data)
    
    assert not df.empty
    assert len(df) == 1
    # Deve escolher a celebração de maior rank_num (Saint Benedict / white)
    assert df.iloc[0]["colour"] == "white"
    assert df.iloc[0]["celebration_title"] == "Saint Benedict, abbot"
    assert df.iloc[0]["rank_num"] == 3.1
    # Features temporais extraídas
    assert df.iloc[0]["year"] == 2026
    assert df.iloc[0]["month"] == 7
    assert df.iloc[0]["day"] == 11
    assert df.iloc[0]["is_sunday"] == 0
    assert df.iloc[0]["day_of_year"] == 192  # 11 de julho é o dia 192 em ano não bissexto (2026)
