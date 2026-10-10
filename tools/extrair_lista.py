"""Extrai a lista de Recebimento de Exportação (Tecon Santos / Santos Brasil)
de um PDF impresso do site e gera data/navios.csv, data/navios.json e
docs/index.html.

O PDF impresso pelo navegador não tem texto selecionável (as letras são
desenhadas como vetores), então a tabela é lida assim:
  1. a grade (linhas e colunas) vem das bordas vetoriais do PDF;
  2. cada página é renderizada como imagem e passa por OCR (RapidOCR);
  3. cada trecho reconhecido vai para a célula onde está; trechos que
     invadem duas colunas são relidos coluna por coluna.

Uso:
    python tools/extrair_lista.py "C:/caminho/Relação de navios.pdf"
    python tools/extrair_lista.py            # usa o PDF mais recente em entrada/
    python tools/extrair_lista.py --so-painel  # só refaz o painel
"""

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

RAIZ = Path(__file__).resolve().parent.parent
ESCALA = 3.0  # pontos do PDF -> pixels da imagem usada no OCR

# Colunas da tabela, na ordem em que aparecem no site.
COLUNAS = [
    "id", "berco", "navio", "viagem_armador", "viagem", "berth", "dia",
    "inicio", "fim", "deadline", "previsao_chegada", "prev_lib_dry",
    "prev_lib_reefer", "liberacao_dry", "liberacao_reefer",
]
# Colunas que a ferramenta mostra.
SAIDA = ["navio", "berth", "dia", "deadline", "previsao_chegada", "liberacao_dry",
         "duracao_janela"]
COLUNAS_DATA = ["deadline", "previsao_chegada", "liberacao_dry"]

DIAS = {"TERCA": "TERÇA", "SABADO": "SÁBADO"}

# Cabeçalho e rodapé que o navegador imprime em cada página.
RE_RODAPE = re.compile(r"santosbrasil|http|lista-de|\d{2}/\d{2}/\d{4}|^\d{1,2}/\d{1,2}$", re.I)

RE_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{2})\D*(\d{2}):?(\d{2})")


def separadores(valores, minimo):
    """Agrupa posições de bordas próximas e devolve as que se repetem o
    bastante para serem linhas da grade (e não traços dentro do texto)."""
    contagem = Counter(round(v) for v in valores)
    pos = sorted(v for v, n in contagem.items() if n >= minimo)
    unidos = []
    for v in pos:
        if unidos and v - unidos[-1] <= 2:
            continue
        unidos.append(v)
    return unidos


def grade(pagina):
    finos_v = [r for r in pagina.rects if r["width"] < 2 and r["height"] > 5]
    # Traços "--" das células vazias também são retângulos finos; as bordas
    # das linhas são bem mais largas.
    finos_h = [r for r in pagina.rects if r["height"] < 2 and r["width"] > 20]
    linhas_y = separadores([r["top"] for r in finos_h], 1)
    n_linhas = max(len(linhas_y) - 1, 1)
    colunas_x = separadores([r["x0"] for r in finos_v], max(3, n_linhas // 2))
    # A última linha de uma página que continua na seguinte não tem borda
    # inferior: usa o fim das bordas verticais como limite, parando antes do
    # rodapé que o navegador imprime (URL e número da página).
    fundo = min(max((r["bottom"] for r in finos_v), default=0), pagina.height - 20)
    if linhas_y and fundo - linhas_y[-1] > 5:
        linhas_y.append(round(fundo))
    return colunas_x, linhas_y


def sobreposicao(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def ocr_regiao(ocr, imagem, caixa):
    """OCR de um recorte da página; devolve [(x0, x1, y_centro, texto)] em pontos."""
    x0, y0, x1, y1 = caixa
    recorte = imagem.crop(tuple(int(v * ESCALA) for v in caixa))
    fundo = Image.new("RGB", (recorte.width + 40, recorte.height + 40), "white")
    fundo.paste(recorte, (20, 20))
    resultado, _ = ocr(np.array(fundo))
    trechos = []
    for pontos, texto, _conf in resultado or []:
        xs = [(p[0] - 20) / ESCALA + x0 for p in pontos]
        ys = [(p[1] - 20) / ESCALA + y0 for p in pontos]
        trechos.append((min(xs), max(xs), sum(ys) / 4, texto.strip()))
    return trechos


def juntar(trechos):
    """Junta os trechos de uma célula em ordem de leitura, sem repetir o
    mesmo texto lido duas vezes (pelo OCR da página e pela releitura)."""
    textos = []
    for *_, t in sorted(trechos):
        if t and t not in textos:
            textos.append(t)
    return " ".join(textos)


def ler_pdf(caminho):
    """Um OCR por página; trechos que invadem duas colunas (o OCR às vezes
    junta "26/2566" e "PLATA-SB" num trecho só) são relidos coluna por coluna."""
    ocr = RapidOCR()
    pdf_img = pdfium.PdfDocument(str(caminho))
    registros = []
    with pdfplumber.open(str(caminho)) as pdf:
        for n, pagina in enumerate(pdf.pages):
            xs, ys = grade(pagina)
            if len(xs) - 1 != len(COLUNAS):
                raise SystemExit(
                    f"Página {n + 1}: esperava {len(COLUNAS)} colunas e "
                    f"encontrei {len(xs) - 1}. O layout do site mudou?")
            imagem = pdf_img[n].render(scale=ESCALA).to_pil().convert("RGB")
            largura, altura = imagem.width / ESCALA, imagem.height / ESCALA
            celulas = {}
            for tx0, tx1, ty, texto in ocr_regiao(ocr, imagem, (0, 0, largura, altura)):
                if RE_RODAPE.search(texto):
                    continue
                linha = next((i for i in range(len(ys) - 1) if ys[i] <= ty < ys[i + 1]), None)
                if linha is None:
                    continue
                cols = [c for c in range(len(xs) - 1)
                        if sobreposicao(tx0, tx1, xs[c], xs[c + 1]) > 3]
                if len(cols) == 1:
                    celulas.setdefault((linha, cols[0]), []).append((ty, tx0, texto))
                    continue
                for c in cols:
                    caixa = (xs[c] + 1, ty - 8, xs[c + 1] - 1, ty + 8)
                    for _, sx0, sy, sub in ocr_regiao(ocr, imagem, caixa):
                        celulas.setdefault((linha, c), []).append((sy, sx0, sub))
            for l in range(len(ys) - 1):
                linha = {nome: juntar(celulas.get((l, c), []))
                         for c, nome in enumerate(COLUNAS)}
                if re.search(r"N[uú]mero|Navio$", linha["id"] + linha["navio"]):
                    continue  # cabeçalho repetido em cada página
                if not linha["id"]:
                    # Continuação de uma linha que começou na página anterior.
                    if registros:
                        for nome, valor in linha.items():
                            if valor:
                                registros[-1][nome] = f"{registros[-1][nome]} {valor}".strip()
                    continue
                if linha["navio"]:
                    registros.append(linha)
    return registros


def para_data(texto):
    m = RE_DATA.search(texto.replace(" ", ""))
    if not m:
        return None
    d, mes, a, h, mi = (int(x) for x in m.groups())
    try:
        return datetime(2000 + a, mes, d, h, mi)
    except ValueError:
        return None


def duracao_janela(liberacao, deadline):
    """Tempo entre a liberação do dry e o deadline, em "Xd Yh"."""
    if not liberacao or not deadline:
        return ""
    fmt = "%Y-%m-%d %H:%M"
    minutos = int((datetime.strptime(deadline, fmt) - datetime.strptime(liberacao, fmt))
                  .total_seconds() // 60)
    sinal = "-" if minutos < 0 else ""
    horas, resto = divmod(abs(minutos), 60)
    dias, horas = divmod(horas, 24)
    texto = f"{dias}d {horas}h" if dias else f"{horas}h"
    if resto:
        texto += f" {resto}min"
    return sinal + texto


def limpar(registros):
    navios = []
    for r in registros:
        nome = re.sub(r"\s+", " ", r["navio"]).upper()
        # Linhas de reserva do sistema, sem navio de verdade.
        if nome.startswith("TBN") or "SEM NOME" in nome or r["id"] == "-1":
            continue
        dia = r["dia"].upper().replace(" ", "")
        item = {"navio": nome,
                "berth": re.sub(r"\s+", "", r["berth"]).upper(),
                "dia": DIAS.get(dia, dia)}
        for col in COLUNAS_DATA:
            dt = para_data(r[col])
            item[col] = dt.strftime("%Y-%m-%d %H:%M") if dt else ""
        for col in ("berth", "dia"):
            if set(item[col]) <= {"-"}:
                item[col] = ""
        item["duracao_janela"] = duracao_janela(item["liberacao_dry"], item["deadline"])
        navios.append(item)
    # Mais próximo primeiro; sem deadline vai para o fim.
    navios.sort(key=lambda x: (x["deadline"] == "", x["deadline"], x["previsao_chegada"]))
    return navios


def salvar(navios, origem):
    pasta = RAIZ / "data"
    pasta.mkdir(exist_ok=True)
    with open(pasta / "navios.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=SAIDA, delimiter=";")
        w.writeheader()
        w.writerows(navios)
    # Horário do arquivo = momento em que a lista foi salva do site.
    salvo_em = datetime.fromtimestamp(Path(origem).stat().st_mtime)
    meta = {"atualizado_em": salvo_em.strftime("%Y-%m-%d %H:%M"),
            "fonte": Path(origem).name, "navios": navios}
    (pasta / "navios.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    gerar_painel(meta)


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


def main():
    if sys.argv[1:] == ["--so-painel"]:
        # Refaz só o painel com os dados já extraídos (após mudar o modelo).
        gerar_painel(json.loads((RAIZ / "data" / "navios.json").read_text(encoding="utf-8")))
        print("Painel regerado a partir de data/navios.json")
        return
    if len(sys.argv) > 1:
        origem = Path(sys.argv[1])
    else:
        pdfs = sorted((RAIZ / "entrada").glob("*.pdf"), key=lambda p: p.stat().st_mtime)
        if not pdfs:
            raise SystemExit("Nenhum PDF em entrada/. Passe o caminho do arquivo.")
        origem = pdfs[-1]
    navios = limpar(ler_pdf(origem))
    salvar(navios, origem)
    print(f"{len(navios)} navios extraídos de {origem.name}")


if __name__ == "__main__":
    main()
