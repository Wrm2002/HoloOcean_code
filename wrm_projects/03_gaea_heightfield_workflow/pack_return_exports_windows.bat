@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "EXPORT_DIR=%SCRIPT_DIR%04_put_gaea_exports_here"
set "RETURN_ZIP=%SCRIPT_DIR%WRM_Gaea_Exports_Return_20260603.zip"
if "%WRM_LINUX_PROJECT_ROOT%"=="" set "WRM_LINUX_PROJECT_ROOT=<your Linux holoocean checkout>"

if not exist "%EXPORT_DIR%" (
  echo Missing export directory:
  echo %EXPORT_DIR%
  pause
  exit /b 1
)

if exist "%RETURN_ZIP%" del "%RETURN_ZIP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Compress-Archive -Path '%EXPORT_DIR%\\*' -DestinationPath '%RETURN_ZIP%' -Force"

if errorlevel 1 (
  echo Failed to create return zip.
  pause
  exit /b 1
)

echo Created:
echo %RETURN_ZIP%
echo.
echo Send/copy this zip back to Linux, then put its contents in:
echo %WRM_LINUX_PROJECT_ROOT%/wrm_projects/03_gaea_heightfield_workflow/02_gaea_export_dropbox
pause
