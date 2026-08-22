# ============================================================
# HISTÓRICO
# IPM-RADAR-V3
# ROBÔ 2 - RADAR DE MOVIMENTAÇÃO / IPM
# ============================================================
#
# Função:
#   - Registrar os jogos analisados
#   - Guardar sinais/entradas
#   - Guardar resultado final dos jogos
#   - Permitir análise posterior do laboratório
#
# O arquivo histórico é salvo em:
#   historico.json
#
# ============================================================

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo


ARQUIVO_HISTORICO = os.getenv(
    "ARQUIVO_HISTORICO",
    "historico.json"
)

FUSO_HORARIO = os.getenv(
    "FUSO_HORARIO",
    "America/Sao_Paulo"
)

HISTORICO_MAXIMO = int(
    os.getenv(
        "HISTORICO_MAXIMO",
        "1000"
    )
)


# ============================================================
# DATA / HORA
# ============================================================

def agora():
    return datetime.now(
        ZoneInfo(FUSO_HORARIO)
    ).isoformat()


# ============================================================
# CARREGAR HISTÓRICO
# ============================================================

def carregar_historico():

    if not os.path.exists(
        ARQUIVO_HISTORICO
    ):
        return []

    try:

        with open(
            ARQUIVO_HISTORICO,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(
                arquivo
            )

        if isinstance(
            dados,
            list
        ):
            return dados

        return []

    except (
        json.JSONDecodeError,
        OSError,
        TypeError
    ):

        print(
            "⚠️ Não foi possível carregar o histórico."
        )

        return []


# ============================================================
# SALVAR HISTÓRICO
# ============================================================

def salvar_historico(historico):

    if not isinstance(
        historico,
        list
    ):
        return False

    # Mantém somente os registros mais recentes.
    if len(historico) > HISTORICO_MAXIMO:

        historico = historico[
            -HISTORICO_MAXIMO:
        ]

    try:

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

        return True

    except OSError as erro:

        print(
            "❌ ERRO AO SALVAR HISTÓRICO:"
        )

        print(
            erro
        )

        return False


# ============================================================
# SALVAR EVENTO
# ============================================================

def salvar_evento(evento):

    if not isinstance(
        evento,
        dict
    ):
        return False

    historico = carregar_historico()

    evento = dict(
        evento
    )

    if not evento.get(
        "data_registro"
    ):

        evento[
            "data_registro"
        ] = agora()

    historico.append(
        evento
    )

    sucesso = salvar_historico(
        historico
    )

    if sucesso:

        print(
            "📚 Evento registrado no histórico."
        )

    return sucesso


# ============================================================
# REGISTRAR JOGO / SINAL
# ============================================================

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
    sinal="",
    linha="",
    odd_anterior="",
    variacao_pct="",
    direcao="",
    forca="",
    status="OBSERVAÇÃO"
):

    evento = {

        "tipo": "jogo",

        "evento_id": str(
            evento_id
        ) if evento_id is not None else "",

        "data_registro": agora(),

        "campeonato": campeonato,

        "casa": casa,

        "fora": fora,

        "placar_entrada": placar,

        "minuto_entrada": minuto,

        "ipm": ipm,

        "mercado": mercado,

        "linha": linha,

        "odd_anterior": odd_anterior,

        "odd_entrada": odd,

        "variacao_pct": variacao_pct,

        "direcao": direcao,

        "forca": forca,

        "sinal": sinal,

        "status": status,

        "resultado_final": "",

        "placar_final": "",

        "gols_total": "",

        "classificacao_ciclo": ""

    }

    return salvar_evento(
        evento
    )


# ============================================================
# REGISTRAR RESULTADO FINAL
# ============================================================
#
# Usado depois que o jogo termina.
#
# Exemplos de classificação:
#
#   0x0
#   1x1
#   2x1
#   empate
#   mais_4_gols
#   outro
#
# ============================================================

def registrar_resultado(
    evento_id,
    placar_final,
    classificacao_ciclo="",
    resultado_final="",
    gols_total=""
):

    historico = carregar_historico()

    evento_id = str(
        evento_id
    )

    encontrado = False

    for evento in reversed(
        historico
    ):

        if str(
            evento.get(
                "evento_id",
                ""
            )
        ) != evento_id:

            continue

        evento[
            "placar_final"
        ] = placar_final

        evento[
            "resultado_final"
        ] = resultado_final

        evento[
            "gols_total"
        ] = gols_total

        evento[
            "classificacao_ciclo"
        ] = classificacao_ciclo

        evento[
            "data_resultado"
        ] = agora()

        encontrado = True

        break

    if not encontrado:

        print(
            "⚠️ Evento não encontrado:",
            evento_id
        )

        return False

    return salvar_historico(
        historico
    )


# ============================================================
# CONSULTAR HISTÓRICO
# ============================================================

def consultar_historico():

    return carregar_historico()


# ============================================================
# QUANTIDADE DE REGISTROS
# ============================================================

def quantidade_jogos():

    historico = carregar_historico()

    return len(
        historico
    )


# ============================================================
# CONSULTAR EVENTO
# ============================================================

def consultar_evento(
    evento_id
):

    evento_id = str(
        evento_id
    )

    historico = carregar_historico()

    for evento in reversed(
        historico
    ):

        if str(
            evento.get(
                "evento_id",
                ""
            )
        ) == evento_id:

            return evento

    return None


# ============================================================
# CLASSIFICAÇÃO AUTOMÁTICA DO PLACAR
# ============================================================

def classificar_placar(
    placar_final
):

    if not placar_final:

        return "sem_resultado"

    texto = str(
        placar_final
    ).strip().lower()

    # Aceita formatos:
    # 2x1
    # 2-1
    # 2 : 1

    texto = (
        texto
        .replace(
            "-",
            "x"
        )
        .replace(
            ":",
            "x"
        )
        .replace(
            " ",
            ""
        )
    )

    partes = texto.split(
        "x"
    )

    if len(partes) != 2:

        return "placar_invalido"

    try:

        gols_casa = int(
            partes[0]
        )

        gols_fora = int(
            partes[1]
        )

    except ValueError:

        return "placar_invalido"

    total = (
        gols_casa
        + gols_fora
    )

    if (
        gols_casa == 2
        and gols_fora == 1
    ):

        return "2x1"

    if gols_casa == gols_fora:

        return "empate"

    if total > 4:

        return "mais_4_gols"

    return "outro"


# ============================================================
# RESUMO DO LABORATÓRIO
# ============================================================

def resumo_resultados():

    historico = carregar_historico()

    resumo = {

        "total": 0,

        "2x1": 0,

        "empate": 0,

        "mais_4_gols": 0,

        "outro": 0,

        "sem_resultado": 0

    }

    for evento in historico:

        if evento.get(
            "tipo"
        ) != "jogo":

            continue

        resumo[
            "total"
        ] += 1

        classificacao = evento.get(
            "classificacao_ciclo"
        )

        if not classificacao:

            classificacao = classificar_placar(
                evento.get(
                    "placar_final",
                    ""
                )
            )

        if classificacao in resumo:

            resumo[
                classificacao
            ] += 1

        else:

            resumo[
                "outro"
            ] += 1

    return resumo
    
