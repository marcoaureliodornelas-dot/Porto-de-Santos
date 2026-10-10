"""Busca a escala de navios previstos da DP World Santos (Embraport) no site
público https://www.embraportonline.com.br/Navios/Escala e grava em
data/terminais/dp-world-santos.json.

O site carrega a tabela a partir de /Navios/getEscalaPrevistos, que devolve
JSON; aqui fazemos a mesma chamada que a página faz.

Uso:
    python tools/dpworld.py
"""

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from consolidar import FMT, salvar_terminal

TERMINAL = "DP World Santos"
PAGINA = "https://www.embraportonline.com.br/Navios/Escala"
API = "https://www.embraportonline.com.br/Navios/getEscalaPrevistos"
DIAS = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO"]
# Navios de celulose não recebem contêiner de exportação.
SERVICOS_IGNORADOS = {"CELULOSE"}


def buscar():
    corpo = urllib.parse.urlencode({
        "prDataInicial": "", "prDataFinal": "", "prArmador": "", "prServico": "",
        "skipresult": 0, "takeresult": 1000,
    }).encode()
    req = urllib.request.Request(API, data=corpo, headers={
        "User-Agent": "Mozilla/5.0 (painel Porto-de-Santos)",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": PAGINA,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def data(texto):
    """'13/10/2026 22:00' -> '2026-10-13 22:00' (vazio se não houver)."""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})", texto or "")
    if not m:
        return ""
    d, mes, a, h, mi = m.groups()
    return f"{a}-{mes}-{d} {h}:{mi}"


def converter(registros, agora):
    corte = (agora - timedelta(days=30)).strftime(FMT)
    navios = []
    for r in registros:
        if (r.get("SERVICO") or "").upper() in SERVICOS_IGNORADOS:
            continue
        deadline = data(r.get("DryDeadlineDATA"))
        chegada = data(r.get("PrevisaoChegadaDATA"))
        # Registros antigos que ficaram como "previsto" no sistema do terminal.
        if max(deadline, chegada) < corte:
            continue
        atracacao = data(r.get("AtracacaoDATA"))
        dia = DIAS[datetime.strptime(atracacao, FMT).weekday()] if atracacao else ""
        # Gate já aberto; se ainda não abriu, a previsão de abertura.
        gate = data(r.get("AberturaGateDATA"))
        gate_previsto = data(r.get("PrevisaoAberturaGateDATA"))
        navios.append({
            "navio": (r.get("NAVIO") or "").strip().upper(),
            "berth": (r.get("SERVICO") or "").strip().upper(),
            "dia": dia,
            "deadline": deadline,
            "previsao_chegada": chegada,
            "liberacao_dry": gate or gate_previsto,
            "liberacao_prevista": not gate and bool(gate_previsto),
        })
    return navios


def main():
    agora = datetime.now()
    navios = converter(buscar(), agora)
    salvar_terminal(TERMINAL, navios, PAGINA, agora)
    print(f"{len(navios)} navios da {TERMINAL}")


if __name__ == "__main__":
    main()
