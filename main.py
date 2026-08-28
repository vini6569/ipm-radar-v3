# IPM RADAR V4.2 - main.py
import os, time, threading, json, urllib.parse, urllib.request
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import (NOME_BOT, VERSAO, INTERVALO_RADAR, MAX_JOGOS_RADAR,
    IPM_MINIMO_OBSERVACAO, IPM_MINIMO_FORTE, IPM_MINIMO_MUITO_FORTE,
    VARIACAO_MINIMA_ODD, horario_ativo, horario_atual)
from odds_api import buscar_jogos_ao_vivo, buscar_odds_multiplos, extrair_mercados
from motor_ipm import analisar_ipm_com_memoria, formatar_radar, avaliar_entrada, jogo_finalizado, resultado_empate

PORTA_SAUDE = int(os.environ.get("PORT", "10000"))
ARQUIVO_CONTROLE = Path(os.getenv("ARQUIVO_CONTROLE", "ipm_controle.json"))
IPM_MINIMO_ENTRADA = float(os.getenv("IPM_MINIMO_ENTRADA", "40"))
MINUTO_MINIMO_ENTRADA = int(os.getenv("MINUTO_MINIMO_ENTRADA", "1"))
MINUTO_MAXIMO_ENTRADA = int(os.getenv("MINUTO_MAXIMO_ENTRADA", "5"))
MAX_ENTRADAS_POR_JOGO = int(os.getenv("MAX_ENTRADAS_POR_JOGO", "3"))
INTERVALO_ENTRE_ENTRADAS = int(os.getenv("INTERVALO_ENTRE_ENTRADAS", "5"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
_controle_jogos = {}
_lock = threading.Lock()

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram não configurado; mensagem mantida no log.")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": texto}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r: return 200 <= r.status < 300
    except Exception as e:
        print("❌ ERRO TELEGRAM:", type(e).__name__, e); return False

def salvar_controle():
    try:
        tmp = ARQUIVO_CONTROLE.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f: json.dump(_controle_jogos, f, ensure_ascii=False, indent=2)
        tmp.replace(ARQUIVO_CONTROLE)
    except Exception as e: print("❌ ERRO AO SALVAR:", e)

def carregar_controle():
    global _controle_jogos
    try:
        if ARQUIVO_CONTROLE.exists():
            with ARQUIVO_CONTROLE.open(encoding="utf-8") as f: d=json.load(f)
            if isinstance(d, dict): _controle_jogos=d
    except Exception as e: print("⚠️ ERRO AO CARREGAR:", e)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            corpo=f"{NOME_BOT} ONLINE | Brasil: {horario_atual().strftime('%d/%m/%Y %H:%M:%S')} | Versão: {VERSAO}".encode()
            self.send_response(200); self.send_header("Content-Type","text/plain; charset=utf-8")
            self.send_header("Content-Length",str(len(corpo))); self.end_headers(); self.wfile.write(corpo)
        except Exception:
            try: self.send_response(500); self.end_headers()
            except Exception: pass
    def log_message(self, format, *args): return

def iniciar_servidor_saude():
    try:
        HTTPServer(("0.0.0.0",PORTA_SAUDE),HealthHandler).serve_forever()
    except Exception as e: print("❌ ERRO SERVIDOR:",e)

def classificar_sinal(ipm):
    try: v=float(ipm)
    except: v=0
    if v>=IPM_MINIMO_MUITO_FORTE: return "SINAL MUITO FORTE"
    if v>=IPM_MINIMO_FORTE: return "SINAL FORTE"
    if v>=IPM_MINIMO_OBSERVACAO: return "OBSERVAR"
    return "SEM SINAL"

def controle(event_id):
    k=str(event_id)
    with _lock:
        return _controle_jogos.setdefault(k,{"entradas":[],"entrada_ativa":False,"padrao_mantido":False,"finalizado":False,"resultado":None})

def processar_jogo(jogo, mercados, resultado):
    event_id=jogo.get("id")
    c=controle(event_id)
    minuto=resultado.get("minuto",0)
    if c["entradas"]:
        c["padrao_mantido"]=(float(resultado.get("ipm",0))>=IPM_MINIMO_ENTRADA and abs(float(resultado.get("variacao_odd",0)))>=VARIACAO_MINIMA_ODD)
    if not c["finalizado"] and not c["entradas"] and avaliar_entrada(resultado,minuto,IPM_MINIMO_ENTRADA,VARIACAO_MINIMA_ODD,MINUTO_MINIMO_ENTRADA,MINUTO_MAXIMO_ENTRADA):
        c["entradas"].append({"numero":1,"minuto":int(minuto),"odd":resultado.get("odd_atual"),"ipm":resultado.get("ipm"),"variacao_odd":resultado.get("variacao_odd"),"status":"ATIVA"})
        c["entrada_ativa"]=True; c["padrao_mantido"]=True
        casa,fora=jogo.get("home") or "Casa",jogo.get("away") or "Fora"
        enviar_telegram(f"🚨 ENTRADA EMPATE\n\n⚽ {casa} x {fora}\n⏱️ {minuto}'\n💰 Odd: {resultado.get('odd_atual')}\n📈 Variação: {float(resultado.get('variacao_odd',0)):+.2f}%\n🎯 IPM: {float(resultado.get('ipm',0)):.2f}\n🟢 PADRÃO CONFIRMADO")
    if c["entradas"] and c["padrao_mantido"] and len(c["entradas"])<MAX_ENTRADAS_POR_JOGO:
        ultima=c["entradas"][-1]["minuto"]
        if int(minuto)-int(ultima)>=INTERVALO_ENTRE_ENTRADAS and avaliar_entrada(resultado,minuto,IPM_MINIMO_ENTRADA,VARIACAO_MINIMA_ODD,MINUTO_MINIMO_ENTRADA,MINUTO_MAXIMO_ENTRADA):
            n=len(c["entradas"])+1
            c["entradas"].append({"numero":n,"minuto":int(minuto),"odd":resultado.get("odd_atual"),"ipm":resultado.get("ipm"),"variacao_odd":resultado.get("variacao_odd"),"status":"ATIVA"})
            enviar_telegram(f"🔁 NOVA ENTRADA EMPATE\n⚽ {jogo.get('home','Casa')} x {jogo.get('away','Fora')}\n⏱️ {minuto}'\n💰 Odd: {resultado.get('odd_atual')}\n🎯 IPM: {float(resultado.get('ipm',0)):.2f}")
    if not c["finalizado"] and jogo_finalizado(jogo):
        emp=resultado_empate(jogo,mercados)
        if emp is not None:
            c["finalizado"]=True; c["resultado"]="VERDE" if emp else "VERMELHO"
            for e in c["entradas"]: e["status"]=c["resultado"]
            enviar_telegram(f"{'🟢' if emp else '🔴'} RESULTADO FINAL\n⚽ {jogo.get('home','Casa')} x {jogo.get('away','Fora')}\n📌 {'EMPATE' if emp else 'NÃO EMPATE'}")
    salvar_controle()

def executar_consulta():
    try:
        jogos=buscar_jogos_ao_vivo() or []
        if not jogos: print("ℹ️ Nenhum jogo ao vivo."); return
        jogos=jogos[:MAX_JOGOS_RADAR]
        odds=buscar_odds_multiplos(jogos) or []
        for jogo in jogos:
            try:
                if not isinstance(jogo,dict) or jogo.get("id") is None: continue
                mercados=extrair_mercados(jogo,odds) or {}
                r=analisar_ipm_com_memoria(jogo["id"],mercados.get("odd_atual",0),mercados.get("minuto",0),mercados.get("gols",0),mercados.get("escanteios",0),mercados.get("finalizacoes",0),mercados.get("ataques_perigosos",0))
                print(formatar_radar(jogo,r,mercados)); print("🚦",classificar_sinal(r.get("ipm",0)))
                processar_jogo(jogo,mercados,r)
            except Exception as e: print("❌ ERRO JOGO:",type(e).__name__,e)
    except Exception as e: print("❌ ERRO CICLO:",type(e).__name__,e)

def loop_consulta():
    carregar_controle()
    print(f"🚀 {NOME_BOT} V{VERSAO} | Protocolo: referência → 1–5 min → entrada → compare → resultado")
    while True:
        inicio=time.time()
        try:
            if horario_ativo(): executar_consulta()
            else: print("⏸️ Radar em período de pausa.")
        except Exception as e: print("❌ ERRO LOOP:",e)
        time.sleep(max(1,int(INTERVALO_RADAR-(time.time()-inicio))))

if __name__=="__main__":
    threading.Thread(target=iniciar_servidor_saude,daemon=True).start()
    loop_consulta()
            
