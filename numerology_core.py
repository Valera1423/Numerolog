# numerology_core.py
from datetime import date, datetime
from typing import Dict, Any, List, Tuple

def reduce_to_single(n: int, keep_master: bool = True) -> int:
    """Сводит число к однозначному, сохраняя мастер-числа 11 и 22."""
    if keep_master and n in (11, 22):
        return n
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n

# ===========================
# 1. БАЗОВЫЕ РАСЧЁТЫ (из Бота №2)
# ===========================

def get_life_path_number(birthdate: str) -> int:
    """Число жизненного пути (из даты). Формат YYYY-MM-DD"""
    try:
        d = datetime.strptime(birthdate, "%Y-%m-%d")
        total = d.day + d.month + d.year
        return reduce_to_single(total)
    except ValueError:
        return 0

def get_expression_number(fio: str) -> int:
    """Число выражения (по ФИО)."""
    ru = {
        'а':1,'б':2,'в':3,'г':4,'д':5,'е':6,'ё':7,'ж':8,'з':9,
        'и':1,'й':2,'к':3,'л':4,'м':5,'н':6,'о':7,'п':8,'р':9,
        'с':1,'т':2,'у':3,'ф':4,'х':5,'ц':6,'ч':7,'ш':8,'щ':9,
        'ъ':1,'ы':2,'ь':3,'э':4,'ю':5,'я':6
    }
    fio = fio.lower()
    total = sum(ru.get(ch, 0) for ch in fio if ch in ru)
    return reduce_to_single(total)

def get_soul_urge_number(fio: str) -> int:
    """Число души (гласные)."""
    ru_vowels = {'а':1,'е':6,'ё':7,'и':1,'о':7,'у':3,'ы':2,'э':4,'ю':5,'я':6}
    fio = fio.lower()
    total = sum(ru_vowels.get(ch, 0) for ch in fio if ch in ru_vowels)
    return reduce_to_single(total)

def get_personality_number(fio: str) -> int:
    """Число личности (согласные)."""
    ru_cons = {
        'б':2,'в':3,'г':4,'д':5,'ж':8,'з':9,'й':2,'к':3,'л':4,
        'м':5,'н':6,'п':8,'р':9,'с':1,'т':2,'у':3,'ф':4,'х':5,'ц':6,
        'ч':7,'ш':8,'щ':9,'ъ':1,'ь':3
    }
    fio = fio.lower()
    total = sum(ru_cons.get(ch, 0) for ch in fio if ch in ru_cons)
    return reduce_to_single(total)

def calculate_numerology(birthdate: str, fio: str) -> Dict[str, Any]:
    """Полный базовый профиль."""
    return {
        "life_path": get_life_path_number(birthdate),
        "expression": get_expression_number(fio),
        "soul_urge": get_soul_urge_number(fio),
        "personality": get_personality_number(fio),
        "birthdate": birthdate,
        "fio": fio
    }

# ===========================
# 2. БЛОКИРОВКИ И ЛИЧНЫЙ ГОД (из Бота №3)
# ===========================

def money_block_number(birthdate: date) -> int:
    """Блокировка денег = день рождения."""
    return reduce_to_single(birthdate.day)

def relations_block_number(birthdate: date) -> int:
    """Блокировка отношений = месяц рождения."""
    return reduce_to_single(birthdate.month)

def health_block_number(birthdate: date) -> int:
    """Блокировка здоровья = сумма судьбы + сумма цифр года."""
    lp = get_life_path_number(birthdate.strftime("%Y-%m-%d"))
    year_sum = reduce_to_single(sum(int(d) for d in str(birthdate.year)))
    return reduce_to_single(lp + year_sum)

def personal_year(birthdate: date, target_year: int = 2026) -> int:
    """Личный год: день + месяц + сумма цифр года."""
    year_sum = reduce_to_single(sum(int(d) for d in str(target_year)))
    total = birthdate.day + birthdate.month + year_sum
    return reduce_to_single(total)

# ===========================
# 3. СОВМЕСТИМОСТЬ (из Бота №2)
# ===========================

def calculate_compatibility(birthdate1: str, fio1: str, birthdate2: str, fio2: str) -> Dict[str, Any]:
    """Расчёт совместимости двух людей."""
    p1 = calculate_numerology(birthdate1, fio1)
    p2 = calculate_numerology(birthdate2, fio2)
    
    lc = 10 - abs(p1["life_path"] - p2["life_path"])
    ec = 10 - abs(p1["soul_urge"] - p2["soul_urge"])
    ic = 10 - abs(p1["expression"] - p2["expression"])
    pc = 10 - abs(p1["personality"] - p2["personality"])
    
    total = round(lc * 0.4 + ec * 0.3 + ic * 0.2 + pc * 0.1, 1)
    
    challenges = []
    if abs(p1["life_path"] - p2["life_path"]) > 5:
        challenges.append("Разные жизненные пути")
    if abs(p1["soul_urge"] - p2["soul_urge"]) > 5:
        challenges.append("Разные эмоциональные потребности")
        
    return {
        "person1": p1,
        "person2": p2,
        "compatibility": {
            "life_path": lc, "emotional": ec, "intellectual": ic, "physical": pc, "total": total
        },
        "challenges": challenges
    }

# ===========================
# 4. КАРМИЧЕСКИЕ УРОКИ (из Бота №2)
# ===========================

def get_karmic_lessons(fio: str) -> List[int]:
    """
    Определяет кармические уроки на основе отсутствующих чисел в ФИО.
    Возвращает список чисел (1-9), которых нет в имени.
    """
    ru_letters = {
        'а':1, 'б':2, 'в':3, 'г':4, 'д':5, 'е':6, 'ё':7, 'ж':8, 'з':9,
        'и':1, 'й':2, 'к':3, 'л':4, 'м':5, 'н':6, 'о':7, 'п':8, 'р':9,
        'с':1, 'т':2, 'у':3, 'ф':4, 'х':5, 'ц':6, 'ч':7, 'ш':8, 'щ':9,
        'ъ':1, 'ы':2, 'ь':3, 'э':4, 'ю':5, 'я':6
    }
    en_letters = {
        'a':1, 'b':2, 'c':3, 'd':4, 'e':5, 'f':6, 'g':7, 'h':8, 'i':9,
        'j':1, 'k':2, 'l':3, 'm':4, 'n':5, 'o':6, 'p':7, 'q':8, 'r':9,
        's':1, 't':2, 'u':3, 'v':4, 'w':5, 'x':6, 'y':7, 'z':8
    }
    
    # Счётчик для чисел 1-9
    counts = {i: 0 for i in range(1, 10)}
    fio_lower = fio.lower()
    
    for ch in fio_lower:
        if ch in ru_letters:
            counts[ru_letters[ch]] += 1
        elif ch in en_letters:
            counts[en_letters[ch]] += 1
    
    # Кармические уроки – числа, которых нет (0 вхождений)
    lessons = [num for num, cnt in counts.items() if cnt == 0]
    return lessons

# ===========================
# 5. МАТРИЦА ПИФАГОРА (ПСИХОМАТРИЦА) (из Бота №2)
# ===========================

def get_pythagoras_matrix(birthdate: str) -> Dict[str, int]:
    """
    Возвращает психоматрицу (квадрат Пифагора) на основе даты рождения.
    Формат даты: YYYY-MM-DD.
    Возвращает словарь {цифра: количество_вхождений} для цифр 1-9.
    """
    try:
        d = datetime.strptime(birthdate, "%Y-%m-%d")
        date_str = f"{d.day:02d}{d.month:02d}{d.year}"
        # Подсчитываем частоту каждой цифры от 1 до 9
        matrix = {str(i): date_str.count(str(i)) for i in range(1, 10)}
        return matrix
    except ValueError:
        return {str(i): 0 for i in range(1, 10)}