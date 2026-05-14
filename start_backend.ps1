# TG OPS AI — Backend startup script
# Ensures .env takes precedence over system environment variables
Set-Location $PSScriptRoot
$env:PYTHONPATH = "backend"

# Clear the stale system-level OpenAI key from this session so .env takes precedence
$env:OPENAI_API_KEY = $null

Write-Host "Starting TG OPS AI Backend..." -ForegroundColor Cyan
Write-Host "PostgreSQL: localhost:5432/tg_ops_ai" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/api/docs" -ForegroundColor Green

& ".venv\Scripts\uvicorn.exe" app.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --reload `
    --reload-dir backend `
    --env-file .env `
    --log-level info
