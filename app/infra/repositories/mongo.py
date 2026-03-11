from abc import ABC
from dataclasses import dataclass
from typing import Iterable

from motor.core import AgnosticClient

from app.domain.entities.likes import LikesEntity
from app.domain.entities.users import UserEntity
from app.domain.values.users import AboutText
from app.infra.repositories.base import (
    BaseDislikesRepository,
    BaseLikesRepository,
    BaseUsersRepository,
)
from app.infra.repositories.converters import (
    convert_like_entity_to_document,
    convert_user_document_to_entity,
    convert_user_entity_to_document,
)
from app.infra.repositories.filters.users import GetAllUsersFilters


@dataclass
class BaseMongoDBRepository(ABC):
    mongo_db_client: AgnosticClient
    mongo_db_name: str
    mongo_db_collection_name: str

    @property
    def _collection(self):
        return self.mongo_db_client[self.mongo_db_name][self.mongo_db_collection_name]


_CITY_NEIGHBORS: dict[str, list[str]] = {
    # ── Москва и область ──────────────────────────────────────────────────────
    "Москва": ["Химки", "Балашиха", "Подольск", "Мытищи", "Люберцы", "Королёв", "Одинцово", "Видное",
               "Серпухов", "Коломна", "Домодедово", "Электросталь", "Ногинск", "Щёлково", "Клин",
               "Дмитров", "Пушкино", "Железнодорожный", "Красногорск", "Жуковский"],
    "Химки": ["Москва", "Красногорск", "Зеленоград", "Долгопрудный"],
    "Балашиха": ["Москва", "Электросталь", "Ногинск", "Железнодорожный", "Люберцы"],
    "Подольск": ["Москва", "Серпухов", "Домодедово", "Видное"],
    "Мытищи": ["Москва", "Пушкино", "Щёлково", "Королёв"],
    "Люберцы": ["Москва", "Балашиха", "Железнодорожный", "Жуковский"],
    "Королёв": ["Москва", "Мытищи", "Щёлково", "Пушкино"],
    "Одинцово": ["Москва", "Красногорск", "Звенигород", "Истра"],
    "Серпухов": ["Москва", "Подольск", "Коломна"],
    "Коломна": ["Москва", "Серпухов", "Рязань"],
    "Жуковский": ["Москва", "Люберцы", "Раменское"],
    "Зеленоград": ["Москва", "Химки", "Клин"],
    "Электросталь": ["Балашиха", "Ногинск", "Москва"],
    "Ногинск": ["Электросталь", "Балашиха", "Щёлково"],
    "Щёлково": ["Мытищи", "Королёв", "Ногинск", "Пушкино"],
    "Пушкино": ["Мытищи", "Щёлково", "Королёв", "Сергиев Посад"],
    "Сергиев Посад": ["Пушкино", "Дмитров", "Александров"],
    "Дмитров": ["Москва", "Сергиев Посад", "Клин"],
    "Клин": ["Москва", "Зеленоград", "Дмитров", "Тверь"],
    "Красногорск": ["Москва", "Химки", "Одинцово"],
    "Домодедово": ["Москва", "Подольск"],
    "Видное": ["Москва", "Подольск"],
    "Раменское": ["Жуковский", "Москва"],
    "Дубна": ["Дмитров", "Тверь"],

    # ── Санкт-Петербург и область ─────────────────────────────────────────────
    "Санкт-Петербург": ["Гатчина", "Пушкин", "Колпино", "Выборг", "Петергоф", "Сестрорецк",
                        "Красное Село", "Тосно", "Всеволожск", "Кронштадт", "Сосновый Бор"],
    "Гатчина": ["Санкт-Петербург", "Луга", "Кингисепп"],
    "Выборг": ["Санкт-Петербург", "Приозерск"],
    "Тосно": ["Санкт-Петербург", "Гатчина", "Кириши"],
    "Всеволожск": ["Санкт-Петербург", "Кировск", "Шлиссельбург"],
    "Кировск": ["Всеволожск", "Шлиссельбург", "Санкт-Петербург"],
    "Луга": ["Гатчина", "Псков", "Санкт-Петербург"],
    "Сосновый Бор": ["Санкт-Петербург", "Кингисепп"],
    "Кингисепп": ["Сосновый Бор", "Гатчина", "Нарва"],
    "Тихвин": ["Санкт-Петербург", "Кириши", "Череповец"],
    "Петрозаводск": ["Санкт-Петербург", "Сортавала", "Кондопога"],

    # ── Северо-Запад ──────────────────────────────────────────────────────────
    "Архангельск": ["Северодвинск", "Новодвинск", "Котлас"],
    "Северодвинск": ["Архангельск", "Новодвинск"],
    "Котлас": ["Архангельск", "Сыктывкар"],
    "Мурманск": ["Апатиты", "Кандалакша", "Североморск"],
    "Апатиты": ["Мурманск", "Кировск", "Кандалакша"],
    "Кандалакша": ["Мурманск", "Апатиты"],
    "Калининград": ["Балтийск", "Черняховск", "Советск", "Гусев"],
    "Балтийск": ["Калининград", "Светлогорск"],
    "Черняховск": ["Калининград", "Гусев"],
    "Псков": ["Великий Новгород", "Луга", "Санкт-Петербург"],
    "Великий Новгород": ["Псков", "Санкт-Петербург", "Тверь", "Боровичи"],
    "Вологда": ["Череповец", "Ярославль", "Кострома"],
    "Череповец": ["Вологда", "Тихвин", "Ярославль"],
    "Петрозаводск": ["Санкт-Петербург", "Медвежьегорск"],

    # ── Центральная Россия ────────────────────────────────────────────────────
    "Ярославль": ["Рыбинск", "Кострома", "Иваново", "Вологда", "Тверь"],
    "Рыбинск": ["Ярославль", "Вологда"],
    "Кострома": ["Ярославль", "Иваново", "Нижний Новгород"],
    "Иваново": ["Ярославль", "Кострома", "Владимир", "Нижний Новгород"],
    "Владимир": ["Иваново", "Суздаль", "Ковров", "Муром", "Нижний Новгород"],
    "Ковров": ["Владимир", "Иваново"],
    "Муром": ["Владимир", "Арзамас"],
    "Тверь": ["Москва", "Клин", "Ржев", "Великий Новгород", "Ярославль"],
    "Ржев": ["Тверь", "Смоленск"],
    "Смоленск": ["Рославль", "Вязьма", "Ржев", "Брянск"],
    "Вязьма": ["Смоленск", "Москва"],
    "Рязань": ["Коломна", "Москва", "Тамбов", "Пенза", "Тула"],
    "Тула": ["Москва", "Рязань", "Новомосковск", "Орёл", "Калуга"],
    "Новомосковск": ["Тула", "Рязань"],
    "Калуга": ["Москва", "Тула", "Обнинск", "Брянск"],
    "Обнинск": ["Калуга", "Москва"],
    "Орёл": ["Тула", "Курск", "Брянск", "Липецк"],
    "Брянск": ["Смоленск", "Орёл", "Калуга", "Рославль"],
    "Курск": ["Орёл", "Белгород", "Воронеж", "Брянск"],
    "Белгород": ["Курск", "Старый Оскол", "Губкин", "Воронеж"],
    "Старый Оскол": ["Белгород", "Губкин", "Воронеж"],
    "Губкин": ["Старый Оскол", "Белгород"],
    "Воронеж": ["Белгород", "Курск", "Липецк", "Тамбов", "Борисоглебск"],
    "Липецк": ["Воронеж", "Орёл", "Тамбов", "Елец"],
    "Елец": ["Липецк", "Орёл"],
    "Тамбов": ["Воронеж", "Липецк", "Рязань", "Пенза", "Саратов"],
    "Пенза": ["Тамбов", "Саратов", "Ульяновск", "Рязань"],
    "Саратов": ["Энгельс", "Балаково", "Пенза", "Тамбов", "Вольск", "Волгоград"],
    "Энгельс": ["Саратов", "Балаково"],
    "Балаково": ["Саратов", "Энгельс", "Вольск"],
    "Вольск": ["Саратов", "Балаково"],
    "Орёл": ["Тула", "Курск", "Брянск", "Липецк"],

    # ── Поволжье ──────────────────────────────────────────────────────────────
    "Нижний Новгород": ["Дзержинск", "Арзамас", "Кстово", "Бор", "Иваново", "Чебоксары", "Кострома"],
    "Дзержинск": ["Нижний Новгород", "Арзамас", "Кстово"],
    "Арзамас": ["Нижний Новгород", "Муром", "Саранск"],
    "Кстово": ["Нижний Новгород", "Дзержинск"],
    "Бор": ["Нижний Новгород"],
    "Чебоксары": ["Новочебоксарск", "Казань", "Нижний Новгород", "Йошкар-Ола"],
    "Новочебоксарск": ["Чебоксары", "Казань"],
    "Йошкар-Ола": ["Чебоксары", "Казань", "Киров"],
    "Казань": ["Набережные Челны", "Нижнекамск", "Чебоксары", "Ульяновск", "Самара", "Йошкар-Ола"],
    "Набережные Челны": ["Казань", "Нижнекамск", "Альметьевск", "Елабуга"],
    "Нижнекамск": ["Набережные Челны", "Казань", "Елабуга"],
    "Альметьевск": ["Набережные Челны", "Казань", "Бугульма"],
    "Елабуга": ["Набережные Челны", "Нижнекамск"],
    "Бугульма": ["Альметьевск", "Уфа"],
    "Ульяновск": ["Казань", "Самара", "Пенза", "Сызрань", "Димитровград"],
    "Димитровград": ["Ульяновск", "Тольятти"],
    "Самара": ["Тольятти", "Сызрань", "Новокуйбышевск", "Кинель", "Казань", "Ульяновск"],
    "Тольятти": ["Самара", "Сызрань", "Жигулёвск", "Ульяновск", "Димитровград"],
    "Сызрань": ["Самара", "Тольятти", "Ульяновск"],
    "Новокуйбышевск": ["Самара", "Тольятти"],
    "Жигулёвск": ["Тольятти", "Самара"],
    "Саранск": ["Арзамас", "Пенза", "Рузаевка"],

    # ── Урал ──────────────────────────────────────────────────────────────────
    "Уфа": ["Стерлитамак", "Салават", "Нефтекамск", "Октябрьский", "Ишимбай", "Оренбург", "Бугульма"],
    "Стерлитамак": ["Уфа", "Салават", "Ишимбай", "Мелеуз"],
    "Салават": ["Стерлитамак", "Уфа", "Ишимбай"],
    "Нефтекамск": ["Уфа", "Октябрьский"],
    "Октябрьский": ["Уфа", "Нефтекамск"],
    "Ишимбай": ["Стерлитамак", "Салават", "Уфа"],
    "Мелеуз": ["Стерлитамак", "Уфа"],
    "Оренбург": ["Уфа", "Орск", "Соль-Илецк"],
    "Орск": ["Оренбург", "Новотроицк"],
    "Новотроицк": ["Орск", "Оренбург"],
    "Пермь": ["Березники", "Соликамск", "Чайковский", "Кунгур", "Лысьва", "Ижевск"],
    "Березники": ["Пермь", "Соликамск"],
    "Соликамск": ["Березники", "Пермь"],
    "Чайковский": ["Пермь", "Ижевск"],
    "Кунгур": ["Пермь", "Екатеринбург"],
    "Лысьва": ["Пермь", "Чусовой"],
    "Ижевск": ["Пермь", "Сарапул", "Воткинск", "Чайковский", "Киров"],
    "Сарапул": ["Ижевск", "Воткинск"],
    "Воткинск": ["Ижевск", "Сарапул"],
    "Екатеринбург": ["Нижний Тагил", "Первоуральск", "Берёзовский", "Каменск-Уральский",
                     "Асбест", "Ревда", "Тюмень", "Челябинск", "Серов"],
    "Нижний Тагил": ["Екатеринбург", "Серов", "Нижняя Салда"],
    "Первоуральск": ["Екатеринбург", "Ревда"],
    "Берёзовский": ["Екатеринбург", "Асбест"],
    "Каменск-Уральский": ["Екатеринбург", "Асбест", "Курган"],
    "Асбест": ["Екатеринбург", "Берёзовский", "Каменск-Уральский"],
    "Ревда": ["Первоуральск", "Екатеринбург"],
    "Серов": ["Нижний Тагил", "Екатеринбург"],
    "Челябинск": ["Магнитогорск", "Миасс", "Златоуст", "Копейск", "Коркино", "Екатеринбург", "Уфа", "Курган"],
    "Магнитогорск": ["Челябинск", "Белорецк"],
    "Миасс": ["Челябинск", "Златоуст"],
    "Златоуст": ["Челябинск", "Миасс"],
    "Копейск": ["Челябинск"],
    "Коркино": ["Челябинск", "Копейск"],
    "Белорецк": ["Магнитогорск", "Уфа"],
    "Курган": ["Челябинск", "Тюмень", "Шадринск", "Каменск-Уральский"],
    "Шадринск": ["Курган", "Тюмень"],
    "Тюмень": ["Омск", "Екатеринбург", "Тобольск", "Сургут", "Ишим", "Курган"],
    "Тобольск": ["Тюмень", "Ханты-Мансийск"],
    "Ишим": ["Тюмень", "Омск"],

    # ── Западная Сибирь / ХМАО / ЯНАО ────────────────────────────────────────
    "Сургут": ["Нижневартовск", "Тюмень", "Ханты-Мансийск", "Нефтеюганск"],
    "Нижневартовск": ["Сургут", "Нефтеюганск"],
    "Ханты-Мансийск": ["Сургут", "Тобольск"],
    "Нефтеюганск": ["Сургут", "Нижневартовск"],
    "Новый Уренгой": ["Ноябрьск", "Надым", "Салехард"],
    "Ноябрьск": ["Новый Уренгой", "Муравленко"],
    "Надым": ["Новый Уренгой", "Салехард"],
    "Салехард": ["Новый Уренгой", "Надым", "Лабытнанги"],
    "Нижневартовск": ["Сургут", "Нефтеюганск"],
    "Когалым": ["Сургут", "Нефтеюганск"],

    # ── Новосибирск и Западная Сибирь ────────────────────────────────────────
    "Новосибирск": ["Бердск", "Искитим", "Обь", "Кемерово", "Томск", "Барнаул", "Омск"],
    "Бердск": ["Новосибирск", "Искитим"],
    "Искитим": ["Новосибирск", "Бердск"],
    "Обь": ["Новосибирск"],
    "Омск": ["Новосибирск", "Тюмень", "Томск", "Барнаул", "Ишим", "Тара"],
    "Тара": ["Омск"],
    "Томск": ["Новосибирск", "Омск", "Кемерово", "Северск"],
    "Северск": ["Томск"],
    "Кемерово": ["Новосибирск", "Томск", "Новокузнецк", "Прокопьевск", "Белово", "Ленинск-Кузнецкий"],
    "Новокузнецк": ["Кемерово", "Прокопьевск", "Белово", "Осинники", "Киселёвск"],
    "Прокопьевск": ["Кемерово", "Новокузнецк", "Киселёвск"],
    "Белово": ["Кемерово", "Новокузнецк", "Ленинск-Кузнецкий"],
    "Ленинск-Кузнецкий": ["Кемерово", "Белово"],
    "Киселёвск": ["Прокопьевск", "Новокузнецк"],
    "Осинники": ["Новокузнецк"],
    "Барнаул": ["Новосибирск", "Бийск", "Рубцовск", "Заринск", "Новоалтайск"],
    "Бийск": ["Барнаул", "Горно-Алтайск"],
    "Горно-Алтайск": ["Бийск", "Барнаул"],
    "Рубцовск": ["Барнаул"],
    "Новоалтайск": ["Барнаул", "Бийск"],

    # ── Восточная Сибирь ──────────────────────────────────────────────────────
    "Красноярск": ["Ачинск", "Железногорск", "Канск", "Норильск", "Иркутск", "Новосибирск", "Абакан"],
    "Ачинск": ["Красноярск", "Канск"],
    "Железногорск": ["Красноярск"],
    "Канск": ["Красноярск", "Ачинск"],
    "Норильск": ["Красноярск"],
    "Абакан": ["Красноярск", "Черногорск", "Минусинск"],
    "Черногорск": ["Абакан", "Красноярск"],
    "Минусинск": ["Абакан", "Красноярск"],
    "Иркутск": ["Ангарск", "Шелехов", "Братск", "Красноярск", "Улан-Удэ"],
    "Ангарск": ["Иркутск", "Шелехов"],
    "Шелехов": ["Иркутск", "Ангарск"],
    "Братск": ["Иркутск", "Усть-Илимск"],
    "Усть-Илимск": ["Братск", "Иркутск"],
    "Улан-Удэ": ["Иркутск", "Северобайкальск"],
    "Северобайкальск": ["Улан-Удэ"],
    "Чита": ["Улан-Удэ", "Борзя", "Чернышевск"],
    "Борзя": ["Чита"],

    # ── Дальний Восток ────────────────────────────────────────────────────────
    "Хабаровск": ["Комсомольск-на-Амуре", "Биробиджан", "Амурск", "Николаевск-на-Амуре"],
    "Комсомольск-на-Амуре": ["Хабаровск", "Амурск"],
    "Биробиджан": ["Хабаровск"],
    "Амурск": ["Комсомольск-на-Амуре", "Хабаровск"],
    "Владивосток": ["Уссурийск", "Находка", "Артём", "Партизанск"],
    "Уссурийск": ["Владивосток", "Артём"],
    "Находка": ["Владивосток", "Партизанск"],
    "Артём": ["Владивосток", "Уссурийск"],
    "Партизанск": ["Находка", "Владивосток"],
    "Благовещенск": ["Свободный", "Белогорск"],
    "Свободный": ["Благовещенск"],
    "Белогорск": ["Благовещенск"],
    "Якутск": ["Нерюнгри", "Мирный"],
    "Нерюнгри": ["Якутск", "Алдан"],
    "Мирный": ["Якутск"],
    "Алдан": ["Нерюнгри", "Якутск"],
    "Магадан": ["Сусуман"],
    "Петропавловск-Камчатский": ["Елизово"],
    "Елизово": ["Петропавловск-Камчатский"],
    "Южно-Сахалинск": ["Корсаков", "Холмск"],
    "Корсаков": ["Южно-Сахалинск"],
    "Холмск": ["Южно-Сахалинск"],

    # ── Юг России / Северный Кавказ ───────────────────────────────────────────
    "Ростов-на-Дону": ["Батайск", "Новочеркасск", "Таганрог", "Аксай", "Шахты", "Новошахтинск",
                       "Азов", "Волгодонск", "Краснодар"],
    "Батайск": ["Ростов-на-Дону", "Азов"],
    "Новочеркасск": ["Ростов-на-Дону", "Шахты"],
    "Таганрог": ["Ростов-на-Дону", "Азов"],
    "Аксай": ["Ростов-на-Дону"],
    "Шахты": ["Ростов-на-Дону", "Новочеркасск", "Новошахтинск"],
    "Новошахтинск": ["Шахты", "Ростов-на-Дону"],
    "Азов": ["Ростов-на-Дону", "Батайск", "Таганрог"],
    "Волгодонск": ["Ростов-на-Дону", "Цимлянск"],
    "Волгоград": ["Волжский", "Камышин", "Михайловка", "Фролово", "Ростов-на-Дону", "Саратов", "Астрахань"],
    "Волжский": ["Волгоград", "Камышин"],
    "Камышин": ["Волгоград", "Волжский", "Балаково"],
    "Михайловка": ["Волгоград"],
    "Астрахань": ["Волгоград", "Элиста", "Ахтубинск"],
    "Элиста": ["Астрахань", "Волгоград", "Ставрополь"],
    "Ахтубинск": ["Астрахань"],
    "Краснодар": ["Новороссийск", "Анапа", "Армавир", "Сочи", "Ставрополь", "Майкоп", "Геленджик",
                  "Тихорецк", "Кропоткин", "Ростов-на-Дону"],
    "Новороссийск": ["Краснодар", "Анапа", "Геленджик"],
    "Анапа": ["Краснодар", "Новороссийск", "Геленджик"],
    "Геленджик": ["Анапа", "Новороссийск", "Краснодар"],
    "Армавир": ["Краснодар", "Ставрополь", "Невинномысск"],
    "Сочи": ["Краснодар", "Новороссийск", "Туапсе", "Адлер"],
    "Туапсе": ["Сочи", "Новороссийск", "Краснодар"],
    "Адлер": ["Сочи"],
    "Майкоп": ["Краснодар", "Армавир"],
    "Тихорецк": ["Краснодар", "Армавир"],
    "Кропоткин": ["Краснодар", "Армавир"],
    "Ставрополь": ["Краснодар", "Пятигорск", "Невинномысск", "Армавир", "Элиста"],
    "Невинномысск": ["Ставрополь", "Армавир", "Пятигорск"],
    "Пятигорск": ["Ставрополь", "Нальчик", "Черкесск", "Кисловодск", "Ессентуки", "Минеральные Воды"],
    "Кисловодск": ["Пятигорск", "Ессентуки", "Нальчик"],
    "Ессентуки": ["Пятигорск", "Кисловодск", "Минеральные Воды"],
    "Минеральные Воды": ["Пятигорск", "Ессентуки", "Невинномысск"],
    "Черкесск": ["Пятигорск", "Нальчик", "Карачаевск"],
    "Карачаевск": ["Черкесск"],
    "Нальчик": ["Пятигорск", "Черкесск", "Владикавказ", "Прохладный"],
    "Прохладный": ["Нальчик", "Моздок"],
    "Владикавказ": ["Нальчик", "Грозный", "Беслан", "Моздок"],
    "Беслан": ["Владикавказ", "Нальчик"],
    "Моздок": ["Прохладный", "Владикавказ"],
    "Грозный": ["Владикавказ", "Гудермес", "Аргун", "Назрань", "Хасавюрт"],
    "Гудермес": ["Грозный", "Хасавюрт"],
    "Аргун": ["Грозный"],
    "Назрань": ["Грозный", "Магас", "Малгобек"],
    "Магас": ["Назрань"],
    "Малгобек": ["Назрань", "Грозный"],
    "Махачкала": ["Каспийск", "Хасавюрт", "Дербент", "Буйнакск", "Избербаш", "Кизляр", "Кизилюрт"],
    "Каспийск": ["Махачкала", "Буйнакск"],
    "Хасавюрт": ["Махачкала", "Гудермес", "Кизляр", "Кизилюрт"],
    "Дербент": ["Махачкала", "Избербаш"],
    "Буйнакск": ["Махачкала", "Каспийск"],
    "Избербаш": ["Дербент", "Махачкала"],
    "Кизляр": ["Хасавюрт", "Махачкала"],
    "Кизилюрт": ["Махачкала", "Хасавюрт"],

    # ── Крым ──────────────────────────────────────────────────────────────────
    "Симферополь": ["Севастополь", "Ялта", "Керчь", "Евпатория", "Феодосия", "Джанкой"],
    "Севастополь": ["Симферополь", "Ялта", "Балаклава"],
    "Ялта": ["Симферополь", "Севастополь", "Алушта"],
    "Алушта": ["Ялта", "Симферополь"],
    "Евпатория": ["Симферополь", "Саки"],
    "Феодосия": ["Симферополь", "Керчь"],
    "Керчь": ["Феодосия", "Симферополь"],
    "Джанкой": ["Симферополь"],
    "Саки": ["Евпатория"],

    # ── Кировская / Нижегородская зоны ───────────────────────────────────────
    "Киров": ["Кирово-Чепецк", "Котельнич", "Йошкар-Ола", "Ижевск", "Пермь"],
    "Кирово-Чепецк": ["Киров"],
    "Котельнич": ["Киров"],

    # ── Сыктывкар / Коми ──────────────────────────────────────────────────────
    "Сыктывкар": ["Ухта", "Котлас", "Воркута"],
    "Ухта": ["Сыктывкар", "Воркута"],
    "Воркута": ["Сыктывкар", "Ухта"],
}


@dataclass
class MongoDBUserRepository(BaseUsersRepository, BaseMongoDBRepository):
    async def get_user_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        user_document = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
        )

        if not user_document:
            return None

        return convert_user_document_to_entity(user_document=user_document)

    async def check_user_is_active(self, telegram_id: int) -> bool:
        user_document = await self._collection.find_one(
            filter={"telegram_id": telegram_id, "is_active": True},
        )

        return bool(user_document)

    async def update_user_info_after_register(self, telegram_id: int, data: dict):
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": data},
        )

    async def update_user_about(self, telegram_id: int, about: AboutText):
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": {"about": about.as_generic_type()}},
        )

    async def update_user_ai_fields(self, telegram_id: int, ai_fields: dict) -> None:
        """Обновляет AI-поля анкеты (search_text, ai_traits, ai_skills, ai_appearance)."""
        if not ai_fields:
            return
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": ai_fields},
        )

    async def create_user(self, user: UserEntity):
        await self._collection.insert_one(convert_user_entity_to_document(user))

    async def check_user_exist_by_telegram_id(self, telegram_id: int) -> bool:
        return bool(
            await self._collection.find_one(
                filter={"telegram_id": telegram_id},
            ),
        )

    async def get_all_user(
        self,
        filters: GetAllUsersFilters,
    ) -> tuple[Iterable[UserEntity], int]:
        cursor = self._collection.find().skip(filters.offset).limit(filters.limit)

        count = await self._collection.count_documents({})
        chats = [
            convert_user_document_to_entity(user_document=user_document)
            async for user_document in cursor
        ]

        return chats, count

    async def get_best_result_for_user(
        self, telegram_id: int, exclude_ids: list[int] | None = None
    ) -> Iterable[UserEntity]:
        """
        Возвращает ВСЕ подходящие анкеты противоположного пола,
        отсортированные по расстоянию от пользователя (Haversine, Python).
        Порядок: ближе → дальше → анкеты никогда не заканчиваются.
        Внутри одной дистанционной группы: boost → VIP → Premium → бесплатные.
        """
        from datetime import datetime, timezone
        from app.infra.repositories.cities import get_city_coords, haversine_km

        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []

        excluded = set(exclude_ids or [])
        excluded.add(telegram_id)
        now = datetime.now(timezone.utc)

        # ── Гендерный фильтр: СТРОГО противоположный пол ─────────────
        _ALL_MALE   = ["Man", "man", "Male", "male", "Мужской", "мужской", "м", "m"]
        _ALL_FEMALE = ["Female", "female", "Женский", "женский", "Woman", "woman", "ж", "f"]

        raw_gender = getattr(user, "gender", None)
        user_gender = ""
        if raw_gender is not None:
            user_gender = str(
                raw_gender.as_generic_type() if hasattr(raw_gender, "as_generic_type") else raw_gender
            ).strip().lower()

        gender_filter: dict | None = None
        if user_gender in ("man", "male", "мужской", "м", "m"):
            gender_filter = {"$in": _ALL_FEMALE}
        elif user_gender in ("female", "женский", "woman", "ж", "f"):
            gender_filter = {"$in": _ALL_MALE}

        # Без определённого пола — не показываем никого (не угадываем)
        if not gender_filter:
            return []

        # ── Базовый фильтр ───────────────────────────────────────────
        base: dict = {
            "telegram_id": {"$nin": list(excluded)},
            "is_banned":   {"$ne": True},
            "profile_hidden": {"$ne": True},
            "gender":      gender_filter,
            "$and": [
                {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
                {"$or": [
                    {"photos.0": {"$exists": True}},
                    {"photo": {"$nin": [None, ""]}},
                ]},
            ],
        }

        docs: list[dict] = []
        async for doc in self._collection.find(base):
            docs.append(doc)

        if not docs:
            return []

        # ── Координаты пользователя ───────────────────────────────────
        raw_city = getattr(user, "city", None)
        user_city = ""
        if raw_city is not None:
            user_city = str(
                raw_city.as_generic_type() if hasattr(raw_city, "as_generic_type") else raw_city
            ).strip()
        user_lat: float | None = None
        user_lon: float | None = None

        raw_lat = getattr(user, "lat", None)
        raw_lon = getattr(user, "lon", None)
        try:
            if raw_lat is not None and raw_lon is not None:
                user_lat = float(raw_lat)
                user_lon = float(raw_lon)
        except (TypeError, ValueError):
            pass

        if (user_lat is None or user_lon is None) and user_city:
            coords = get_city_coords(user_city)
            if coords:
                user_lat, user_lon = coords

        # ── Кэш координат кандидата ────────────────────────────────────
        _coord_cache: dict[str, tuple[float, float] | None] = {}

        def _candidate_coords(doc: dict) -> tuple[float, float] | None:
            try:
                d_lat = doc.get("lat")
                d_lon = doc.get("lon")
                if d_lat is not None and d_lon is not None:
                    return float(d_lat), float(d_lon)
            except (TypeError, ValueError):
                pass
            city = doc.get("city") or ""
            if city not in _coord_cache:
                _coord_cache[city] = get_city_coords(city)
            return _coord_cache[city]

        # ── Безопасное сравнение datetime (naive/aware) ────────────────
        def _is_future(dt) -> bool:
            if not dt:
                return False
            try:
                if getattr(dt, "tzinfo", None) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt > now
            except (TypeError, ValueError):
                return False

        # ── Ключ сортировки: 1) свой город 2) по расстоянию 3) подписка ─
        user_city_lower = user_city.lower() if user_city else ""

        def _sort_key(doc: dict) -> tuple:
            # 1) Свой город — всегда первые
            doc_city = (doc.get("city") or "").strip().lower()
            city_match = 0 if doc_city and user_city_lower and doc_city == user_city_lower else 1

            # 2) Расстояние в км
            dist = 999999.0
            if user_lat is not None and user_lon is not None:
                crd = _candidate_coords(doc)
                if crd:
                    try:
                        dist = haversine_km(user_lat, user_lon, crd[0], crd[1])
                    except Exception:
                        dist = 999999.0
            # Свой город без координат — считаем 0 км
            if city_match == 0 and dist > 100:
                dist = 0.0

            # 3) Приоритет подписки
            pt = doc.get("premium_type")
            pu = doc.get("premium_until")
            bu = doc.get("boost_until")
            if _is_future(bu):
                sub = 0
            elif pt == "vip" and _is_future(pu):
                sub = 1
            elif pt == "premium" and _is_future(pu):
                sub = 2
            else:
                sub = 3

            return (city_match, dist, sub)

        docs.sort(key=_sort_key)

        return [convert_user_document_to_entity(doc) for doc in docs]

    async def get_ai_matchmaking_candidates(
        self,
        telegram_id: int,
        target_gender: str,
        exclude_ids: list[int] | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        city: str | None = None,
        limit: int = 300,
    ) -> list[UserEntity]:
        """Кандидаты для AI-подбора: противоположный пол + опциональные age, city."""
        from app.infra.repositories.cities import get_city_coords, haversine_km

        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []

        excluded = set(exclude_ids or [])
        excluded.add(telegram_id)

        _ALL_MALE = ["Man", "man", "Male", "male", "Мужской", "мужской", "м", "m"]
        _ALL_FEMALE = ["Female", "female", "Женский", "женский", "Woman", "woman", "ж", "f"]
        gender_filter = {"$in": _ALL_FEMALE} if target_gender == "female" else {"$in": _ALL_MALE}

        base: dict = {
            "telegram_id": {"$nin": list(excluded)},
            "is_banned": {"$ne": True},
            "profile_hidden": {"$ne": True},
            "gender": gender_filter,
            "$and": [
                {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
                {
                    "$or": [
                        {"photos.0": {"$exists": True}},
                        {"photo": {"$nin": [None, ""]}},
                    ]
                },
            ],
        }

        if age_min is not None or age_max is not None:
            age_q: dict = {}
            if age_min is not None:
                age_q["$gte"] = age_min
            if age_max is not None:
                age_q["$lte"] = age_max
            if age_q:
                base["age"] = age_q

        if city:
            neighbors = _CITY_NEIGHBORS.get(city, [])
            allowed_cities = [city] + [c for c in neighbors if c and c not in (city,)]
            base["$and"] = list(base.get("$and", []))
            base["$and"].append({"city": {"$in": allowed_cities}})

        docs: list[dict] = []
        async for doc in self._collection.find(base).limit(limit * 2):
            docs.append(doc)

        if not docs:
            return []

        raw_city = getattr(user, "city", None)
        user_city = str(raw_city.as_generic_type() if hasattr(raw_city, "as_generic_type") else raw_city or "").strip()
        user_lat, user_lon = None, None
        raw_lat, raw_lon = getattr(user, "lat", None), getattr(user, "lon", None)
        if raw_lat is not None and raw_lon is not None:
            try:
                user_lat, user_lon = float(raw_lat), float(raw_lon)
            except (TypeError, ValueError):
                pass
        if (user_lat is None or user_lon is None) and user_city:
            coords = get_city_coords(user_city)
            if coords:
                user_lat, user_lon = coords

        _coord_cache: dict[str, tuple[float, float] | None] = {}

        def _candidate_coords(d: dict) -> tuple[float, float] | None:
            if d.get("lat") is not None and d.get("lon") is not None:
                try:
                    return float(d["lat"]), float(d["lon"])
                except (TypeError, ValueError):
                    pass
            c = d.get("city") or ""
            if c not in _coord_cache:
                _coord_cache[c] = get_city_coords(c)
            return _coord_cache[c]

        query_city_lower = (city or "").strip().lower()
        user_city_lower = user_city.lower()

        def _ai_sort_key(d: dict) -> tuple:
            doc_city = (d.get("city") or "").strip().lower()
            city_match = 0 if query_city_lower and doc_city == query_city_lower else 1
            if city_match == 1 and query_city_lower:
                neighbors_lower = [c.lower() for c in _CITY_NEIGHBORS.get(city or "", [])]
                if doc_city in neighbors_lower:
                    city_match = 0.5
            dist = 999999.0
            if user_lat is not None and user_lon is not None:
                crd = _candidate_coords(d)
                if crd:
                    dist = haversine_km(user_lat, user_lon, crd[0], crd[1])
            if city_match == 0 and dist > 100:
                dist = 0.0
            return (city_match, dist)

        docs.sort(key=_ai_sort_key)
        return [convert_user_document_to_entity(d) for d in docs[:limit]]

    async def get_users_liked_from(self, user_list: list[int]) -> Iterable[UserEntity]:
        users_documents = self._collection.find(
            filter={"telegram_id": {"$in": user_list}},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("telegram_id")
            if telegram_id:
                user_entity = await self.get_user_by_telegram_id(
                    telegram_id=telegram_id,
                )
                if user_entity:
                    result.append(user_entity)

        return result

    async def get_users_liked_by(self, user_list: list[int]) -> Iterable[UserEntity]:
        users_documents = self._collection.find(
            filter={"telegram_id": {"$in": user_list}},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("telegram_id")
            if telegram_id:
                user_entity = await self.get_user_by_telegram_id(
                    telegram_id=telegram_id,
                )
                if user_entity:
                    result.append(user_entity)

        return result

    async def get_icebreaker_count(self, telegram_id: int) -> int:
        """
        Для бесплатных пользователей — тотальный счётчик (icebreaker_used).
        Для Premium/VIP — суточный счётчик (icebreaker_daily_used, icebreaker_daily_date).
        Handlers сами решают какой лимит применять по premium_type.
        Здесь возвращаем объект-обёртку в виде числа: используем суточный если есть.
        """
        from datetime import date
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"icebreaker_used": 1, "icebreaker_daily_used": 1, "icebreaker_daily_date": 1},
        )
        if not doc:
            return 0
        # Проверяем суточный счётчик
        daily_date = doc.get("icebreaker_daily_date")
        daily_used = doc.get("icebreaker_daily_used", 0)
        today = str(date.today())
        if daily_date == today:
            return int(daily_used)
        # Новый день — суточный счётчик обнулился
        return 0

    async def get_icebreaker_total_count(self, telegram_id: int) -> int:
        """Тотальный счётчик для бесплатных пользователей."""
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"icebreaker_used": 1},
        )
        return int((doc or {}).get("icebreaker_used", 0))

    async def increment_icebreaker_count(self, telegram_id: int) -> int:
        """Инкрементирует ОБА счётчика: тотальный и суточный."""
        from datetime import date
        today = str(date.today())
        # Атомарно сбрасываем суточный если новый день
        existing = await self._collection.find_one(
            {"telegram_id": telegram_id},
            {"icebreaker_daily_date": 1},
        )
        if existing and existing.get("icebreaker_daily_date") != today:
            await self._collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"icebreaker_daily_used": 0, "icebreaker_daily_date": today}},
            )
        result = await self._collection.find_one_and_update(
            filter={"telegram_id": telegram_id},
            update={"$inc": {"icebreaker_used": 1, "icebreaker_daily_used": 1},
                    "$set": {"icebreaker_daily_date": today}},
            return_document=True,
            projection={"icebreaker_used": 1, "icebreaker_daily_used": 1},
        )
        if not result:
            return 1
        return int(result.get("icebreaker_daily_used", 1))

    async def get_advisor_trial_start(self, telegram_id: int):
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"ai_advisor_first_used": 1},
        )
        if not doc:
            return None
        return doc.get("ai_advisor_first_used")

    async def set_advisor_trial_start(self, telegram_id: int):
        from datetime import datetime, timezone
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": {"ai_advisor_first_used": datetime.now(timezone.utc)}},
        )

    async def get_photos(self, telegram_id: int) -> list[str]:
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"photos": 1},
        )
        if not doc:
            return []
        return doc.get("photos") or []

    async def add_photo(self, telegram_id: int, s3_key: str) -> list[str]:
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$push": {"photos": s3_key}},
        )
        return await self.get_photos(telegram_id)

    async def remove_photo(self, telegram_id: int, index: int) -> list[str]:
        photos = await self.get_photos(telegram_id)
        if index < 0 or index >= len(photos):
            return photos
        photos.pop(index)
        main_photo = photos[0] if photos else None
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": {"photos": photos, "photo": main_photo}},
        )
        return photos

    async def replace_photo(self, telegram_id: int, index: int, s3_key: str) -> list[str]:
        photos = await self.get_photos(telegram_id)
        if index < 0 or index >= len(photos):
            return photos
        photos[index] = s3_key
        update_data: dict = {"photos": photos}
        if index == 0:
            update_data["photo"] = s3_key
        await self._collection.update_one(
            filter={"telegram_id": telegram_id},
            update={"$set": update_data},
        )
        return photos


@dataclass
class MongoDBLikesRepository(BaseLikesRepository, BaseMongoDBRepository):
    async def check_like_is_exists(self, from_user: int, to_user: int) -> bool:
        return bool(
            await self._collection.find_one(
                filter={
                    "from_user": from_user,
                    "to_user": to_user,
                },
            ),
        )

    async def create_like(self, like: LikesEntity) -> LikesEntity:
        await self._collection.insert_one(convert_like_entity_to_document(like))
        return like

    async def delete_like(self, from_user: int, to_user: int):
        await self._collection.delete_one(
            filter={
                "from_user": from_user,
                "to_user": to_user,
            },
        )

    async def get_users_ids_liked_from(self, user_id: int) -> list[int]:
        users_documents = self._collection.find(
            filter={"from_user": user_id},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("to_user")
            if telegram_id:
                result.append(telegram_id)

        return result

    async def get_users_ids_liked_by(self, user_id: int) -> list[int]:
        users_documents = self._collection.find(
            filter={"to_user": user_id},
        )

        result = []
        async for user_document in users_documents:
            telegram_id = user_document.get("from_user")
            if telegram_id:
                result.append(telegram_id)

        return result

    async def count_likes_today(self, from_user: int) -> int:
        from datetime import datetime, timezone
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return await self._collection.count_documents({
            "from_user": from_user,
            "created_at": {"$gte": today_start},
        })


@dataclass
class MongoDBPhotoLikesRepository(BaseMongoDBRepository):
    """Лайки к конкретным фотографиям."""

    async def toggle_like(self, from_user: int, owner_id: int, photo_index: int) -> bool:
        """Добавляет или удаляет лайк. Возвращает True если лайк добавлен."""
        existing = await self._collection.find_one(
            filter={"from_user": from_user, "owner_id": owner_id, "photo_index": photo_index},
        )
        if existing:
            await self._collection.delete_one({"_id": existing["_id"]})
            return False
        from datetime import datetime, timezone
        await self._collection.insert_one({
            "from_user": from_user,
            "owner_id": owner_id,
            "photo_index": photo_index,
            "created_at": datetime.now(timezone.utc),
        })
        return True

    async def get_likes_info(self, owner_id: int, photo_index: int, viewer_id: int) -> dict:
        count = await self._collection.count_documents(
            {"owner_id": owner_id, "photo_index": photo_index}
        )
        liked_by_me = bool(await self._collection.find_one(
            {"from_user": viewer_id, "owner_id": owner_id, "photo_index": photo_index}
        ))
        return {"count": count, "liked_by_me": liked_by_me}

    async def delete_likes_for_photo(self, owner_id: int, photo_index: int) -> int:
        """Удаляет все лайки к конкретному фото. Вызывается при замене/удалении фото."""
        result = await self._collection.delete_many(
            {"owner_id": owner_id, "photo_index": photo_index}
        )
        return result.deleted_count


@dataclass
class MongoDBPhotoCommentsRepository(BaseMongoDBRepository):
    """Комментарии к фотографиям."""

    async def add_comment(self, from_user: int, from_name: str, owner_id: int, photo_index: int, text: str) -> dict:
        from datetime import datetime, timezone
        doc = {
            "from_user": from_user,
            "from_name": from_name,
            "owner_id": owner_id,
            "photo_index": photo_index,
            "text": text,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self._collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return doc

    async def get_comments(self, owner_id: int, photo_index: int, limit: int = 20) -> list[dict]:
        cursor = self._collection.find(
            filter={"owner_id": owner_id, "photo_index": photo_index},
        ).sort("created_at", -1).limit(limit)
        comments = []
        async for doc in cursor:
            comments.append({
                "id": str(doc.get("_id", "")),
                "from_user": doc["from_user"],
                "from_name": doc.get("from_name", ""),
                "text": doc["text"],
                "created_at": doc["created_at"].isoformat() if doc.get("created_at") else "",
            })
        return list(reversed(comments))


@dataclass
class MongoDBDislikesRepository(BaseDislikesRepository, BaseMongoDBRepository):
    """Дизлайки (пропущенные анкеты) — хранятся в коллекции 'dislikes'."""

    async def add_dislike(self, from_user: int, to_user: int) -> None:
        from datetime import datetime, timezone
        await self._collection.update_one(
            {"from_user": from_user, "to_user": to_user},
            {"$set": {"from_user": from_user, "to_user": to_user,
                      "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    async def get_disliked_ids(self, user_id: int) -> list[int]:
        cursor = self._collection.find({"from_user": user_id}, {"to_user": 1})
        return [doc["to_user"] async for doc in cursor]

    async def remove_dislike(self, from_user: int, to_user: int) -> None:
        await self._collection.delete_one({"from_user": from_user, "to_user": to_user})
