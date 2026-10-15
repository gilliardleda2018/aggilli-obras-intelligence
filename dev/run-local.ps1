# Ambiente local completo (Windows): identidade de desenvolvimento, banco SQLite, importaÃ§Ã£o de referÃªncia,
# API (porta 8000) e frontend (porta 3100). Nada aqui serve para produÃ§Ã£o.
#
#   powershell -ExecutionPolicy Bypass -File dev\run-local.ps1            # sobe tudo
#   powershell -ExecutionPolicy Bypass -File dev\run-local.ps1 -Reset     # recria o banco local
#
# Depois abra http://localhost:3100/login e use "Entrar como usuÃ¡rio de desenvolvimento".
param([switch]$Reset, [switch]$Wait, [int]$ApiPort = 8000, [int]$WebPort = 3100)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$work = Join-Path $root ".local"
New-Item -ItemType Directory -Force $work | Out-Null
$db = Join-Path $work "obras-dev.db"
$py = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { python -m venv (Join-Path $backend ".venv"); & $py -m pip install -q -r (Join-Path $backend "requirements.txt") }

Push-Location $backend
try {
  foreach ($line in (& $py -m scripts.dev_identity init)) { $k, $v = $line -split "=", 2; Set-Item "env:$k" $v.Trim() }
  $env:APP_ENV = "development"
  $env:DATABASE_URL = "sqlite+pysqlite:///" + ($db -replace "\\", "/")
  if ($Reset -and (Test-Path $db)) { Remove-Item $db }
  & $py -m alembic upgrade head
  & $py -m scripts.import_tuntum --organization "Grupo MG (desenvolvimento)" --owner-subject dev-owner --apply
  & $py -m scripts.seed_demo --owner-subject dev-owner
  $env:DEV_ACCESS_TOKEN = (& $py -m scripts.dev_identity token --sub dev-owner --hours 12 | Out-String).Trim()
  $api = Start-Process -PassThru -WindowStyle Hidden -FilePath $py -ArgumentList "-m", "uvicorn", "app.main:app", "--port", $ApiPort `
    -WorkingDirectory $backend -RedirectStandardOutput (Join-Path $work "api.log") -RedirectStandardError (Join-Path $work "api.err")
} finally { Pop-Location }

$env:SESSION_ENCRYPTION_KEY = -join ((1..32) | ForEach-Object { "{0:x2}" -f (Get-Random -Maximum 256) })
$env:ALLOW_DEV_LOGIN = "1"
$env:API_BASE_URL = "http://localhost:$ApiPort"
Push-Location $frontend
try {
  if (-not (Test-Path "node_modules")) { npm install --no-audit --no-fund }
  npm run build
  $web = Start-Process -PassThru -WindowStyle Hidden -FilePath "npm.cmd" -ArgumentList "run", "start", "--", "-p", $WebPort `
    -WorkingDirectory $frontend -RedirectStandardOutput (Join-Path $work "web.log") -RedirectStandardError (Join-Path $work "web.err")
} finally { Pop-Location }
Write-Host "API: http://localhost:$ApiPort/docs   Painel: http://localhost:$WebPort/login"
if ($Wait) { Wait-Process -Id $api.Id, $web.Id }

