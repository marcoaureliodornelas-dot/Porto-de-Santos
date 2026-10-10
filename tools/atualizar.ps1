# Atualiza o painel a partir do PDF mais recente da lista do Tecon Santos e
# envia o resultado para o GitHub. Só faz algo quando há um PDF novo.
#
# Procura o PDF em:
#   - entrada\*.pdf (pasta do projeto)
#   - Área de Trabalho\Relação de navios*.pdf

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$candidatos = @()
$candidatos += Get-ChildItem (Join-Path $raiz "entrada") -Filter *.pdf -ErrorAction SilentlyContinue
$candidatos += Get-ChildItem ([Environment]::GetFolderPath("Desktop")) -Filter "Rela*navios*.pdf" -ErrorAction SilentlyContinue
$pdf = $candidatos | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $pdf) { Write-Output "Nenhum PDF encontrado."; exit 0 }

# Pula se este PDF já foi processado (mesmo horário de gravação).
$marca = Join-Path $raiz "data\.ultimo_pdf"
$assinatura = "$($pdf.FullName)|$($pdf.LastWriteTimeUtc.Ticks)"
if ((Test-Path $marca) -and ((Get-Content $marca -Raw).Trim() -eq $assinatura)) {
    Write-Output "Sem PDF novo desde a última atualização."
    exit 0
}

python (Join-Path $PSScriptRoot "extrair_lista.py") $pdf.FullName
if ($LASTEXITCODE -ne 0) { throw "Falha ao extrair $($pdf.Name)" }
Set-Content -Path $marca -Value $assinatura -Encoding utf8

git add data docs
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Output "Nada mudou na lista."; exit 0 }
git commit -m "Atualiza lista de navios ($($pdf.LastWriteTime.ToString('dd/MM/yyyy HH:mm')))"
git push
