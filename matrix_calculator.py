# matrix_calculator.py
from datetime import date
from numerology_core import reduce_to_single

def calculate_shadow_matrix(birthdate: date, name: str = "") -> dict:
    """
    Полный расчёт Теневой Матрицы Судьбы (методика Натальи Яницкой).
    Возвращает словарь со всеми арканами и ключами.
    """
    day = birthdate.day
    month = birthdate.month
    year = birthdate.year

    # 1. Базовые арканы (день, месяц, год) — сведение до 1–22
    arc_day = reduce_to_single(day)
    arc_month = reduce_to_single(month)
    arc_year = reduce_to_single(year)

    # 2. Второй ряд: сумма дня и месяца, месяца и года, всех трёх
    arc_day_month = reduce_to_single(arc_day + arc_month)
    arc_month_year = reduce_to_single(arc_month + arc_year)
    arc_total = reduce_to_single(arc_day + arc_month + arc_year)

    # 3. Третий ряд: диагонали (крест)
    arc_cross1 = reduce_to_single(arc_day + arc_month_year)
    arc_cross2 = reduce_to_single(arc_month + arc_year)
    arc_cross_total = reduce_to_single(arc_cross1 + arc_cross2)

    # 4. Центр (главный аркан судьбы)
    arc_center = reduce_to_single(arc_cross_total + arc_total)

    # 5. Ключи реализации (по методике)
    # КРТ (Ключ Реализации Таланта) = сумма дня и месяца
    key_talent = reduce_to_single(arc_day + arc_month)
    # КРП (Ключ Реализации Предназначения) = сумма месяца и года
    key_destiny = reduce_to_single(arc_month + arc_year)
    # ЦРП (Центр Родовых Программ) = сумма дня и года
    center_family = reduce_to_single(arc_day + arc_year)

    # 6. Дополнительные позиции (для полной матрицы)
    # Личностный центр (ЦЛ) = сумма дня и месяца (то же, что КРТ)
    personality_center = key_talent
    # Центр предназначения (ЦП) = сумма месяца и года (то же, что КРП)
    destiny_center = key_destiny
    # Ключ реализации кармической задачи (КРКЗ) = сумма всех трёх базовых
    karmic_key = arc_total

    # Собираем всё в словарь
    matrix = {
        "day": arc_day,                     # День рождения (аркан)
        "month": arc_month,                 # Месяц рождения
        "year": arc_year,                   # Год рождения
        "day_month": arc_day_month,         # Сумма дня и месяца
        "month_year": arc_month_year,       # Сумма месяца и года
        "total": arc_total,                 # Сумма всех трёх
        "cross1": arc_cross1,               # Диагональ 1
        "cross2": arc_cross2,               # Диагональ 2
        "cross_total": arc_cross_total,     # Сумма диагоналей
        "center": arc_center,               # Центральный аркан (судьба)
        "key_talent": key_talent,           # КРТ
        "key_destiny": key_destiny,         # КРП
        "center_family": center_family,     # ЦРП (родовые программы)
        "personality_center": personality_center,
        "destiny_center": destiny_center,
        "karmic_key": karmic_key,
    }
    return matrix