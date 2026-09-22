from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    code: str
    name_uk: str
    name_en: str
    aliases: tuple[str, ...]


REGIONS: tuple[Region, ...] = (
    Region("vinnytsia_oblast", "Вінницька область", "Vinnytsia Oblast", ("vinnytsia oblast", "vinnytsia region")),
    Region("volyn_oblast", "Волинська область", "Volyn Oblast", ("volyn oblast", "volyn region")),
    Region("dnipropetrovsk_oblast", "Дніпропетровська область", "Dnipropetrovsk Oblast", ("dnipropetrovsk oblast", "dnipropetrovsk region")),
    Region("donetsk_oblast", "Донецька область", "Donetsk Oblast", ("donetsk oblast", "donetsk region")),
    Region("zhytomyr_oblast", "Житомирська область", "Zhytomyr Oblast", ("zhytomyr oblast", "zhytomyr region")),
    Region("zakarpattia_oblast", "Закарпатська область", "Zakarpattia Oblast", ("zakarpattia oblast", "zakarpattia region", "transcarpathian region")),
    Region("zaporizhzhia_oblast", "Запорізька область", "Zaporizhzhia Oblast", ("zaporizhzhia oblast", "zaporizhzhia region", "zaporizhia oblast", "zaporizhia region")),
    Region("ivano_frankivsk_oblast", "Івано-Франківська область", "Ivano-Frankivsk Oblast", ("ivano-frankivsk oblast", "ivano frankivsk oblast", "ivano-frankivsk region", "ivano frankivsk region")),
    Region("kyiv_oblast", "Київська область", "Kyiv Oblast", ("kyiv oblast", "kyiv region", "kiev oblast", "kiev region")),
    Region("kirovohrad_oblast", "Кіровоградська область", "Kirovohrad Oblast", ("kirovohrad oblast", "kirovohrad region", "kirovograd oblast", "kirovograd region")),
    Region("luhansk_oblast", "Луганська область", "Luhansk Oblast", ("luhansk oblast", "luhansk region", "lugansk oblast", "lugansk region")),
    Region("lviv_oblast", "Львівська область", "Lviv Oblast", ("lviv oblast", "lviv region")),
    Region("mykolaiv_oblast", "Миколаївська область", "Mykolaiv Oblast", ("mykolaiv oblast", "mykolaiv region", "nikolaev oblast", "nikolaev region")),
    Region("odesa_oblast", "Одеська область", "Odesa Oblast", ("odesa oblast", "odesa region", "odessa oblast", "odessa region")),
    Region("poltava_oblast", "Полтавська область", "Poltava Oblast", ("poltava oblast", "poltava region")),
    Region("rivne_oblast", "Рівненська область", "Rivne Oblast", ("rivne oblast", "rivne region", "rovno oblast", "rovno region")),
    Region("sumy_oblast", "Сумська область", "Sumy Oblast", ("sumy oblast", "sumy region")),
    Region("ternopil_oblast", "Тернопільська область", "Ternopil Oblast", ("ternopil oblast", "ternopil region")),
    Region("kharkiv_oblast", "Харківська область", "Kharkiv Oblast", ("kharkiv oblast", "kharkiv region", "kharkov oblast", "kharkov region")),
    Region("kherson_oblast", "Херсонська область", "Kherson Oblast", ("kherson oblast", "kherson region")),
    Region("khmelnytskyi_oblast", "Хмельницька область", "Khmelnytskyi Oblast", ("khmelnytskyi oblast", "khmelnytskyi region", "khmelnitsky oblast", "khmelnitsky region")),
    Region("cherkasy_oblast", "Черкаська область", "Cherkasy Oblast", ("cherkasy oblast", "cherkasy region")),
    Region("chernivtsi_oblast", "Чернівецька область", "Chernivtsi Oblast", ("chernivtsi oblast", "chernivtsi region")),
    Region("chernihiv_oblast", "Чернігівська область", "Chernihiv Oblast", ("chernihiv oblast", "chernihiv region", "chernigov oblast", "chernigov region")),
    Region("crimea", "Автономна Республіка Крим", "Autonomous Republic of Crimea", ("autonomous republic of crimea", "crimea")),
    Region("kyiv_city", "м. Київ", "Kyiv City", ("kyiv city", "city of kyiv", "kiev city", "city of kiev")),
    Region("sevastopol_city", "м. Севастополь", "Sevastopol City", ("sevastopol city", "city of sevastopol")),
)


def _normalize_text(value: str) -> str:
    value = value.lower().replace("_", " ")
    return re.sub(r"\s+", " ", value).strip()


def extract_region_codes(value: object) -> list[str]:
    """Extract only explicit administrative-region mentions.

    Bare city names are intentionally not mapped to oblasts.
    """
    if value is None:
        return []

    text = _normalize_text(str(value))
    if not text or text in {"nan", "none", "null"}:
        return []

    matches: list[str] = []
    for region in REGIONS:
        for alias in region.aliases:
            pattern = rf"(?<![a-z]){re.escape(alias)}(?![a-z])"
            if re.search(pattern, text):
                matches.append(region.code)
                break
    return matches
