import os
import re
import hashlib
import sqlite3
import json
from flask import Flask, render_template_string, request, url_for, g

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), 'wishlist.db')

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Книжный вишлист</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #f5f0e6; font-family: Georgia, serif; padding: 10px; margin: 0; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; }
        h1 { color: #3e2e1f; font-size: 24px; }
        textarea { width: 100%; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #ccc; font-size: 14px; box-sizing: border-box; }
        button { background: #b99e7c; color: white; padding: 12px 20px; border: none; border-radius: 40px; cursor: pointer; font-size: 16px; margin-right: 10px; margin-bottom: 10px; }
        button:hover { background: #a08462; }
        .controls { margin: 20px 0; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        .sort-select, .filter-select { padding: 8px; border-radius: 20px; border: 1px solid #ccc; background: white; }
        .book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }
        .book-card { text-align: center; padding: 15px; border: 1px solid #e2d5c0; border-radius: 8px; background: #fffcf5; }
        .book-image { width: 120px; height: 160px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9; }
        .book-title { margin: 8px 0; font-weight: bold; font-size: 14px; color: #2c1e12; min-height: 40px; overflow: hidden; }
        .book-price { font-size: 18px; color: #b12704; margin: 5px 0; }
        .book-old-price { font-size: 14px; color: #666; text-decoration: line-through; margin-right: 8px; }
        .book-link { display: inline-block; padding: 6px 12px; background: #f2e8d8; border-radius: 20px; text-decoration: none; color: #3e2e1f; font-size: 13px; }
        .book-link:hover { background: #b99e7c; color: white; }
        .stats { margin-top: 20px; color: #666; }
        .share-link { margin-top: 20px; padding: 15px; background: #f2e8d8; border-radius: 8px; word-break: break-all; }
        .share-link input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .loading { display: none; text-align: center; padding: 20px; }
        .price-filter { display: flex; flex-wrap: wrap; gap: 5px; margin: 10px 0; }
        .price-filter button { background: #e2d5c0; color: #3e2e1f; padding: 5px 10px; border: none; border-radius: 20px; cursor: pointer; font-size: 12px; }
        .price-filter button.active { background: #b99e7c; color: white; }
        @media (max-width: 600px) {
            .book-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
            .book-image { width: 100px; height: 140px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Книжный вишлист</h1>
        <form method="post" id="mainForm" onsubmit="showLoading()">
            <textarea name="links" rows="8" placeholder="Вставьте ссылки на Wildberries (каждая с новой строки)">{{ request.form.get('links', '') }}</textarea>
            <br>
            <button type="submit" name="action" value="show">📋 Только показать</button>
            <button type="submit" name="action" value="save">💾 Сохранить и получить ссылку</button>
            <div class="loading" id="loading">⏳ Загрузка данных с Wildberries, это может занять некоторое время...</div>
        </form>
        {% if saved_url %}
        <div class="share-link">
            <h3>🔗 Ссылка на ваш вишлист:</h3>
            <input type="text" value="{{ saved_url }}" readonly onclick="this.select()">
            <p>Скопируйте и отправьте друзьям!</p>
        </div>
        {% endif %}
        {% if books %}
        <div class="controls">
            <select class="sort-select" id="sortSelect">
                <option value="price-asc">По цене (сначала дешёвые)</option>
                <option value="price-desc">По цене (сначала дорогие)</option>
                <option value="title">По названию</option>
            </select>
            <div class="price-filter" id="priceFilter">
                <button data-min="0" data-max="350">до 350 ₽</button>
                <button data-min="351" data-max="550">351-550 ₽</button>
                <button data-min="551" data-max="1200">551-1200 ₽</button>
                <button data-min="1201" data-max="1800">1201-1800 ₽</button>
                <button data-min="1801" data-max="2200">1801-2200 ₽</button>
                <button data-min="2201" data-max="3500">2201-3500 ₽</button>
                <button data-min="3501" data-max="5000">3501-5000 ₽</button>
                <button data-min="5001" data-max="7000">5001-7000 ₽</button>
                <button data-min="7001" data-max="999999">от 7001 ₽</button>
                <button data-min="0" data-max="999999" class="active">Все</button>
            </div>
        </div>
        <div class="book-grid" id="bookGrid">
            {% for book in books %}
            <div class="book-card" data-price="{{ book.price }}" data-title="{{ book.title }}">
                <img class="book-image" 
                     src="https://basket-01.wbbasket.ru/vol{{ book.vol }}/part{{ book.part }}/{{ book.art }}/images/big/1.webp"
                     onerror="loadImage(this, '{{ book.vol }}', '{{ book.part }}', '{{ book.art }}')"
                     alt="{{ book.title }}">
                <div class="book-title">{{ book.title }}</div>
                <div class="book-price">
                    {% if book.old_price and book.old_price > book.price %}
                        <span class="book-old-price">{{ book.old_price }} ₽</span>
                    {% endif %}
                    {{ book.price }} ₽
                </div>
                <a class="book-link" href="{{ book.url }}" target="_blank">📖 Открыть</a>
            </div>
            {% endfor %}
        </div>
        <div class="stats">Найдено книг: <span id="bookCount">{{ books|length }}</span></div>
        {% endif %}
    </div>
    <script>
    function loadImage(img, vol, part, art, attempt = 1) {
        if (attempt > 50) {
            img.src = "https://images.wbstatic.net/big/" + art + "1.jpg";
            img.onerror = function() {
                img.src = "https://via.placeholder.com/300x400?text=Нет+обложки";
                img.onerror = null;
            };
            return;
        }
        const basketNum = attempt.toString().padStart(2, '0');
        img.src = `https://basket-${basketNum}.wbbasket.ru/vol${vol}/part${part}/${art}/images/big/1.webp`;
        img.onerror = function() {
            loadImage(img, vol, part, art, attempt + 1);
        };
    }
    function showLoading() {
        document.getElementById('loading').style.display = 'block';
    }
    document.addEventListener('DOMContentLoaded', function() {
        const bookGrid = document.getElementById('bookGrid');
        if (!bookGrid) return;
        const bookCards = Array.from(document.querySelectorAll('.book-card'));
        const sortSelect = document.getElementById('sortSelect');
        const priceFilter = document.getElementById('priceFilter');
        const bookCountSpan = document.getElementById('bookCount');
        let currentFilterMin = 0;
        let currentFilterMax = 999999;
        function filterAndSort() {
            let filtered = bookCards.filter(card => {
                const price = parseInt(card.dataset.price);
                return price >= currentFilterMin && price <= currentFilterMax;
            });
            const sortValue = sortSelect.value;
            filtered.sort((a, b) => {
                if (sortValue === 'price-asc') {
                    return parseInt(a.dataset.price) - parseInt(b.dataset.price);
                } else if (sortValue === 'price-desc') {
                    return parseInt(b.dataset.price) - parseInt(a.dataset.price);
                } else if (sortValue === 'title') {
                    return a.dataset.title.localeCompare(b.dataset.title);
                }
            });
            bookGrid.innerHTML = '';
            filtered.forEach(card => bookGrid.appendChild(card));
            bookCountSpan.textContent = filtered.length;
        }
        sortSelect.addEventListener('change', filterAndSort);
        priceFilter.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON') {
                priceFilter.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                currentFilterMin = parseInt(e.target.dataset.min);
                currentFilterMax = parseInt(e.target.dataset.max);
                filterAndSort();
            }
        });
        filterAndSort();
    });
    </script>
</body>
</html>
'''

# ----- Работа с БД -----
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wishlists (
                id TEXT PRIMARY KEY,
                arts TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                books_data TEXT
            )
        ''')
        db.commit()

def get_wishlist_from_db(wish_id):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT books_data FROM wishlists WHERE id = ?', (wish_id,))
        row = cursor.fetchone()
        if row and row['books_data']:
            return json.loads(row['books_data'])
        return None

def extract_articul(link):
    match = re.search(r'catalog/(\d+)', link)
    return match.group(1) if match else None

def get_vol_part(art):
    art = str(art)
    vol = art[:4]
    part = art[:6]
    return vol, part

def generate_hash(arts):
    data = ','.join(sorted(arts))
    return hashlib.md5(data.encode()).hexdigest()[:8]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        raw_links = request.form.get('links', '').splitlines()
        links = [l.strip() for l in raw_links if l.strip()]
        action = request.form.get('action', 'show')
        if not links:
            return render_template_string(INDEX_TEMPLATE, error='Введите ссылки')
        arts = set()
        for link in links:
            art = extract_articul(link)
            if art:
                arts.add(art)
        arts_list = list(arts)
        if action == 'save':
            wish_id = generate_hash(arts_list)
            with app.app_context():
                db = get_db()
                cursor = db.cursor()
                cursor.execute('INSERT OR REPLACE INTO wishlists (id, arts) VALUES (?, ?)',
                               (wish_id, ','.join(arts_list)))
                db.commit()
            saved_url = url_for('show_wishlist', wish_id=wish_id, _external=True)
            # Показываем заглушку (без названий/цен, только артикулы)
            books_data = []
            for art in arts_list:
                vol, part = get_vol_part(art)
                books_data.append({
                    'art': art,
                    'vol': vol,
                    'part': part,
                    'title': f'Книга {art}',
                    'price': 0,
                    'old_price': None,
                    'url': f'https://www.wildberries.ru/catalog/{art}/detail.aspx'
                })
            return render_template_string(INDEX_TEMPLATE, books=books_data, saved_url=saved_url, request=request)
        else:
            # Режим "только показать" – формируем заглушку без сохранения
            books_data = []
            for art in arts_list:
                vol, part = get_vol_part(art)
                books_data.append({
                    'art': art,
                    'vol': vol,
                    'part': part,
                    'title': f'Книга {art}',
                    'price': 0,
                    'old_price': None,
                    'url': f'https://www.wildberries.ru/catalog/{art}/detail.aspx'
                })
            return render_template_string(INDEX_TEMPLATE, books=books_data, request=request)
    return render_template_string(INDEX_TEMPLATE)

@app.route('/wishlist/<wish_id>')
def show_wishlist(wish_id):
    books_data = get_wishlist_from_db(wish_id)
    if books_data is None:
        # Если данных нет, пробуем достать список артикулов из колонки arts
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT arts FROM wishlists WHERE id = ?', (wish_id,))
            row = cursor.fetchone()
            if not row:
                return "Вишлист не найден. Возможно, он был удалён или ещё не создан.", 404
            arts_list = row['arts'].split(',')
        books_data = []
        for art in arts_list:
            vol, part = get_vol_part(art)
            books_data.append({
                'art': art,
                'vol': vol,
                'part': part,
                'title': f'Книга {art}',
                'price': 0,
                'old_price': None,
                'url': f'https://www.wildberries.ru/catalog/{art}/detail.aspx'
            })
    else:
        for book in books_data:
            vol, part = get_vol_part(book['art'])
            book['vol'] = vol
            book['part'] = part
    return render_template_string(INDEX_TEMPLATE, books=books_data)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)