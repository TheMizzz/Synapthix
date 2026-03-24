const API_BASE = '/api';

// === Остальные функции остаются как есть ===

function setActiveTab(tabName) {
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');
        setActiveTab(tabName);
    });
});

// === Функции для API ===

async function searchBooks() {
    const desc = document.getElementById('book-desc').value;
    const formData = new FormData();
    formData.append('description', desc);

    const response = await fetch(`${API_BASE}/search_books`, {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    const resultsDiv = document.getElementById('search-results');
    resultsDiv.innerHTML = '';

    if (data.books.length === 0 || (data.books[0] && data.books[0].error)) {
        resultsDiv.innerHTML = '<p>Книги не найдены.</p>';
        return;
    }

    data.books.forEach(book => {
        const div = document.createElement('div');
        div.innerHTML = `
            <h4>${book.title}</h4>
            <p><strong>Автор:</strong> ${book.authors}</p>
            <p>${book.description}</p>
        `;
        resultsDiv.appendChild(div);
    });
}

async function uploadBooks() {
    const filesInput = document.getElementById('book-files');
    const files = filesInput.files;

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = `<p>Загружено ${data.result.length} файлов.</p>`;
}

async function searchFragments() {
    const query = document.getElementById('fragment-query').value;
    const formData = new FormData();
    formData.append('query', query);

    const response = await fetch(`${API_BASE}/search_fragments`, {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    const resultsDiv = document.getElementById('fragment-results');
    resultsDiv.innerHTML = '';

    if (data.fragments.length === 0) {
        resultsDiv.innerHTML = '<p>Фрагменты не найдены.</p>';
        return;
    }

    data.fragments.forEach(fragment => {
        const div = document.createElement('div');
        div.innerHTML = `
            <p><strong>Источник:</strong> ${fragment.source}</p>
            <p>${fragment.fragment}</p>
        `;
        resultsDiv.appendChild(div);
    });
}

async function askQuestion() {
    const question = document.getElementById('question-input').value;

    const response = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question })
    });

    const data = await response.json();
    const answerDiv = document.getElementById('answer-result');
    const quotesDiv = document.getElementById('quotes-result');

    answerDiv.innerHTML = `<h4>Ответ:</h4><p>${data.answer}</p>`;
    if (data.quotes.length > 0) {
        quotesDiv.innerHTML = `<h4>Цитаты:</h4>`;
        data.quotes.forEach(quote => {
            const p = document.createElement('p');
            p.textContent = `"${quote}"`;
            quotesDiv.appendChild(p);
        });
    } else {
        quotesDiv.innerHTML = `<p>Цитаты отсутствуют.</p>`;
    }
}