import time

from config import INTERVALO_SEGUNDOS
from odds_api import buscar_jogos_ao_vivo, buscar_odds_multiplos, extrair_mercados
from motor_ipm_v2 import analisar_ipm_com_memoria, formatar_radar

def processar_ciclo():
    print("\n" + "=" * 70)
    print("🚀 IPM RADAR V3 - NOVO CICLO")
    print("=" * 70)
    eventos = buscar_jogos_ao_vivo()
    if not eventos:
        print("⚠️ Nenhum jogo ao vivo neste ciclo.")
        return
    odds = buscar_odds_multiplos(eventos)
    if not odds:
        print("⚠️ Nenhuma odd recebida neste ciclo.")
        return
    for jogo in eventos:
        if not isinstance(jogo, dict) or jogo.get("id") is None:
            continue
        dados = extrair_mercados(jogo, odds)
        odd = dados.get("odd_atual", 0.0)
        if odd <= 0:
            print(f"⚠️ {jogo.get('id')} | odd de empate não encontrada.")
            continue
        resultado = analisar_ipm_com_memoria(
            jogo["id"], odd, minuto=dados.get("minuto", 0)
        )
        print(formatar_radar(jogo, resultado))

def main():
    print("🤖 IPM RADAR V3 INICIADO")
    while True:
        inicio = time.time()
        try:
            processar_ciclo()
        except KeyboardInterrupt:
            print("🛑 Encerrado.")
            break
        except Exception as e:
            print(f"❌ ERRO NO CICLO: {type(e).__name__}: {e}")
        espera = max(1, INTERVALO_SEGUNDOS - int(time.time() - inicio))
        print(f"⏳ Próximo ciclo em {espera}s...")
        time.sleep(espera)

if __name__ == "__main__":
    main()
        
