@echo off
setlocal
echo Iniciando Integrated Web...
where py >nul 2>nul
if %errorlevel%==0 (
  start "Integrated Web - Iniciador local" py -3 "%~dp0web_launcher.py"
) else (
  start "Integrated Web - Iniciador local" python "%~dp0web_launcher.py"
)
echo El iniciador abrira Integrated en el navegador.
echo Pulsa "Minimizar iniciador" en la aplicacion para minimizar esta ventana.
echo No cierres esta ventana si quieres detectar puertos o cargar programas.
