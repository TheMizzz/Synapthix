@echo off
chcp 65001 >nul
title Launch Synapthix API

echo 🚀 Запуск Synapthix API...
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo "❌ Python не найден!"
    echo "📦 Скачиваю и устанавливаю Python..."
    echo.
    REM Скачиваем Python (портативную версию)
    if not exist "python-installer.exe" (
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python-installer.exe'"
    )
    echo "✅ Установщик Python скачан."
    echo.
    echo "🔧 Запускаю установку Python (добавлю в PATH)..."
    python-installer.exe /quiet PrependPath=1 Include_test=0
 5 /nobreak >nul
    del python-installer.exe
    echo "✅ Python установлен."
    echo.
)

echo "🐍 Проверяю версию Python..."
python --version
echo.
echo "📦 Устанавливаю зависимости через pip..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "✅ Зависимости установлены."
echo.
python synapthix-installer.py

REM Проверка, установлен ли ollama в PATH
echo "🔍 Проверяю, установлена ли Ollama в PATH..."
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo "✅ Ollama уже установлена и доступна в PATH."
) else (
    echo "❌ Ollama не найдена в PATH. Пытаюсь найти и добавить..."
    echo.

    REM Попробуем найти ollama.exe в стандартных местах
    set OLLAMA_PATH=
    if exist "C:\Program Files\Ollama\ollama.exe" (
        set OLLAMA_PATH=C:\Program Files\Ollama
    ) else if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set OLLAMA_PATH=%LOCALAPPDATA%\Programs\Ollama
    )

    if defined OLLAMA_PATH (
        echo "✅ Найдена Ollama в: %OLLAMA_PATH%"
        echo "🔧 Добавляю в PATH..."

        REM Добавляем в PATH для текущей сессии
        set "PATH=%PATH%;%OLLAMA_PATH%"

        REM Добавляем в PATH для системы (требует права администратора)
        echo "🔑 Пытаюсь добавить в системный PATH..."
        reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path /t REG_EXPAND_SZ /d "%PATH%" /f 2>nul
        if %errorlevel% equ 0 (
            echo "✅ Ollama добавлена в системный PATH."
        ) else (
            echo "⚠️ Не удалось добавить в системный PATH. Попробуй запустить от имени администратора."
        )
    ) else (
        echo "❌ Ollama не найдена ни в одном из стандартных мест."
        echo "👉 Убедитесь, что Ollama установлена."
    )
)


REM Проверка, запущен ли ollama serve
echo "🔍 Проверяю, запущен ли Ollama сервер (ollama serve)..."
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo "✅ Ollama сервер запущен."
) else (
    echo "💡 Ollama сервер не запущен. Запускаю в фоне..."
    start "" ollama serve
    echo "⏳ Жду запуска сервера (5 секунд)..."
    timeout /t 5 /nobreak >nul
    REM Повторная проверка
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% equ 0 (
        echo "✅ Ollama сервер запущен."
    ) else (
        echo "❌ Не удалось запустить Ollama сервер. Проверьте вручную."
    )
)

REM Проверка, установлена ли модель qwen3-vl:4b
echo "🔍 Проверяю, установлена ли модель qwen3-vl:4b..."
ollama show qwen3-vl:4b >nul 2>&1

if %errorlevel% equ 0 (
    echo "✅ Модель qwen3-vl:4b уже установлена."
) else (
    echo "⚠️ Модель qwen3-vl:4b не найдена. Скачиваю..."
    echo.
    echo "📥 Скачиваю модель qwen3-vl:4b (ожидайте, может занять время)..."
    ollama pull qwen3-vl:4b
    if %errorlevel% equ 0 (
        echo "✅ Модель qwen3-vl:4b успешно скачана."
    ) else (
        echo "❌ Ошибка при скачивании модели qwen3-vl:4b."
        pause
        exit /b 1
    )
)


echo.
echo "🌐 Запускаю FastAPI сервер (UI будет доступен по http://localhost:8000/static/index.html)..."
python -m uvicorn api.synapthix_api:app --host 0.0.0.0 --port 8000
echo.

echo "📝 Нажмите любую клавишу для выхода..."
pause >nul