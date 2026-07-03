@echo off
cd /d "%~dp0"
echo ============================================
echo   GEXR Level-Update  (SPY + QQQ)
echo ============================================
echo.
set PY=python
where python >nul 2>nul || set PY=py
%PY% fetch_gex_levels.py SPY --patch GEXR_Style_Matrix.pine
if errorlevel 1 goto err
echo.
%PY% fetch_gex_levels.py QQQ --patch GEXR_Style_Matrix.pine
if errorlevel 1 goto err
powershell -NoProfile -Command "Set-Clipboard -Value (Get-Content -Raw -Encoding UTF8 'GEXR_Style_Matrix.pine')"
echo.
echo ============================================
echo   FERTIG! Der Indikator-Code liegt in der
echo   Zwischenablage. Jetzt in TradingView:
echo   Pine Editor oeffnen - Strg+A - Strg+V -
echo   Speichern. Das war's.
echo ============================================
pause
exit /b
:err
echo.
echo FEHLER beim Datenabruf. Einfach nochmal doppelklicken.
echo Wenn es wieder passiert: Screenshot an Claude schicken.
pause
