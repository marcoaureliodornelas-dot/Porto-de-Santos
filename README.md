# Porto de Santos

Painel de previsão de chegada e deadlines de recebimento de exportação do
Tecon Santos (Santos Brasil), ordenado pela data do deadline.

Colunas: **Navio, Berth, Dia, Deadline, Previsão de chegada, Liberação do dry** e
**Duração da janela** (tempo entre a liberação do dry e o deadline).

## Como funciona

A lista do site da Santos Brasil fica atrás de um CAPTCHA, então os dados entram
por um PDF salvo do site:

1. Abra a [lista de recebimento de exportação](https://www.santosbrasil.com.br/v2021/lista-de-atracacao?titulo=Tecon+Santos&unidade=tecon-santos&lista=recebimento-de-exportacao),
   resolva o CAPTCHA e use o botão de impressão da lista → **Salvar como PDF**.
2. Salve na Área de Trabalho como `Relação de navios - Porto de Santos.pdf`
   (ou em `entrada/` dentro do projeto).
3. Rode `tools/atualizar.ps1`. Ele lê o PDF mais recente, gera o painel e
   envia para o GitHub. Se o PDF não mudou, não faz nada.

O PDF impresso não tem texto selecionável, então `tools/extrair_lista.py` lê a
tabela com OCR (RapidOCR, roda localmente). Leva cerca de 2 a 3 minutos.

## Arquivos gerados

| Arquivo | Conteúdo |
| --- | --- |
| `docs/index.html` | Painel: busca, ordenação por qualquer coluna, destaque de deadlines vencidos e das próximas 48 h |
| `data/navios.csv` | Tabela para Excel (separador `;`) |
| `data/navios.json` | Mesmos dados, com a data da lista |

Linhas de reserva do sistema (`TBN ...`, `NAVIO SEM NOME`) são descartadas.

## Instalação

```bash
python -m pip install -r requirements.txt
```
