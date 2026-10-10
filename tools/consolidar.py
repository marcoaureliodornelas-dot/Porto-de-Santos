"""Junta os navios de todos os terminais e gera data/navios.csv,
data/navios.json e o painel docs/index.html.

Cada terminal grava os seus navios em data/terminais/<terminal>.json (ver
extrair_lista.py e dpworld.py); este módulo só consolida.

Uso:
    python tools/consolidar.py      # refaz o painel com os dados já coletados
"""

import csv
import json
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_TERMINAIS = RAIZ / "data" / "terminais"
FMT = "%Y-%m-%d %H:%M"

SAIDA = ["terminal", "navio", "berth", "dia", "deadline", "previsao_chegada",
         "liberacao_dry", "duracao_janela"]


def duracao_janela(liberacao, deadline):
    """Tempo entre a liberação do dry e o deadline, em "Xd Yh"."""
    if not liberacao or not deadline:
        return ""
    minutos = int((datetime.strptime(deadline, FMT) - datetime.strptime(liberacao, FMT))
                  .total_seconds() // 60)
    sinal = "-" if minutos < 0 else ""
    horas, resto = divmod(abs(minutos), 60)
    dias, horas = divmod(horas, 24)
    texto = f"{dias}d {horas}h" if dias else f"{horas}h"
    if resto:
        texto += f" {resto}min"
    return sinal + texto


def salvar_terminal(terminal, navios, fonte, atualizado_em):
    """Grava os navios de um terminal e refaz o consolidado."""
    PASTA_TERMINAIS.mkdir(parents=True, exist_ok=True)
    for n in navios:
        n["terminal"] = terminal
        n["duracao_janela"] = duracao_janela(n.get("liberacao_dry", ""), n.get("deadline", ""))
    dados = {"terminal": terminal, "fonte": fonte,
             "atualizado_em": atualizado_em.strftime(FMT), "navios": navios}
    arquivo = PASTA_TERMINAIS / (terminal.lower().replace(" ", "-") + ".json")
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    consolidar()


def consolidar():
    terminais, navios = [], []
    for arquivo in sorted(PASTA_TERMINAIS.glob("*.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        terminais.append({k: dados[k] for k in ("terminal", "fonte", "atualizado_em")}
                         | {"navios": len(dados["navios"])})
        navios.extend(dados["navios"])
    # Mais próximo primeiro; sem deadline vai para o fim.
    navios.sort(key=lambda x: (x["deadline"] == "", x["deadline"], x["previsao_chegada"]))

    with open(RAIZ / "data" / "navios.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=SAIDA, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(navios)
    meta = {"terminais": terminais, "navios": navios}
    (RAIZ / "data" / "navios.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    gerar_painel(meta)
    return meta


def gerar_painel(meta, destino=None, documento_completo=True):
    """Preenche o modelo com os dados. O modelo não tem <html>/<head> para
    também servir como Artifact do claude.ai; para abrir no navegador ou no
    GitHub, o arquivo ganha o esqueleto de documento."""
    modelo = (RAIZ / "tools" / "painel.html").read_text(encoding="utf-8")
    html = modelo.replace("/*DADOS*/null", json.dumps(meta, ensure_ascii=False))
    if documento_completo:
        html = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                f'{html}\n</html>\n')
    destino = Path(destino) if destino else RAIZ / "docs" / "index.html"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    m = consolidar()
    print(", ".join(f'{t["terminal"]}: {t["navios"]}' for t in m["terminais"]))
