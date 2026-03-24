import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import os
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile

# --- Модель для эмбеддингов ---
emb_model = SentenceTransformer('all-MiniLM-L6-v2')


# --- Вызов Ollama API с Literary Critic Prompt ---
def call_ollama(prompt, model='qwen3-vl:4b'):
    system_prompt = """
    Ты — литературный критик и помощник по книгам. Твоя задача:

    1. Пересказывать смысл прочитанного (главы, фрагменты, всю книгу).
    2. Работать с книгами, которые тебе присылает пользователь (анализировать, объяснять, отвечать на вопросы).
    3. Находить книги по описанию (например: "книга про космос и любовь").
    4. Находить нужную главу, абзац или предложение в книге по смыслу (например: "где говорится о войне?").
    5. Рекомендовать книги из базы данных, если спрашивают.
    6. Всегда отвечать вежливо, структурировано и по делу.
    7. Если в тексте нет нужной информации — честно говорить об этом.
    """

    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        return data['message']['content']
    else:
        return f"Ошибка: {response.status_code} - {response.text}"


# === Google Books API ===
def search_books_google(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        books = []
        for item in data.get("items", []):
            volume_info = item.get("volumeInfo", {})
            title = volume_info.get("title", "Без названия")
            authors = ", ".join(volume_info.get("authors", ["Неизвестен"]))
            description = volume_info.get("description", "Описание отсутствует.")
            cover_url = volume_info.get("imageLinks", {}).get("thumbnail", "")
            books.append({
                "title": title,
                "authors": authors,
                "description": description,
                "cover_url": cover_url})
            return books
    except Exception as e:
        return [{"error": str(e)}]


# === Project Gutenberg API ===
def fetch_gutenberg_book_text(book_id):
    #Скачивает текст книги с Project Gutenberg по ID.
    url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception:
        # Попробуем .epub
        epub_url = f"https://www.gutenberg.org/ebooks/{book_id}.epub.images"
        try:
            response = requests.get(epub_url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            text = epub_to_text(tmp_path)
            os.unlink(tmp_path)
            return text
        except Exception:
            print(f"❌ Не удалось скачать книгу {book_id}")
            return None


def epub_to_text(epub_path):
    """Конвертирует .epub в текст."""
    book = epub.read_epub(epub_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            texts.append(soup.get_text())
    return "\n\n".join(texts)


# === Хранилище книг ===
class BookStorage:
    def __init__(self):
        self.books = {}
        self.chunks_map = {}
        self.chunk_texts = []
        self.chunk_sources = []
        self.index = None
        self.book_metadata = {}  # Для хранения метаданных: {filename: {"author": ..., "title": ...}}
        self.seen_books = set()  # Для уникальности: {(title, author)}
        print("📦 Storage создан.")

    def _get_unique_key(self, title, author):
        """Генерирует уникальный ключ для книги."""
        key = (title.lower().strip(), author.lower().strip())
        return key

    def add_book(self, filename, text, title=None, author=None):
        if title and author:
            unique_key = self._get_unique_key(title, author)
            if unique_key in self.seen_books:
                print(f"⚠️ Книга '{title}' от '{author}' уже добавлена. Пропускаю.")
                return
            self.seen_books.add(unique_key)

        print(f"📖 Добавляю книг, размер: {len(text)} символов")
        self.books[filename] = text

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50
        )
        chunks = splitter.split_text(text)
        print(f"✂️ Разбил книгу на {len(chunks)} фрагментов")
        self.chunks_map[filename] = [(i, i + len(chunk), chunk) for i, chunk in enumerate(chunks)]

        for chunk in chunks:
            self.chunk_texts.append(chunk)
            self.chunk_sources.append((filename, 0, len(chunk)))

        # Сохраняем метаданные
        if title and author:
            self.book_metadata[filename] = {"title": title, "author": author}

        print("🔄 Вызываю rebuild_index...")
        self._rebuild_index()

    def _rebuild_index(self):
        if not self.chunk_texts:
            print("⚠️ Нет текстов для индекса.")
            self.index = None
            return
        print(f"🔍 Создаю эмбеддинги для {len(self.chunk_texts)} фрагментов...")
        embeddings = emb_model.encode(self.chunk_texts)
        dimension = embeddings.shape[1]
        print(f"🏗️ Создаю индекс FAISS (размерность: {dimension})")
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        print(f"✅ Индекс пересобран. Всего фрагментов: {len(self.chunk_texts)}")

    def search_fragments(self, query, top_k=5):
        print(f"🔍 Ищу фрагменты для запроса: '{query[:50]}...' (top_k={top_k})")
        if not self.index or not self.chunk_texts:
            print("⚠️ Нет индекса или текстов для поиска.")
            return []
        query_vec = emb_model.encode([query])
        scores, indices = self.index.search(query_vec.astype('float32'), k=top_k)
        print(f"📊 Нашёл {len(indices[0])} результатов")
        results = []
        for idx in indices[0]:
            if idx < len(self.chunk_texts):
                chunk = self.chunk_texts[idx]
                source = self.chunk_sources[idx]
                results.append({
                    "chunk": chunk,
                    "source": source[0],
                    "position": f"{source[1]}:{source[2]}"
                })
        print(f"✅ Вернул {len(results)} фрагментов")
        return results
 
    def find_answer_with_quotes(self, question):
        print(f"❓ Ищу ответ на вопрос: '{question[:50]}...'")

        if not self.index or not self.chunk_texts:
            print("⚠️ Нет индекса или текстов для ответа.")
            return {"answer": "Нет загруженных книг.", "quotes": []}

        print(f"🔍 Количество фрагментов в индексе: {len(self.chunk_texts)}")
        query_vec = emb_model.encode([question])
        scores, indices = self.index.search(query_vec.astype('float32'), k=5)
        relevant_chunks = [self.chunk_texts[idx] for idx in indices[0] if idx < len(self.chunk_texts)]
        print(f"🎯 Нашёл {len(relevant_chunks)} релевантных фрагментов")

        if not relevant_chunks:
            print("⚠️ Не найдено релевантных фрагментов.")
            return {"answer": "Нет информации в загруженных текстах.", "quotes": []}

        context = "\n\n".join(relevant_chunks)
        prompt = f"""
        Ответь на вопрос, опираясь только на следующий текст. Если в тексте нет ответа — честно скажи об этом.
        Вопрос: {question}

        Текст:
        {context}
        """

        try:
            print("🤖 Отправляю запрос в Ollama...")
            answer = call_ollama(prompt, model='qwen3-vl:4b')
            quotes = []
            for chunk in relevant_chunks:
                if len(chunk.strip()) > 20:
                    quotes.append(chunk.strip())
            print(f"✅ Ответ сгенерирован. Количество цитат: {len(quotes)}")
            return {"answer": answer, "quotes": quotes}
        except Exception as e:
            print(f"❌ Ошибка при генерации ответа: {e}")
            return {"answer": f"Ошибка: {str(e)}", "quotes": []}

    def upload_books(self, files):
        results = []
        for file_obj in files:
            with open(file_obj.name, 'r', encoding='utf-8') as f:
                text = f.read()
            print(f"📖 Загружаю книгу: {file_obj.name}, размер: {len(text)} символов")
            self.add_book(os.path.basename(file_obj.name), text)
            results.append({"file": os.path.basename(file_obj.name), "status": "uploaded"})
        return results

    # === НОВОЕ: Загрузка всех книг из папки ===
    def load_all_books_from_folder(self, folder_path):
        print(f"📚 Начинаю загрузку всех книг из {folder_path}")
        txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        print(f"📖 Найдено {len(txt_files)} книг для загрузки.")

        for filename in txt_files:
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            # Извлекаем ID из имени файла
            book_id = filename.replace('book_', '').replace('.txt', '')
            title = f"Book_{book_id}"
            author = "Unknown"
            self.add_book(filename, text, title=title, author=author)

        print(f"✅ Все книги из {folder_path} загружены.")


# === Создаём глобальный объект ===
storage = BookStorage() 


# === Функции для API ===
def upload_books(files):
    return storage.upload_books(files)


def search_fragments(query):
    results = storage.search_fragments(query, top_k=5)
    if not results:
        return {"fragments": [], "message": "Фрагменты не найдены в загруженных текстах."}

    output = []
    for res in results:
        output.append({
            "source": res["source"],
            "position": res["position"],
            "fragment": res["chunk"][:200] + "..."
        })
    return {"fragments": output}


def ask_question(question):
    result = storage.find_answer_with_quotes(question)
    return result


def search_books_by_description(desc):
    books = search_books_google(desc)
    return books
