# Atualiza o painel e envia o resultado para o GitHub.
#   - DP World Santos: busca a escala no site a cada execução (automático).
#   - Tecon Santos: lê o PDF mais recente, só quando há um PDF novo
#     (o site da Santos Brasil exige CAPTCHA, então o PDF é salvo à mão).
#
# Procura o PDF do Tecon em:
#   - entrada\*.pdf (pasta do projeto)
#   - Área de Trabalho\Relação de navios*.pdf (filtro sem acento: o PowerShell 5.1 lê o script como ANSI)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

python (Join-Path $PSScriptRoot "dpworld.py")
if ($LASTEXITCODE -ne 0) { Write-Warning "Falha ao buscar a DP World Santos; seguindo com o Tecon." }

$candidatos = @()
$candidatos += Get-ChildItem (Join-Path $raiz "entrada") -Filter *.pdf -ErrorAction SilentlyContinue
$candidatos += Get-ChildItem ([Environment]::GetFolderPath("Desktop")) -Filter "Rela*navios*.pdf" -ErrorAction SilentlyContinue
$pdf = $candidatos | Sort-Object LastWriteTime | Select-Object -Last 1

# Pula o Tecon se este PDF já foi processado (mesmo horário de gravação).
$marca = Join-Path $raiz "data\.ultimo_pdf"
if ($pdf) {
    $assinatura = "$($pdf.FullName)|$($pdf.LastWriteTimeUtc.Ticks)"
    if ((Test-Path $marca) -and ((Get-Content $marca -Raw).Trim() -eq $assinatura)) {
        Write-Output "Tecon Santos: sem PDF novo."
    } else {
        python (Join-Path $PSScriptRoot "extrair_lista.py") $pdf.FullName
        if ($LASTEXITCODE -ne 0) { throw "Falha ao extrair $($pdf.Name)" }
        Set-Content -Path $marca -Value $assinatura -Encoding utf8
    }
} else {
    Write-Output "Tecon Santos: nenhum PDF encontrado."
}

git add data docs
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Output "Nada mudou nos dados."; exit 0 }
git commit -m "Atualiza navios ($(Get-Date -Format 'dd/MM/yyyy HH:mm'))"
git push
