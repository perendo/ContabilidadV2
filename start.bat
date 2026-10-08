@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"

echo ============================================
echo   ContabilidadV2 - Arranque de desarrollo
echo ============================================
echo.

if not exist "%ROOT%.venv\Scripts\activate.bat" (
  echo [ERROR] No se encontro el entorno virtual en ".venv".
  echo         Creelo con:
  echo             python -m venv .venv
  echo             .venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
  echo.
  pause
  exit /b 1
)

echo [1/2] Activando el entorno virtual...
call "%ROOT%.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] No se pudo activar el entorno virtual.
  echo.
  pause
  exit /b 1
)

echo.
echo [2/2] Lanzando los servidores (start_servers.py)...
echo.
python "%ROOT%start_servers.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [ERROR] start_servers.py termino con codigo %RC%.
)

echo.
pause
endlocal
