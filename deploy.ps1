$DeployPath = "C:\deploy\library_prod"
$SourcePath = $env:GITHUB_WORKSPACE

$VenvPath = Join-Path $DeployPath "venv"
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"
$PipPath = Join-Path $VenvPath "Scripts\pip.exe"

if (!(Test-Path $DeployPath)) {
    New-Item -ItemType Directory -Path $DeployPath | Out-Null
}

Write-Host "Deploy path: $DeployPath"
Write-Host "Source path: $SourcePath"

# Копируем код из workspace GitHub Actions в папку "prod"
# Важно: сохраняем локальные .env, db.sqlite3, media, staticfiles, venv
robocopy $SourcePath $DeployPath /MIR `
    /XD venv .git __pycache__ htmlcov .pytest_cache media staticfiles `
    /XF .coverage db.sqlite3 .env

# Для robocopy коды 0..7 считаются успешными
if ($LASTEXITCODE -gt 7) {
    Write-Error "robocopy failed with exit code $LASTEXITCODE"
    exit 1
}

# Создаем venv, если его ещё нет
if (!(Test-Path $PythonPath)) {
    py -3.13 -m venv $VenvPath
}

# Обновляем pip и ставим зависимости
& $PythonPath -m pip install --upgrade pip
& $PipPath install -r "$DeployPath\requirements.txt"

# Django-команды
& $PythonPath "$DeployPath\manage.py" migrate
& $PythonPath "$DeployPath\manage.py" check

# Оставь collectstatic, если он у тебя настроен
try {
    & $PythonPath "$DeployPath\manage.py" collectstatic --noinput
}
catch {
    Write-Host "collectstatic skipped or failed; continue if static is not configured yet"
}

Write-Host "Deploy completed successfully"