from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import FileResponse
import json
import os

app = FastAPI()

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="ui/static"), name="static")

# Импортируем всё из backend
from backend.synapthix_backend import (
    search_books_by_description,
    search_fragments,
    ask_question,
    upload_books,
    storage  # ✅ Импортируем storage
)

# === НОВОЕ: Автозагрузка книг из папки при старте сервера ===
BOOKS_FOLDER = "./books/my_books"


@app.on_event('startup')
def startup_event():
    print("🚀 Сервер запускается...")
    print(f"📚 Проверяю папку: {os.path.abspath(BOOKS_FOLDER)}")
    if os.path.exists(BOOKS_FOLDER):
        print("📁 Папка найдена. Загружаю книги...")
        storage.load_all_books_from_folder(BOOKS_FOLDER)
    else:
        print(f"❌ Папка {BOOKS_FOLDER} не найдена. Пропускаю загрузку книг.")


class QuestionRequest(BaseModel):
    question: str


@app.post("/api/search_books")
async def search_books(description: str = Form(...)):
    books = search_books_by_description(description)
    return {"books": books}


@app.post("/api/search_fragments")
async def search_text_fragments(query: str = Form(...)):
    fragments = search_fragments(query)
    return fragments


@app.post("/api/ask")
async def ask(q: QuestionRequest):
    result = ask_question(q.question)
    return result


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    # Сохраняем файлы во временные пути
    temp_files = []
    for file in files:
        temp_name = f"temp_{file.filename}"
        with open(temp_name, "wb") as f:
            f.write(await file.read())
        # Создаём объект с атрибутом name
        temp_file_obj = type('obj', (object,), {'name': temp_name})()
        temp_files.append(temp_file_obj)

    result = upload_books(temp_files)
    # Удаляем временные файлы
    for file in temp_files:
        os.remove(file.name)
    return {"result": result}


# Главная страница — отдаём HTML
@app.get("/")
async def read_root():
    return {"message": "Synapthix API is running. Visit /static/index.html for UI."}


# Отдаём index.html по умолчанию
@app.get("/ui")
async def serve_ui():
    return FileResponse("../ui/static/index.html")