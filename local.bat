@echo off
setlocal
title TCC Delaunay Triangulation - Executor Local

cd /d "%~dp0"

echo ================================================================
echo      TCC Delaunay Triangulation - Ambiente Localhost
echo ================================================================
echo.
echo Escolha o modo de execucao:
echo.
echo  [1] Modo Nativo (Python venv + React)
echo      - Muito rapido, nao precisa do Docker Desktop aberto.
echo      - Backend na porta 5000, Frontend na porta 3000.
echo.
echo  [2] Docker Compose Local (build local via compose.yml)
echo      - Constroi e roda os containers a partir do codigo fonte.
echo.
echo  [3] Docker Compose via Docker Hub (compose.dockerhub.yml)
echo      - Puxa e roda as imagens emersonbottega/* publicadas.
echo.
echo ================================================================

set "OPTION="
set /p "OPTION=Escolha uma opcao [1, 2 ou 3] (Pressione Enter para 1): "
if "%OPTION%"=="" set "OPTION=1"

if "%OPTION%"=="1" goto run_native
if "%OPTION%"=="2" goto run_docker_local
if "%OPTION%"=="3" goto run_docker_hub

echo Opcao invalida. Executando Modo Nativo por padrao...
goto run_native


:run_native
echo.
echo ----------------------------------------------------------------
echo [1/3] Verificando ambiente do Backend...
echo ----------------------------------------------------------------
if exist "prototype\backend\venv\Scripts\python.exe" goto backend_ready

echo Criando venv e instalando dependencias do backend...
cd /d "%~dp0prototype\backend"
py -3.12 -m venv venv || python -m venv venv
call .\venv\Scripts\activate.bat
pip install -r requirements.txt
cd /d "%~dp0"

:backend_ready
echo Backend OK.

echo.
echo ----------------------------------------------------------------
echo [2/3] Verificando dependencias do Frontend...
echo ----------------------------------------------------------------
if exist "prototype\frontend\node_modules" goto frontend_ready

echo Executando npm install no frontend...
cd /d "%~dp0prototype\frontend"
call npm install
cd /d "%~dp0"

:frontend_ready
echo Frontend OK.

echo.
echo ----------------------------------------------------------------
echo [3/3] Iniciando servidores em janelas separadas...
echo ----------------------------------------------------------------

start "Backend - Flask (5000)" cmd /k "cd /d "%~dp0prototype\backend" && .\venv\Scripts\python.exe app.py"
start "Frontend - React (3000)" cmd /k "cd /d "%~dp0prototype\frontend" && npm start"

echo.
echo ================================================================
echo   Servidores iniciados!
echo ================================================================
echo.
echo   - Backend:  http://localhost:5000/api/v1/status
echo   - Frontend: http://localhost:3000
echo.
echo   Abrindo navegador em http://localhost:3000 ...
echo   (Para encerrar, feche as duas janelas que foram abertas)
echo ================================================================
timeout /t 5 /nobreak >nul
start http://localhost:3000
goto end


:run_docker_local
echo.
echo ----------------------------------------------------------------
echo Verificando Docker Desktop...
echo ----------------------------------------------------------------
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Docker Desktop nao esta aberto.
    echo Abra o Docker Desktop e tente novamente, ou use a Opcao 1 (Nativo).
    pause
    goto end
)

echo Subindo containers locais via compose.yml...
start "" cmd /c "timeout /t 8 /nobreak >nul && start http://localhost:3000"
docker compose up --build
goto end


:run_docker_hub
echo.
echo ----------------------------------------------------------------
echo Verificando Docker Desktop...
echo ----------------------------------------------------------------
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Docker Desktop nao esta aberto.
    echo Abra o Docker Desktop e tente novamente, ou use a Opcao 1 (Nativo).
    pause
    goto end
)

echo Puxando e subindo imagens do Docker Hub...
start "" cmd /c "timeout /t 8 /nobreak >nul && start http://localhost:3000"
docker compose -f compose.dockerhub.yml up
goto end


:end
