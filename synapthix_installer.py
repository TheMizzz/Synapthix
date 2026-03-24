import os
import platform
import subprocess
import sys
import time
import requests
import tempfile
import json
from tqdm import tqdm

STATUS_FILE = "status.json"
OLLAMA_MODEL = "qwen3-vl:4b"


def update_status(step, progress, message):
    #Записывает статус в JSON-файл.
    data = {"step": step, "progress": progress, "message": message}
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def install_dependencies():
    #Устанавливает зависимости через pip.
    import os
    print("📦 Устанавливаю зависимости через pip...")

    # Получаем директорию, где лежит сам скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(script_dir, "requirements.txt")

    if not os.path.exists(req_file):
        print(f"❌ Файл {req_file} не найден!")
        sys.exit(1)

    # Запускаем pip install с указанием файла
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=True)
    print("✅ Зависимости установлены.")
    update_status("installing_deps", 20, "Зависимости установлены.")


def check_ollama_installed():
    #Проверяет, установлен ли Ollama.
    try:
        # Попробуем запустить `ollama --version`
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Ollama уже установлена.")
            return True
        else:
            print(f"⚠️ Ollama установлена, но --version вернул ошибку: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Ollama не найдена в PATH.")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️ Команда ollama --version зависла.")
        return False
    except Exception as e:
        print(f"⚠️ Ошибка при проверке Ollama: {e}")
        return False

def download_with_progress(url, dest_path):
    #Скачивает файл с отображением прогресса.
    print(f"📥 Скачиваю {dest_path}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    with open(dest_path, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(dest_path)) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))


def install_ollama_windows():
    #Скачивает и устанавливает Ollama для Windows
    arch = platform.architecture()[0]
    if arch != "64bit":
        print("❌ Ollama не поддерживает 32-битные версии Windows.")
        print("👉 Пожалуйста, скачай и установи Ollama вручную: https://ollama.com/download")
        input("После установки нажми Enter для продолжения...")
        return

    print("📥 Скачиваю Ollama для Windows (64-bit)...")
    update_status("installing_ollama", 30, "Скачиваю Ollama для Windows...")
    url = "https://ollama.com/download/OllamaSetup.exe"
    temp_dir = tempfile.mkdtemp()
    installer_path = os.path.join(temp_dir, "OllamaSetup.exe")

    try:
        download_with_progress(url, installer_path)
        print("✅ Установочный файл скачан.")
        update_status("installing_ollama", 40, "Установочный файл скачан.")

        print("🔧 Запускаю установку Ollama...")
        update_status("installing_ollama", 50, "Запускаю установку Ollama...")
        subprocess.run([installer_path], check=True)
        print("✅ Ollama установлена.")
        update_status("installing_ollama", 60, "Ollama установлена.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Установка завершилась с ошибкой: {e}")
        print("Твоя версия Windows имеет особенную структуру")
        print("👉 Попробуй запустить установку вручную: https://ollama.com/download")
        input("После проверки нажми Enter для продолжения...")
    except Exception as e:
        print(f"❌ Ошибка при установке: {e}")
        print("👉 Пожалуйста, скачай и установи Ollama вручную: https://ollama.com/download")
        input("После установки нажми Enter для продолжения...")


def install_ollama_linux_mac():
    #Устанавливает Ollama на Linux/macOS
    print("📥 Скачиваю и запускаю официальный скрипт установки Ollama...")
    update_status("installing_ollama", 30, "Скачиваю и запускаю установку Ollama для Linux/macOS...")
    try:
        # Для Linux скачиваем напрямую бинарник
        system = platform.system().lower()
        if system == "linux":
            arch = platform.machine()
            if arch == "x86_64":
                arch = "amd64"
            elif arch == "aarch64":
                arch = "arm64"
            else:
                print(f"❌ Архитектура {arch} не поддерживается.")
                sys.exit(1)

            url = f"https://ollama.ai/download/ollama-linux-{arch}"
            temp_dir = tempfile.mkdtemp()
            binary_path = os.path.join(temp_dir, "ollama")

            download_with_progress(url, binary_path)

            # Устанавливаем бинарник
            subprocess.run(["sudo", "install", "-o0", "-g0", "-m755", binary_path, "/usr/local/bin/ollama"], check=True)
            print("✅ Ollama установлена.")
            update_status("installing_ollama", 60, "Ollama установлена.")
        else:
            # macOS — используем официальный скрипт
            subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
            print("✅ Ollama установлена.")
            update_status("installing_ollama", 60, "Ollama установлена.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при установке: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при скачивании: {e}")
        sys.exit(1)


def install_ollama():
    #Устанавливает Ollama в зависимости от ОС.
    system = platform.system().lower()
    print(f"Установка Ollama для {system}...")
    update_status("installing_ollama", 25, f"Установка Ollama для {system}...")

    if system == "windows":
        install_ollama_windows()
    elif system in ("linux", "darwin"):
        install_ollama_linux_mac()
    else:
        print(f"❌ ОС {system} не поддерживается автоматически.")
        sys.exit(1)


def download_model():
    #Скачивает модель Ollama.
    print(f"Скачиваю модель {OLLAMA_MODEL}...")
    update_status("downloading_model", 70, f"Скачиваю модель {OLLAMA_MODEL}...")

    result = subprocess.run(["ollama", "pull", OLLAMA_MODEL], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Ошибка при скачивании модели: {result.stderr}")
        sys.exit(1)

    print("✅ Модель успешно скачана!")
    update_status("downloading_model", 90, f"Модель {OLLAMA_MODEL} скачана.")


def check_ollama_running():
    #Проверяет, запущен ли сервер Ollama.
    try:
        result = subprocess.run(["curl", "-s", "http://localhost:11434/api/tags"], capture_output=True, text=True)
        if result.returncode == 0 and OLLAMA_MODEL in result.stdout:
            return True
        return False
    except Exception:
        return False


def find_ollama_executable():
    #Находит исполняемый файл ollama.exe в системе.
    system = platform.system().lower()

    if system == "windows":
        possible_paths = [
            r"C:\Program Files\Ollama\ollama.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe",
            "ollama"
        ]
        for path in possible_paths:
            expanded = os.path.expandvars(path)
            if os.path.isfile(expanded):
                return expanded
    else:
        return "ollama"
    return None


def start_ollama_server():
    #Запускает Ollama сервер в фоне.
    print("🔄 Проверяю, запущен ли Ollama сервер...")

    if check_ollama_running():
        print("💡 Ollama сервер уже запущен.")
        update_status("starting_ollama", 100, "Ollama сервер уже запущен.")
        return

    print("💡 Запускаю Ollama сервер в фоне...")
    update_status("starting_ollama", 95, "Запускаю Ollama сервер...")
    ollama_exe = find_ollama_executable()

    if not ollama_exe:
        print("❌ Не удалось найти ollama. Убедитесь, что Ollama установлена.")
        sys.exit(1)

    subprocess.Popen([ollama_exe, "serve"])
    time.sleep(5)
    update_status("starting_ollama", 100, "Ollama сервер запущен.")


def main():
    print("📦 Запуск инсталлера Synapthix...")
    PROJECT_FOLDER = "Synapthix"
    MODELS_DIR_NAME = "models"

    # Создаём папку проекта
    if not os.path.exists(PROJECT_FOLDER):
        os.makedirs(PROJECT_FOLDER)

    # Меняем директорию
    os.chdir(PROJECT_FOLDER)

    # Начинаем с 0%
    update_status("starting", 0, "Запуск инсталлера...")

    install_dependencies()

    if not check_ollama_installed():
        print("⚠️ Ollama не найдена. Устанавливаю...")
        install_ollama()

    print("🔄 Проверяю, запущен ли Ollama...")
    if not check_ollama_running():
        start_ollama_server()
        if not check_ollama_running():
            print("❌ Не удалось запустить Ollama. Убедитесь, что она запущена.")
            sys.exit(1)

    print("🔍 Проверяю наличие модели...")
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if OLLAMA_MODEL not in result.stdout:
        print(f"⚠️ Модель {OLLAMA_MODEL} не найдена. Скачиваю...")
        download_model()
    else:
        print(f"✅ Модель {OLLAMA_MODEL} уже установлена.")

    print("\n🎉 Все готово! Synapthix установлен.")
    update_status("done", 100, "Synapthix установлен и готов к работе.")


if __name__ == "__main__":
    main()
