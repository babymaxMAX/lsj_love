from abc import ABC
from dataclasses import dataclass
from typing import Iterable

from motor.core import AgnosticClient

from app.domain.entities.likes import LikesEntity
from app.domain.entities.users import UserEntity
from app.domain.values.users import AboutText
from app.infra.repositories.base import (
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
        from datetime import datetime, timezone
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []

        user_age = user.age
        age_min = int(user_age) - 5
        age_max = int(user_age) + 5

        excluded = list(exclude_ids or [])
        excluded.append(telegram_id)

        now = datetime.now(timezone.utc)

        query_filter: dict = {
            "telegram_id": {"$nin": excluded},
            "profile_hidden": {"$ne": True},
            "$expr": {
                "$and": [
                    {"$gte": [{"$toInt": "$age"}, age_min]},
                    {"$lte": [{"$toInt": "$age"}, age_max]},
                ],
            },
        }

        if hasattr(user, "gender") and user.gender:
            gender_map = {"Мужской": "Женский", "Женский": "Мужской", "Man": "Female", "Female": "Man"}
            target_gender = gender_map.get(str(user.gender))
            if target_gender:
                query_filter["gender"] = target_gender

        # Фильтр по городу: сначала только свой город
        user_city = str(getattr(user, "city", "") or "").strip()
        if user_city:
            query_filter["city"] = user_city

        # Приоритетная сортировка: boosted → VIP → Premium → бесплатные
        pipeline = [
            {"$match": query_filter},
            {"$addFields": {
                "_sort_priority": {
                    "$switch": {
                        "branches": [
                            # Boost активен
                            {
                                "case": {"$and": [
                                    {"$gt": ["$boost_until", now]},
                                ]},
                                "then": 0,
                            },
                            # VIP с активной подпиской
                            {
                                "case": {"$and": [
                                    {"$eq": ["$premium_type", "vip"]},
                                    {"$gt": ["$premium_until", now]},
                                ]},
                                "then": 1,
                            },
                            # Premium с активной подпиской
                            {
                                "case": {"$and": [
                                    {"$eq": ["$premium_type", "premium"]},
                                    {"$gt": ["$premium_until", now]},
                                ]},
                                "then": 2,
                            },
                        ],
                        "default": 3,
                    }
                }
            }},
            {"$sort": {"_sort_priority": 1}},
            {"$project": {"_sort_priority": 0}},
        ]

        result = []
        async for doc in self._collection.aggregate(pipeline):
            result.append(convert_user_document_to_entity(user_document=doc))

        # Если не нашли никого в своём городе — ищем в ближайших городах
        if not result and user_city:
            neighbors = _CITY_NEIGHBORS.get(user_city, [])
            if neighbors:
                fallback_filter = dict(query_filter)
                fallback_filter.pop("city", None)
                fallback_filter["city"] = {"$in": neighbors}
                fallback_pipeline = [
                    {"$match": fallback_filter},
                    {"$addFields": {"_sort_priority": {"$switch": {
                        "branches": [
                            {"case": {"$and": [{"$gt": ["$boost_until", now]}]}, "then": 0},
                            {"case": {"$and": [{"$eq": ["$premium_type", "vip"]}, {"$gt": ["$premium_until", now]}]}, "then": 1},
                            {"case": {"$and": [{"$eq": ["$premium_type", "premium"]}, {"$gt": ["$premium_until", now]}]}, "then": 2},
                        ],
                        "default": 3,
                    }}}},
                    {"$sort": {"_sort_priority": 1}},
                    {"$project": {"_sort_priority": 0}},
                ]
                async for doc in self._collection.aggregate(fallback_pipeline):
                    result.append(convert_user_document_to_entity(user_document=doc))

            # Если и в ближайших городах никого — ищем по всей базе без фильтра города
            if not result:
                global_filter = dict(query_filter)
                global_filter.pop("city", None)
                global_pipeline = [
                    {"$match": global_filter},
                    {"$addFields": {"_sort_priority": {"$switch": {
                        "branches": [
                            {"case": {"$and": [{"$gt": ["$boost_until", now]}]}, "then": 0},
                            {"case": {"$and": [{"$eq": ["$premium_type", "vip"]}, {"$gt": ["$premium_until", now]}]}, "then": 1},
                            {"case": {"$and": [{"$eq": ["$premium_type", "premium"]}, {"$gt": ["$premium_until", now]}]}, "then": 2},
                        ],
                        "default": 3,
                    }}}},
                    {"$sort": {"_sort_priority": 1}},
                    {"$project": {"_sort_priority": 0}},
                ]
                async for doc in self._collection.aggregate(global_pipeline):
                    result.append(convert_user_document_to_entity(user_document=doc))

        return result

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
        doc = await self._collection.find_one(
            filter={"telegram_id": telegram_id},
            projection={"icebreaker_used": 1},
        )
        if not doc:
            return 0
        return int(doc.get("icebreaker_used", 0))

    async def increment_icebreaker_count(self, telegram_id: int) -> int:
        result = await self._collection.find_one_and_update(
            filter={"telegram_id": telegram_id},
            update={"$inc": {"icebreaker_used": 1}},
            return_document=True,
            projection={"icebreaker_used": 1},
        )
        if not result:
            return 1
        return int(result.get("icebreaker_used", 1))

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
