import os
import re
import hashlib
from flask import Flask, render_template_string, request, url_for

app = Flask(__name__)

# Для продакшена лучше использовать базу данных,
# но для простоты оставим в памяти (на Render всё равно хранится временно)
wishlists = {}

# База данных книг (названия из вашего списка)
BOOKS_DB = {
    '254490346': 'Боги, шаманы и призраки Кореи',
    '195850940': 'Жирандоль',
    '304313602': 'Мифы Центральной и Южной Америки',
    '435821694': 'Легенды и мифы Древней Греции',
    '551580533': 'Герои и их враги в русской мифологии',
    '186860075': 'Корейские мифы',
    '770963389': 'Йокларга теләмәгән бурсык малае',
    '242058030': 'Мифы Румынии',
    '347392021': 'Вампирский клуб вязания',
    '232764065': 'Мифы Китая',
    '387609762': 'Даха Тараторина. Крапива',
    '202286859': 'Смешарики. История культовой Вселенной',
    '315112696': 'Каштанка и другие рассказы',
    '196720398': 'Кельтские мифы',
    '188272409': 'Сердцецветы для охотницы',
    '668447511': 'Дом чудной на улице Лесной',
    '106067824': 'Оранжерея на краю света',
    '119442051': 'Гипотеза любви',
    '289470719': 'Волшебный магазин Токкэби',
    '768311101': 'Три мушкетера. Том 2',
    '323295243': 'Пожиратель душ в Оксфорде',
    '2291984': 'Повелитель мух',
    '432559728': 'Арабские мифы',
    '710243293': 'Любовь под омелой',
    '323294822': 'Убийство в чайной "Бузина"',
    '696125761': 'Змеелов. Гадючий остров',
    '307749445': 'Мифы Тибета',
    '363113220': 'Буддийские мифы',
    '395615966': 'Казахские мифы',
    '650030182': 'Замурчательное фэнтези',
    '248787055': 'Мифы Русского Севера, Сибири и Дальнего Востока',
    '271183099': 'Сказы',
    '475646180': 'Ловец кошмаров',
    '756316149': 'Медленной шлюпкой в Китай',
    '378773065': 'Путешествие к центру Земли',
    '496211210': 'Служба устранения магических конфузов',
    '307749496': 'Мифы о сотворении мира и конце света',
    '44883920': 'Тун. Лето в розовом городе',
    '535473897': 'Лавка сладостей на Сумеречной аллее',
    '451587010': 'Турецкие мифы',
    '525815547': 'Русская готика',
    '624737741': 'Татарский язык без репетитора',
    '196130396': 'Монгольские мифы',
    '629049401': 'Астра. Омнибус',
    '717360130': 'КОМПЛЕКТ из 3 книг Пощады, маэстрина!',
    '456386460': 'Мифы западных славян',
    '552800731': 'Мифология Средиземья',
    '279824145': 'Мифы народов Кавказа',
    '642837335': 'Три мушкетера. Том 1',
    '367385895': 'Лавка сновидений Юнсыль',
    '656756127': 'Ничья на карусели',
    '146178904': 'Русалки и водяные',
    '217366123': 'Мифы Индии',
    '404028350': 'От первого лица',
    '292880046': 'Комплект книг 48 минут. Осколки + Пепел',
    '615911657': 'Узорчатая парча',
    '588552439': 'Рождество в Голливуде',
    '303705185': 'Магазинчик времени. Башня воспоминаний',
    '507852458': 'Астра. Омнибус',
    '343261963': 'Мифы Австралии, Новой Зеландии и Полинезии',
    '246292082': 'Книжный в сердце Парижа',
    '215129859': 'Логика. Упражнения по логике',
    '22272588': 'Шоколадная лавка в Париже',
    '628001708': 'Струны волшебства',
    '544877544': 'Большие подарочные сборники. Враки. Йага и Аир',
    '387580771': 'Когда солнце взойдет на западе',
    '88806167': 'Драконы обожают принцесс',
    '551581005': 'Магия народов мира',
    '588745943': 'Анна Ахматова. Перчатка с левой руки',
    '170219341': 'Славянские мифы',
    '499260436': 'Цитадель',
    '165150869': 'Последняя из рода Мун',
    '366442174': 'Танцовщица',
    '539198750': 'Год крысы',
    '275463847': 'Даха Тараторина. Аир. Хозяин болота',
    '497956695': 'Мифы о животных и мифических существах',
    '395616560': 'Германские мифы',
    '297709817': 'Отель потерянных душ. Госпожа управляющая',
    '262323634': 'Проделки бога лета',
    '316619592': 'Мифы Кореи. Раскрась легенду',
    '239009176': 'Боги, духи и ёкаи японской мифологии',
    '699506848': 'Кото-математика',
    '264612479': 'Мифы Карелии и Ингерманландии',
    '177700538': 'Японские мифы',
    '146500006': 'Булгаков. Жизнь господина де Мольера',
    '52447320': 'Ведьмак, все романы цикла в одном томе',
    '505459035': 'Странная история доктора Джекила и мистера Хайда',
    '175486361': 'Приморская академия',
    '311648108': 'Мифы шумеров',
    '689408579': 'Мифы времен года',
    '220050625': 'Химеры среди нас',
    '274287384': 'Книжная деревушка в Шотландии',
    '449583729': 'Что я узнала в книжном "Кобаяси"',
    '92326906': 'Встретимся в кафе "Капкейк"',
    '234935571': 'Профессия ведьма. Том 1',
    '333495441': 'О нефрите и драконах',
    '262013394': 'Демон. Вечные истории',
    '269373581': 'Алая Топь',
    '237272123': 'Затерянный книжный',
    '439785703': 'ПОПКУЛЬТ 2000',
    '349604316': 'Чудовище во мраке',
    '322922296': 'Волчица, покорившая хаос',
    '310112075': 'Космоолухи Рядом. Комплект из 2 книг',
    '668241663': 'В Рождество у каждого свой секрет',
    '170218636': 'Скандинавские мифы',
    '247408157': 'Космоолухи (трилогия)',
    '256688440': 'Космоолухи. Киберканикулы',
    '365134388': 'Затерянный мир',
    '237122417': 'Даха Тараторина. Йага',
    '262323929': 'Дочь Горгоны',
    '263007703': 'Благие знамения',
    '525031044': 'Магазинчик времени. Башня воспоминаний',
    '399565246': 'Чернильные души',
    '776458268': 'Дети из камеры хранения',
    '714760285': 'Мужчины без женщин',
    '178345589': 'Две зимы',
    '599315404': 'Рыжее братство',
    '289470903': 'Дни в книжном Морисаки',
    '400639743': 'Когда засияет Журавль',
    '714936485': 'Мифы о драконах',
    '568470639': 'Народные промыслы на Руси',
    '439946117': 'Благие знамения',
    '263006856': 'Благие знамения',
    '502631241': 'Эра Думер Жрец со щитом',
    '325685784': 'Отель потерянных душ. Госпожа проводница эфира',
    '172564381': 'Властелин Колец трилогия',
    '711908464': 'Любовь под омелой',
    '711681905': 'Сердца трех',
    '178350525': 'Египетские мифы',
    '74516131': 'Булгаков Мастер и Маргарита',
    '486434480': 'Пушистое счастье',
    '215144314': 'Мифы Урала и Поволжья',
    '658228631': 'Смерть, отбор и котики',
    '356112147': 'Плохие девчонки Древней Греции',
    '545000878': 'Крысявки 2.0',
    '105029241': 'Гипотеза любви',
    '701597224': 'Книги романы. Любовь и вереск',
    '578779011': 'Кафе "Пряная тыква"',
    '589663543': 'Вечера на хуторе близ Диканьки',
    '724664931': 'Кошачий глаз в волшебный час',
    '501368603': 'Сказки народов Поволжья',
    '662891987': 'Шах и мат',
    '363334390': 'Персидские мифы',
    '515494099': 'Одиночка. Книги 1-3',
    '189317929': 'Шах и мат',
    '261060016': 'Шалости богини зимы'
}

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
        .book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; margin-top: 30px; }
        .book-card { text-align: center; padding: 10px; border: 1px solid #e2d5c0; border-radius: 8px; background: #fffcf5; }
        .book-image { width: 120px; height: 160px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9; }
        .book-title { margin: 8px 0; font-weight: bold; font-size: 13px; color: #2c1e12; min-height: 35px; overflow: hidden; }
        .book-link { display: inline-block; padding: 6px 12px; background: #f2e8d8; border-radius: 20px; text-decoration: none; color: #3e2e1f; font-size: 13px; }
        .book-link:hover { background: #b99e7c; color: white; }
        .stats { margin-top: 20px; color: #666; }
        .share-link { margin-top: 20px; padding: 15px; background: #f2e8d8; border-radius: 8px; word-break: break-all; }
        .share-link input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        @media (max-width: 600px) {
            .book-grid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
            .book-image { width: 100px; height: 140px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Книжный вишлист</h1>
        
        <form method="post" id="mainForm">
            <textarea name="links" rows="8" placeholder="Вставьте ссылки на Wildberries (каждая с новой строки)">{{ request.form.get('links', '') }}</textarea>
            <br>
            <button type="submit" name="action" value="show">📋 Показать книги</button>
            <button type="submit" name="action" value="save">💾 Сохранить и получить ссылку</button>
        </form>

        {% if saved_url %}
        <div class="share-link">
            <h3>🔗 Ссылка на ваш вишлист:</h3>
            <input type="text" value="{{ saved_url }}" readonly onclick="this.select()">
            <p>Скопируйте и отправьте друзьям!</p>
        </div>
        {% endif %}

        {% if books %}
        <div class="book-grid">
            {% for book in books %}
            <div class="book-card">
                <img class="book-image" 
                     src="https://basket-01.wbbasket.ru/vol{{ book.vol }}/part{{ book.part }}/{{ book.art }}/images/big/1.webp"
                     onerror="loadImage(this, '{{ book.vol }}', '{{ book.part }}', '{{ book.art }}')"
                     alt="{{ book.title }}">
                <div class="book-title">{{ book.title }}</div>
                <a class="book-link" href="{{ book.url }}" target="_blank">📖 Открыть</a>
            </div>
            {% endfor %}
        </div>
        <div class="stats">Найдено книг: {{ books|length }}</div>
        {% endif %}
    </div>

    <script>
    function loadImage(img, vol, part, art, attempt = 1) {
        // Перебираем basket от 01 до 50
        if (attempt > 50) {
            // Если ничего не помогло, пробуем старый формат
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
            // Пробуем следующий basket
            loadImage(img, vol, part, art, attempt + 1);
        };
    }
    </script>
</body>
</html>
'''

def extract_articul(link):
    """Извлекает артикул из ссылки"""
    match = re.search(r'catalog/(\d+)', link)
    return match.group(1) if match else None

def get_vol_part(art):
    """Вычисляет vol и part по реальной структуре Wildberries"""
    art = str(art)
    vol = art[:4]      # первые 4 цифры
    part = art[:6]     # первые 6 цифр
    return vol, part

def generate_hash(arts):
    """Создаёт уникальный хеш для вишлиста"""
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
        
        books = []
        seen_arts = set()
        for link in links:
            art = extract_articul(link)
            if art and art not in seen_arts:
                seen_arts.add(art)
                vol, part = get_vol_part(art)
                title = BOOKS_DB.get(art, f'Книга {art}')
                books.append({
                    'art': art,
                    'vol': vol,
                    'part': part,
                    'title': title,
                    'url': link
                })
        
        if action == 'save':
            wish_id = generate_hash([b['art'] for b in books])
            wishlists[wish_id] = books
            saved_url = url_for('show_wishlist', wish_id=wish_id, _external=True)
            return render_template_string(INDEX_TEMPLATE, books=books, saved_url=saved_url, request=request)
        else:
            return render_template_string(INDEX_TEMPLATE, books=books, request=request)
    
    return render_template_string(INDEX_TEMPLATE)

@app.route('/wishlist/<wish_id>')
def show_wishlist(wish_id):
    books = wishlists.get(wish_id)
    if books is None:
        return "Вишлист не найден", 404
    return render_template_string(INDEX_TEMPLATE, books=books)

if __name__ == '__main__':
    # Для локального запуска и для хостинга
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
