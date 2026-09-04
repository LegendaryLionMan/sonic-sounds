# launch-visible-browser.bat
# Launches the persistent Chrome window that the agent drives via CDP.
# Run this from a normal cmd/PowerShell (not as admin, not from a service).
# The window appears on YOUR desktop (Session 1/2 console).
# After launch, the agent can drive it via http://127.0.0.1:9333 using
# `python tools/visible_browser.py <command>`.

@echo off
setlocal

set CHROME_BIN=C:\Users\lion_\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe
set PROFILE_DIR=C:\Users\lion_\AppData\Local\hermes\profiles\chrome-sonic-studio
set CDP_PORT=9333
set START_URL=http://127.0.0.1:8765/site/library.html
set LOG_DIR=%LOCALAPPDATA%\hermes\logs
set LOG_FILE=%LOG_DIR%\chrome-sonic-studio.log

REM Ensure dirs exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

REM Check if CDP is already responding (chrome already running)
curl -sf -m 2 http://127.0.0.1:%CDP_PORT%/json/version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo CDP already responding on port %CDP_PORT%. Reusing existing Chrome.
    goto :end
)

REM Kill any stale chrome instances with this profile to avoid lock conflicts
taskkill /F /FI "WINDOWTITLE eq sonic-studio-verify*" 2>nul >nul
taskkill /F /FI "IMAGENAME eq chrome.exe" /FI "WINDOWTITLE eq sonic-studio*" 2>nul >nul

echo [%date% %time%] Launching visible browser >> "%LOG_FILE%"
echo Starting Chrome with profile %PROFILE_DIR%

start "" "%CHROME_BIN%" ^
  --remote-debugging-port=%CDP_PORT% ^
  --user-data-dir="%PROFILE_DIR%" ^
  --window-name=sonic-studio-verify ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-background-timer-throttling ^
  --disable-features=TranslateUI ^
  --window-size=1280,820 ^
  --window-position=200,150 ^
  "%START_URL%"

REM Wait for CDP to come up (up to 15s)
echo Waiting for CDP to come up on port %CDP_PORT%...
set /a count=0
:wait_cdp
set /a count+=1
if %count% gtr 15 (
    echo Timed out waiting for CDP. Check chrome log: %LOG_FILE%
    goto :end
)
curl -sf -m 1 http://127.0.0.1:%CDP_PORT%/json/version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo CDP ready after %count%s.
    goto :end
)
timeout /t 1 /nobreak >nul
goto :wait_cdp

:end
echo.
echo Chrome is up at port %CDP_PORT%. Drive via:
echo   python tools\visible_browser.py status
echo   python tools\visible_browser.py nav http://127.0.0.1:8765/site/albums.html
echo   python tools\visible_browser.py click ".album-card[data-id='half-light-hours']"
endlocal
