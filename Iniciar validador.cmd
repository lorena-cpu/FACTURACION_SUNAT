@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Falta el entorno virtual .venv. Consulta las instrucciones de README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -B -m facturacion_sunat.interfaz
if errorlevel 1 pause
