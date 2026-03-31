import os
import re
import hashlib
import sqlite3
import json
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request, url_for, g

app = Flask(__name__)

# Путь к базе данных
DATABASE = os.path.join(os.path.dirname(__file__), 'wishlist.db')

# HTML-шаблон (с сортировкой и фильтрацией) – без изменений
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

    // Сортировка и фильтрация
    document.addEventListener('DOMContentLoaded', function() {
        const bookGrid = document.getElementById('bookGrid');
        const bookCards = Array.from(document.querySelectorAll('.book-card'));
        const sortSelect = document.getElementById('sortSelect');
        const priceFilter = document.getElementById('priceFilter');
        const bookCountSpan = document.getElementById('bookCount');

        let currentFilterMin = 0;
        let currentFilterMax = 999999;

        function filterAndSort() {
            // Фильтр по цене
            let filtered = bookCards.filter(card => {
                const price = parseInt(card.dataset.price);
                return price >= currentFilterMin && price <= currentFilterMax;
            });

            // Сортировка
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

            // Перестроить DOM
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

# ------------------ Работа с базой данных ------------------
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("PRAGMA table_info(wishlists)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'books_data' not in columns:
            cursor.execute("ALTER TABLE wishlists ADD COLUMN books_data TEXT")
            db.commit()
            print("✅ Добавлена колонка books_data в таблицу wishlists")
        db.commit()

# ------------------ Функция получения данных (API поиска + fallback) ------------------
def fetch_book_data(art):
    """Получить данные о книге сначала через поисковый API, затем через HTML-парсинг"""
    # 1. Пытаемся через поисковый API (ранее работал)
    search_url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {
        'query': art,
        'resultset': 'catalog',
        'sort': 'popular',
        'limit': 1,
        'spp': '30',
        'curr': 'rub',
        'dest': '-1257786'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.wildberries.ru/',
        'Origin': 'https://www.wildberries.ru',
    }
    try:
        time.sleep(1.5)  # задержка между запросами
        resp = requests.get(search_url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get('data', {}).get('products', [])
            if products and str(products[0].get('id')) == art:
                prod = products[0]
                title = prod.get('name', f'Книга {art}')
                price = prod.get('salePriceU') or prod.get('priceU', 0)
                old_price = prod.get('priceU', 0)
                price = price // 100 if price else 0
                old_price = old_price // 100 if old_price else 0
                return {
                    'art': art,
                    'title': title,
                    'price': price,
                    'old_price': old_price if old_price > price else None,
                    'url': f'https://www.wildberries.ru/catalog/{art}/detail.aspx'
                }
        else:
            print(f"⚠️ Поисковый API для {art} вернул статус {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Ошибка поискового API для {art}: {e}")

    # 2. Если поисковый API не сработал, пробуем парсинг HTML
    return parse_html_fallback(art)

def parse_html_fallback(art):
    """Запасной метод: парсинг HTML страницы товара"""
    url = f"https://www.wildberries.ru/catalog/{art}/detail.aspx"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Ошибка загрузки страницы для {art}: статус {resp.status_code}")
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Название
        title = f'Книга {art}'
        title_tag = soup.find('h1', class_='product-page__title')
        if not title_tag:
            title_tag = soup.find('h1')
        if title_tag:
            title = title_tag.text.strip()

        # Цены
        price = 0
        old_price = None

        # Ищем в JSON-скрипте
        script_tag = soup.find('script', text=re.compile(r'window\.__IM__\s*='))
        if script_tag:
            script_text = script_tag.string
            match = re.search(r'window\.__IM__\s*=\s*({.*?});\s*$', script_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    products = data.get('state', {}).get('products', [])
                    if products:
                        prod = products[0]
                        price = prod.get('salePriceU') or prod.get('priceU', 0)
                        old_price = prod.get('priceU', 0)
                        price = price // 100 if price else 0
                        old_price = old_price // 100 if old_price else 0
                except:
                    pass

        # Если не нашли, ищем в HTML
        if price == 0:
            final_price_elem = soup.find('span', class_='final-price')
            if not final_price_elem:
                final_price_elem = soup.find('span', class_='price-block__final-price')
            if final_price_elem:
                price_text = final_price_elem.text.replace('₽', '').strip()
                price = int(re.sub(r'\D', '', price_text)) if price_text else 0

            old_price_elem = soup.find('del', class_='price-block__old-price')
            if old_price_elem:
                old_text = old_price_elem.text.replace('₽', '').strip()
                old_price = int(re.sub(r'\D', '', old_text)) if old_text else None

        return {
            'art': art,
            'title': title,
            'price': price,
            'old_price': old_price if old_price and old_price > price else None,
            'url': url
        }
    except Exception as e:
        print(f"❌ Ошибка при парсинге {art}: {e}")
        return None

# ------------------ Сохранение и получение вишлистов ------------------
def save_wishlist_to_db(wish_id, arts_list):
    books_data = []
    total = len(arts_list)
    for idx, art in enumerate(arts_list, 1):
        print(f"⏳ Загружаю {idx}/{total}: артикул {art}")
        data = fetch_book_data(art)
        if data:
            books_data.append(data)
        else:
            books_data.append({
                'art': art,
                'title': f'Книга {art}',
                'price': 0,
                'old_price': None,
                'url': f'https://www.wildberries.ru/catalog/{art}/detail.aspx'
            })
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO wishlists (id, arts, books_data) VALUES (?, ?, ?)',
            (wish_id, ','.join(arts_list), json.dumps(books_data, ensure_ascii=False))
        )
        db.commit()
    print(f"✅ Вишлист {wish_id} сохранён с {len(books_data)} книгами")
    return books_data

def get_wishlist_from_db(wish_id):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT books_data FROM wishlists WHERE id = ?', (wish_id,))
        row = cursor.fetchone()
        if row and row['books_data']:
            return json.loads(row['books_data'])
        return None

# ------------------ Вспомогательные функции ------------------
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

# ------------------ Маршруты ------------------
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
            books_data = save_wishlist_to_db(wish_id, arts_list)
            saved_url = url_for('show_wishlist', wish_id=wish_id, _external=True)
            return render_template_string(INDEX_TEMPLATE, books=books_data, saved_url=saved_url, request=request)
        else:
            books_data = []
            total = len(arts_list)
            for idx, art in enumerate(arts_list, 1):
                print(f"⏳ Загружаю {idx}/{total}: артикул {art}")
                data = fetch_book_data(art)
                if data:
                    vol, part = get_vol_part(art)
                    data['vol'] = vol
                    data['part'] = part
                    books_data.append(data)
                else:
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
        return "Вишлист не найден. Возможно, он был удалён или ещё не создан.", 404
    
    for book in books_data:
        vol, part = get_vol_part(book['art'])
        book['vol'] = vol
        book['part'] = part
    return render_template_string(INDEX_TEMPLATE, books=books_data)

# ------------------ Запуск ------------------
if __name__ == '__main__':
    with app.app_context():
        init_db()
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM wishlists')
        count = cursor.fetchone()['count']
        print(f"📊 В БД находится {count} сохранённых вишлистов")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)