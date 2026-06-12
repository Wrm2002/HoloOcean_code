@echo off
setlocal
set ROOT=C:\Users\11049\Desktop\WRM_Windows_GPT_Handoff_2026-06-08
set GAEA=C:\Program Files\QuadSpinner\Gaea 2\Gaea.Swarm.exe
set TERRAIN=D:\WRM_Gaea_Windows_Handoff_20260603\05_return_to_linux\x0_y0_gui_build.terrain
set LOG=%ROOT%\wrm_projects\05_validation_outputs\gaea_cli_probe_20260609\gaea_swarm_bat_run.log
echo ==== %DATE% %TIME% ==== > "%LOG%"
echo GAEA=%GAEA% >> "%LOG%"
echo TERRAIN=%TERRAIN% >> "%LOG%"
"%GAEA%" -filename "%TERRAIN%" >> "%LOG%" 2>&1
echo EXITCODE=%ERRORLEVEL% >> "%LOG%"
exit /b %ERRORLEVEL%
