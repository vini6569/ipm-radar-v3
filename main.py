import os, time, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import INTERVALO_SEGUNDOS
from odds_api import buscar_jogos_ao_vivo, buscar_odds_multiplos, extrair_mercados
from motor_ipm import calcular_ipm

def processar_ciclo():
    print("\n"+"="*70+"\n🚀 IPM RADAR V3 - CICLO\n"+"="*70)
    jogos=buscar_jogos_ao_vivo()
    if not jogos: return
    odds=buscar_odds_multiplos(jogos)
    if not odds: return
    for jogo in jogos:
        if not isinstance(jogo,dict) or jogo.get("id") is None: continue
        d=extrair_mercados(jogo,odds)
        if not d["todos"]: continue
        movimentos=[x for x in d["todos"] if not x["primeira_consulta"]]
        maior=max((abs(float(x["variacao"])) for x in movimentos),default=0)
        gols=sum(int(d["placar"].get(k,0)) for k in ("home","away"))
        ipm=calcular_ipm(maior,d["minuto"],gols=gols)
        print(f"⚽ {jogo.get('home','Casa')} x {jogo.get('away','Fora')} | {d['minuto']}' | HT={len(d['HT'])} FT={len(d['FT'])} TOTAL={len(d['todos'])}")
        print(f"🎯 IPM={ipm['ipm']:.2f} | maior movimento={maior:.2f}% | {ipm['forca']}")
        fortes=sorted(movimentos,key=lambda x:abs(float(x["variacao"])),reverse=True)[:10]
        for x in fortes:
            print(f"  {x['periodo']} | {x['mercado']} | {x['linha'] or '-'} | {x['selecao']} | {x['odd_anterior']} -> {x['odd']} | {x['variacao']:.2f}%")

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        body=b"IPM RADAR V3 ONLINE\nHT + FT + TODOS OS MERCADOS\n"
        self.send_response(200); self.send_header("Content-Type","text/plain; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

def servidor():
    porta=int(os.environ.get("PORT","10000"))
    print(f"🌐 Health server: {porta}")
    HTTPServer(("0.0.0.0",porta),Health).serve_forever()

def main():
    print("🤖 IPM RADAR V3 INICIADO | HT + FT + TODOS OS MERCADOS")
    threading.Thread(target=servidor,daemon=True).start()
    while True:
        inicio=time.time()
        try: processar_ciclo()
        except KeyboardInterrupt: break
        except Exception as e: print(f"❌ CICLO: {type(e).__name__}: {e}")
        time.sleep(max(1,INTERVALO_SEGUNDOS-int(time.time()-inicio)))

if __name__=="__main__": main()
