@echo off
setlocal
chcp 65001 >nul

rem 優先使用工作區提供的 Python，找不到時再使用系統 Python。
set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

rem 先確認 Python 與 Tkinter 可用，避免雙擊後視窗立即消失。
"%PYTHON_EXE%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo 找不到可用的 Python 3 或 Tkinter。
    echo 請先安裝包含 Tkinter 的 Python 3，再重新雙擊本檔案。
    pause
    exit /b 1
)

pushd "%PROJECT_DIR%"
"%PYTHON_EXE%" "%PROJECT_DIR%main.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo Method Context Picker 執行失敗，錯誤碼：%EXIT_CODE%
    pause
    exit /b %EXIT_CODE%
)

endlocal
