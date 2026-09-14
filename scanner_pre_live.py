# ============================================================
# SCANNER PRÉ-LIVE - IPM RADAR V5.2
# Q + ESTRUTURA + MERCADOS DE GOL
# ============================================================

from datetime import datetime, time

from config import (
    FUSO_HORARIO,
    MAX_EVENTOS_POR_CONSULTA,
    PRE_LIVE_JANELA_MINUTOS,
    Q_MIN,
    Q_MAX,
)

from odds_api import (
    buscar_jogos_pre_live,
    buscar_odds_multiplos,
    extrair_mercados,
)


def numero(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def probabilidade_implicita(odd):
    odd = numero(odd)
    return 100.0 / odd if odd > 0 else 0.0


def probabilidade_normalizada(odd_casa, odd_empate, odd_visitante):
    pc = probabilidade_implicita(odd_casa)
    px = probabilidade_implicita(odd_empate)
    pv = probabilidade_implicita(odd_visitante)
    total = pc + px + pv
    return (px / total) * 100.0 if total > 0 else 0.0


def calcular_q(odd_casa, odd_visitante):
    casa = numero(odd_casa)
    fora = numero(odd_visitante)
    if casa <= 0 or fora <= 0:
        return 0.0
    return 2.0 * casa * fora / (casa + fora)


def calcular_r(odd_casa, odd_visitante):
    casa = numero(odd_casa)
    fora = numero(odd_visitante)
    if casa <= 0 or fora <= 0:
        return 0.0
    menor = min(casa, fora)
    maior = max(casa, fora)
    return maior / menor if menor > 0 else 0.0


def classificar_equilibrio(r):
    if r <= 0:
        return "SEM_DADOS"
    if r <= 1.20:
        return "EQUILÍBRIO MUITO ALTO"
    if r <= 1.50:
        return "EQUILÍBRIO ALTO"
    if r <= 1.80:
        return "EQUILÍBRIO MODERADO"
    if r <= 2.20:
        return "DESEQUILÍBRIO"
    return "DESEQUILÍBRIO ALTO"


def classificar_padrao(r):
    if r <= 0:
        return "SEM_DADOS"
    return "PADRÃO_EMPATE" if r <= 1.80 else "PADRÃO_GOL"


def identificar_periodo(dt):
    hora = dt.time()
    if time(6, 0) <= hora < time(12, 0):
        return "06:00 - 12:00"
    if time(12, 0) <= hora < time(18, 0):
        return "12:00 - 18:00"
    if time(18, 0) <= hora or hora < time(0, 0):
        return "18:00 - 00:00"
    return "FORA_DA_JANELA"


def converter_horario(evento):
    valor = (
        evento.get("date")
        or evento.get("startTime")
        or evento.get("start_time")
    )
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=FUSO_HORARIO)
        return dt.astimezone(FUSO_HORARIO)
    except Exception:
        return None


def analisar_gols(mercados):
    over_linha = numero(mercados.get("over_linha"))
    under_linha = numero(mercados.get("under_linha"))
    odd_over = numero(mercados.get("odd_over"))
    odd_under = numero(mercados.get("odd_under"))
    odd_btts_sim = numero(mercados.get("odd_btts_sim"))
    odd_btts_nao = numero(mercados.get("odd_btts_nao"))

    prob_over = probabilidade_implicita(odd_over)
    prob_under = probabilidade_implicita(odd_under)
    prob_btts_sim = probabilidade_implicita(odd_btts_sim)
    prob_btts_nao = probabilidade_implicita(odd_btts_nao)

    over_disponivel = odd_over > 0 and odd_under > 0
    btts_disponivel = odd_btts_sim > 0 and odd_btts_nao > 0

    if over_disponivel:
        if prob_over >= 60 and odd_over <= 1.70:
            over_status = "OVER FORTE"
        elif prob_over >= 55 and odd_over <= 1.85:
            over_status = "OVER FAVORÁVEL"
        elif prob_over >= 50 and odd_over <= 2.00:
            over_status = "OVER MODERADO"
        else:
            over_status = "OVER NEUTRO"
    else:
        over_status = "SEM TOTALS"

    if btts_disponivel:
        if prob_btts_sim >= 60 and odd_btts_sim <= 1.70:
            btts_status = "BTTS FORTE"
        elif prob_btts_sim >= 55 and odd_btts_sim <= 1.85:
            btts_status = "BTTS FAVORÁVEL"
        elif prob_btts_sim >= 50 and odd_btts_sim <= 2.00:
            btts_status = "BTTS MODERADO"
        else:
            btts_status = "BTTS NEUTRO"
    else:
        btts_status = "SEM BTTS"

    pontos = 0

    if over_status == "OVER FORTE":
        pontos += 2
    elif over_status in ("OVER FAVORÁVEL", "OVER MODERADO"):
        pontos += 1

    if btts_status == "BTTS FORTE":
        pontos += 2
    elif btts_status in ("BTTS FAVORÁVEL", "BTTS MODERADO"):
        pontos += 1

    if pontos >= 4:
        estrutura_gol = "ESTRUTURA MUITO FAVORÁVEL A GOLS"
    elif pontos >= 3:
        estrutura_gol = "ESTRUTURA FAVORÁVEL A GOLS"
    elif pontos >= 2:
        estrutura_gol = "ESTRUTURA MODERADA PARA GOLS"
    elif pontos == 1:
        estrutura_gol = "ESTRUTURA FRACA PARA GOLS"
    else:
        estrutura_gol = "SEM CONFIRMAÇÃO PRÉ-LIVE"

    return {
        "over_linha": over_linha,
        "under_linha": under_linha,
        "odd_over": odd_over,
        "odd_under": odd_under,
        "prob_over": prob_over,
        "prob_under": prob_under,
        "odd_btts_sim": odd_btts_sim,
        "odd_btts_nao": odd_btts_nao,
        "prob_btts_sim": prob_btts_sim,
        "prob_btts_nao": prob_btts_nao,
        "over_status": over_status,
        "btts_status": btts_status,
        "pontos_gol": pontos,
        "estrutura_gol": estrutura_gol,
        "mercado_gol_disponivel": over_disponivel or btts_disponivel,
    }


def escanear_pre_live():
    print()
    print("=" * 72)
    print("🧪 SCANNER PRÉ-LIVE | IPM RADAR V5.2")
    print("=" * 72)
    print(f"⏱️ JANELA: {PRE_LIVE_JANELA_MINUTOS} minutos")
    print(f"📐 Q REAL DO FILTRO: {Q_MIN:.2f} → {Q_MAX:.2f}")
    print("⚽ ANÁLISE: TOTALS + BTTS")
    print("=" * 72)

    try:
        jogos = buscar_jogos_pre_live() or []
    except Exception as erro:
        print("ERRO AO BUSCAR JOGOS:", type(erro).__name__, erro)
        return []

    if not jogos:
        print("Nenhum jogo pré-live encontrado.")
        return []

    jogos = jogos[:MAX_EVENTOS_POR_CONSULTA]

    try:
        odds = buscar_odds_multiplos(jogos) or []
    except Exception as erro:
        print("ERRO AO BUSCAR ODDS:", type(erro).__name__, erro)
        odds = []

    print(f"JOGOS PRÉ-LIVE ENCONTRADOS: {len(jogos)}")
    print(f"ODDS RECEBIDAS: {len(odds)}")
    print()

    resultados = []
    validos_1x2 = 0
    fora_q = 0
    q_minimo = None
    q_maximo = None

    for jogo in jogos:
        if not isinstance(jogo, dict):
            continue

        event_id = jogo.get("id")
        if event_id is None:
            continue

        mercados = extrair_mercados(jogo, odds) or {}

        odd_casa = numero(mercados.get("odd_casa"))
        odd_empate = numero(mercados.get("odd_empate"))
        odd_visitante = numero(mercados.get("odd_visitante"))

        if odd_casa <= 0 or odd_empate <= 0 or odd_visitante <= 0:
            continue

        validos_1x2 += 1

        dt = converter_horario(jogo)
        if dt is None:
            continue

        periodo = identificar_periodo(dt)
        if periodo == "FORA_DA_JANELA":
            continue

        q = calcular_q(odd_casa, odd_visitante)
        r = calcular_r(odd_casa, odd_visitante)

        q_minimo = q if q_minimo is None else min(q_minimo, q)
        q_maximo = q if q_maximo is None else max(q_maximo, q)

        casa_nome = jogo.get("home") or jogo.get("homeTeam") or "Casa"
        fora_nome = jogo.get("away") or jogo.get("awayTeam") or "Fora"

        print(
            f"🔎 Q | {dt.strftime('%H:%M')} | "
            f"{casa_nome} x {fora_nome} | "
            f"Casa={odd_casa:.2f} | "
            f"Fora={odd_visitante:.2f} | "
            f"Q={q:.4f}"
        )

        if q < Q_MIN or q > Q_MAX:
            fora_q += 1
            continue

        gols = analisar_gols(mercados)

        resultados.append({
            "event_id": str(event_id),
            "data": dt.strftime("%d/%m/%Y"),
            "horario": dt.strftime("%H:%M"),
            "periodo": periodo,
            "casa": casa_nome,
            "fora": fora_nome,
            "odd_casa": odd_casa,
            "odd_empate": odd_empate,
            "odd_visitante": odd_visitante,
            "q": round(q, 4),
            "r": round(r, 4),
            "odd_pre_live": round(q, 4),
            "probabilidade_x": probabilidade_implicita(odd_empate),
            "probabilidade_x_normalizada": probabilidade_normalizada(
                odd_casa, odd_empate, odd_visitante
            ),
            "equilibrio": classificar_equilibrio(r),
            "indice_equilibrio": round(100.0 / r, 2) if r > 0 else 0.0,
            "padrao": classificar_padrao(r),
            "over_linha": gols["over_linha"],
            "under_linha": gols["under_linha"],
            "odd_over": gols["odd_over"],
            "odd_under": gols["odd_under"],
            "prob_over": gols["prob_over"],
            "prob_under": gols["prob_under"],
            "odd_btts_sim": gols["odd_btts_sim"],
            "odd_btts_nao": gols["odd_btts_nao"],
            "prob_btts_sim": gols["prob_btts_sim"],
            "prob_btts_nao": gols["prob_btts_nao"],
            "over_status": gols["over_status"],
            "btts_status": gols["btts_status"],
            "pontos_gol": gols["pontos_gol"],
            "estrutura_gol": gols["estrutura_gol"],
            "mercado_gol_disponivel": gols["mercado_gol_disponivel"],
            "radar": True,
        })

    resultados.sort(
        key=lambda x: (
            -x["pontos_gol"],
            -x["q"],
            -x["r"],
            x["data"],
            x["horario"],
        )
    )

    print()
    print("=" * 72)
    print("📊 DIAGNÓSTICO PRÉ-LIVE")
    print("=" * 72)
    print(f"1X2 VÁLIDO: {validos_1x2}")
    print(
        f"Q MÍNIMO ENCONTRADO: "
        f"{q_minimo:.4f}" if q_minimo is not None else "Q MÍNIMO: --"
    )
    print(
        f"Q MÁXIMO ENCONTRADO: "
        f"{q_maximo:.4f}" if q_maximo is not None else "Q MÁXIMO: --"
    )
    print(f"FORA DO Q: {fora_q}")
    print(f"DENTRO DO Q {Q_MIN:.2f} → {Q_MAX:.2f}: {len(resultados)}")

    if resultados:
        print()
        print("🚨 CANDIDATOS PRÉ-LIVE PARA ESTUDO DE GOLS")
        for jogo in resultados:
            print(
                f"🎯 {jogo['horario']} | "
                f"{jogo['casa']} x {jogo['fora']} | "
                f"Q={jogo['q']:.2f} | "
                f"R={jogo['r']:.2f} | "
                f"OVER={jogo['odd_over']:.2f} | "
                f"BTTS={jogo['odd_btts_sim']:.2f} | "
                f"PONTOS={jogo['pontos_gol']} | "
                f"{jogo['estrutura_gol']}"
            )
    else:
        print()
        print(f"⚠️ NENHUM JOGO DENTRO DO Q {Q_MIN:.2f} → {Q_MAX:.2f}")
        print("🔬 O diagnóstico acima mostra os Q calculados ANTES do filtro.")

    return resultados


def exibir_scanner(resultados):
    if not resultados:
        print("Nenhum resultado para exibir.")
        return

    print()
    print("=" * 72)

    for jogo in resultados:
        print()
        print(f"⚽ {jogo['horario']} | {jogo['casa']} x {jogo['fora']}")
        print(
            f"🏠 {jogo['odd_casa']:.2f} | "
            f"🤝 X {jogo['odd_empate']:.2f} | "
            f"🚌 {jogo['odd_visitante']:.2f}"
        )
        print(f"📐 Q: {jogo['q']:.2f}")
        print(f"📊 R: {jogo['r']:.2f}")
        print(f"⚖️ Equilíbrio: {jogo['equilibrio']}")
        print(
            f"🎯 P(X): {jogo['probabilidade_x']:.2f}% | "
            f"P(X) N: {jogo['probabilidade_x_normalizada']:.2f}%"
        )
        print()
        print("⚽ MERCADO DE GOLS")

        if jogo["odd_over"] > 0:
            print(
                f"📈 Over {jogo['over_linha']:.2f}: "
                f"{jogo['odd_over']:.2f} | "
                f"P={jogo['prob_over']:.2f}% | "
                f"{jogo['over_status']}"
            )
        else:
            print("📈 Over: sem mercado")

        if jogo["odd_btts_sim"] > 0:
            print(
                f"🔄 BTTS SIM: {jogo['odd_btts_sim']:.2f} | "
                f"P={jogo['prob_btts_sim']:.2f}% | "
                f"{jogo['btts_status']}"
            )
        else:
            print("🔄 BTTS: sem mercado")

        print(f"🧪 Pontos GOL: {jogo['pontos_gol']}")
        print(f"🚨 {jogo['estrutura_gol']}")
        print("=" * 72)
