# Porto de Santos

Painel de previsão de chegada e deadlines de recebimento de exportação dos
terminais **Tecon Santos** (Santos Brasil) e **DP World Santos**, ordenado
pela data do deadline.

Colunas: **Terminal, Navio, Berth / serviço, Dia, Deadline, Previsão de
chegada, Liberação do dry** e **Duração da janela** (tempo entre a liberação do
dry e o deadline).

Indicadores: recebimento aberto agora, deadlines em 48 h, chegadas em 7 dias e
janela média de recebimento, cada um com a divisão por terminal.

## Fontes

| Terminal | Fonte | Como entra |
| --- | --- | --- |
| DP World Santos | [embraportonline.com.br/Navios/Escala](https://www.embraportonline.com.br/Navios/Escala) | Automático: `tools/dpworld.py` busca a escala de navios previstos |
| Tecon Santos | [Lista de recebimento de exportação](https://www.santosbrasil.com.br/v2021/lista-de-atracacao?titulo=Tecon+Santos&unidade=tecon-santos&lista=recebimento-de-exportacao) | Manual: o site exige CAPTCHA; salve a lista em PDF |

Na DP World, "Berth / serviço" é o serviço (TANGO, SX2…), "Dia" é o dia da
semana da previsão de atracação e "Liberação do dry" é a abertura do gate
(marcada como "prev." enquanto o gate ainda não abriu). Navios de celulose
ficam de fora.

Para o Tecon Santos, abra a lista, resolva o CAPTCHA, use o botão de impressão
→ **Salvar como PDF** e salve na Área de Trabalho como
`Relação de navios - Porto de Santos.pdf` (ou em `entrada/`). O PDF não tem
texto selecionável, então `tools/extrair_lista.py` lê a tabela com OCR
(RapidOCR, local); leva de 2 a 3 minutos. Linhas de reserva do sistema
(`TBN ...`, `NAVIO SEM NOME`) são descartadas.

## Atualizar

`tools/atualizar.ps1` busca a DP World, relê o PDF do Tecon se houver um novo,
refaz o painel e envia para o GitHub (só faz commit se algo mudou).

Depois de mudar o visual (`tools/painel.html`), refaça só o painel:
`python tools/consolidar.py`.

## Publicação na Vercel

O repositório está ligado à Vercel: cada envio para `main` publica o painel.
O `vercel.json` publica só a pasta `docs/` como site estático, sem build; o
Python roda apenas no computador que coleta os dados (por isso o
`requirements.txt` fica em `tools/`, e não na raiz, onde a Vercel o
confundiria com uma aplicação Python).

## Arquivos gerados

| Arquivo | Conteúdo |
| --- | --- |
| `docs/index.html` | Painel com indicadores, filtro por terminal, busca e ordenação |
| `data/navios.csv` | Tabela para Excel (separador `;`) |
| `data/navios.json` | Mesmos dados, com a data de cada fonte |
| `data/terminais/*.json` | Dados de cada terminal antes da consolidação |

## Instalação

```bash
python -m pip install -r tools/requirements.txt
```
