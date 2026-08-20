import json
import os
from datetime import datetime

ARQUIVO_HISTORICO = "historico.json"


def carregar_historico():
    if not os.path.exists(ARQUIVO_HISTORICO):
        return []

    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception:
        return []


def salvar_evento(evento):
    historico = carregar_historico()

    evento["data_registro"] = datetime.now().isoformat()

    historico.append(evento)

    with open(
        ARQUIVO_HISTORICO,
        "w",
        encoding="utf-8"
    ) as arquivo:
        json.dump(
            historico,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


def registrar_jogo(
    evento_id,
    campeonato,
    casa,
    fora,
    placar,
    minuto,
    ipm,
    mercado="",
    odd="",
    sinal=""
):
    evento = {
        "evento_id": evento_id,
        "campeonato": campeonato,
        "casa": casa,
        "fora": fora,
        "placar": placar,
        "minuto": minuto,
        "ipm": ipm,
        "mercado": mercado,
        "odd": odd,
        "sinal": sinal
    }

    salvar_evento(evento)


def consultar_historico():
    return carregar_historico()


def quantidade_jogos():
    return len(carregar_historico())
