@echo off
setlocal enabledelayedexpansion

REM Configuration
set BAR_WIDTH=30
set WARMUP_RUNS=10
set WARMUP_N=500
set MEASURE_RUNS=30
set MEASURE_N=1000
set COOLDOWN=60
set OUTPUT_DIR=output

REM Note: On Windows, only the 'carbon' profiler is available.
REM The 'mac-silicon' profiler (zeus_apple_silicon) is macOS-only.

echo.
echo ======================================================
echo   Energy Measurement (Windows - CodeCarbon only)
echo ======================================================
echo.
echo WARNING: Do not interrupt - results may be incomplete.

REM 1. Warm-up phase
echo.
echo -- Phase 1: Warm-up (%WARMUP_RUNS% iterations) --
echo.

for /L %%i in (1,1,%WARMUP_RUNS%) do (
    uv run ET -p carbon -n %WARMUP_N% -o warmup-%%i --shuffle
    echo   Warm-up %%i/%WARMUP_RUNS% complete.
)
echo   Warm-up complete.

if exist "%OUTPUT_DIR%\" (
    rmdir /s /q "%OUTPUT_DIR%"
)

REM 2. Measurement phase
echo.
echo -- Phase 2: Measurement (%MEASURE_RUNS% iterations - with cooldown periods of %COOLDOWN%s) --
echo.

for /L %%i in (1,1,%MEASURE_RUNS%) do (
    timeout /t %COOLDOWN% /nobreak >nul

    uv run ET -p carbon -n %MEASURE_N% -o measure-%%i --shuffle
    echo   Measurement %%i/%MEASURE_RUNS% complete.
)
echo   Measurement complete.

REM 3. End
echo.
echo -- All done! Results are in the '%OUTPUT_DIR%\' directory. --

endlocal
