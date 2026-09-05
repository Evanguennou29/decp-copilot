"""Extract structured filters (montant, département, date, type, CPV) from
a free-text question.

This module only recognizes filters that are unambiguous to parse with
patterns — an exact amount, a named département, a year, an explicit CPV
code, a market type keyword. Anything fuzzier (a sector described in
words, a buyer name) is left to the semantic layer in ``retrieval.hybrid``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

# INSEE département codes, including Corsica (2A/2B) and the five DOM.
# Accents and hyphenation match the official denominations used in the
# DECP dataset's acheteur_departement_nom / titulaire_departement_nom columns.
DEPARTMENTS: dict[str, str] = {
    "ain": "01",
    "aisne": "02",
    "allier": "03",
    "alpes-de-haute-provence": "04",
    "hautes-alpes": "05",
    "alpes-maritimes": "06",
    "ardeche": "07",
    "ardennes": "08",
    "ariege": "09",
    "aube": "10",
    "aude": "11",
    "aveyron": "12",
    "bouches-du-rhone": "13",
    "calvados": "14",
    "cantal": "15",
    "charente": "16",
    "charente-maritime": "17",
    "cher": "18",
    "correze": "19",
    "corse-du-sud": "2A",
    "haute-corse": "2B",
    "cote-d'or": "21",
    "cotes-d'armor": "22",
    "creuse": "23",
    "dordogne": "24",
    "doubs": "25",
    "drome": "26",
    "eure": "27",
    "eure-et-loir": "28",
    "finistere": "29",
    "gard": "30",
    "haute-garonne": "31",
    "gers": "32",
    "gironde": "33",
    "herault": "34",
    "ille-et-vilaine": "35",
    "indre": "36",
    "indre-et-loire": "37",
    "isere": "38",
    "jura": "39",
    "landes": "40",
    "loir-et-cher": "41",
    "loire": "42",
    "haute-loire": "43",
    "loire-atlantique": "44",
    "loiret": "45",
    "lot": "46",
    "lot-et-garonne": "47",
    "lozere": "48",
    "maine-et-loire": "49",
    "manche": "50",
    "marne": "51",
    "haute-marne": "52",
    "mayenne": "53",
    "meurthe-et-moselle": "54",
    "meuse": "55",
    "morbihan": "56",
    "moselle": "57",
    "nievre": "58",
    "nord": "59",
    "oise": "60",
    "orne": "61",
    "pas-de-calais": "62",
    "puy-de-dome": "63",
    "pyrenees-atlantiques": "64",
    "hautes-pyrenees": "65",
    "pyrenees-orientales": "66",
    "bas-rhin": "67",
    "haut-rhin": "68",
    "rhone": "69",
    "haute-saone": "70",
    "saone-et-loire": "71",
    "sarthe": "72",
    "savoie": "73",
    "haute-savoie": "74",
    "paris": "75",
    "seine-maritime": "76",
    "seine-et-marne": "77",
    "yvelines": "78",
    "deux-sevres": "79",
    "somme": "80",
    "tarn": "81",
    "tarn-et-garonne": "82",
    "var": "83",
    "vaucluse": "84",
    "vendee": "85",
    "vienne": "86",
    "haute-vienne": "87",
    "vosges": "88",
    "yonne": "89",
    "territoire-de-belfort": "90",
    "essonne": "91",
    "hauts-de-seine": "92",
    "seine-saint-denis": "93",
    "val-de-marne": "94",
    "val-d'oise": "95",
    "guadeloupe": "971",
    "martinique": "972",
    "guyane": "973",
    "la reunion": "974",
    "reunion": "974",
    "mayotte": "976",
}

_MARKET_TYPES = {"fournitures": "Fournitures", "services": "Services", "travaux": "Travaux"}

_LESS_THAN_WORDS = (
    r"(?:moins de|inf[ée]rieur[e]? [àa]|en dessous de|max(?:imum)?(?: de)?|jusqu'[àa])"
)
_MORE_THAN_WORDS = (
    r"(?:plus de|sup[ée]rieur[e]? [àa]|au-dessus de|au dessus de|"
    r"min(?:imum)?(?: de)?|[àa] partir de)"
)

_AMOUNT = r"(\d[\d\s.,]*)\s*(k€|k|€|euros?)?"

_MONTANT_MAX_RE = re.compile(rf"{_LESS_THAN_WORDS}\s+{_AMOUNT}", re.IGNORECASE)
_MONTANT_MIN_RE = re.compile(rf"{_MORE_THAN_WORDS}\s+{_AMOUNT}", re.IGNORECASE)
_MONTANT_RANGE_RE = re.compile(
    rf"entre\s+{_AMOUNT}\s+et\s+{_AMOUNT}", re.IGNORECASE
)
_CPV_RE = re.compile(r"\bcpv\D{0,3}(\d{8})\b", re.IGNORECASE)
_YEAR_SINCE_RE = re.compile(r"depuis\s+(20\d{2})", re.IGNORECASE)
_YEAR_IN_RE = re.compile(r"\ben\s+(20\d{2})\b", re.IGNORECASE)


def _normalize(text: str) -> str:
    """Lowercase and strip accents for département name matching."""
    replacements = str.maketrans("àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ", "aaaeeeeiioouuucAAAEEEEIIOOUUUC")
    return text.translate(replacements).lower()


def _parse_amount(digits: str, unit: str | None) -> float:
    cleaned = re.sub(r"[\s,](?=\d{3}\b)", "", digits.strip())
    cleaned = cleaned.replace(",", ".")
    value = float(cleaned)
    if unit and unit.lower().startswith("k"):
        value *= 1000
    return value


@dataclass(frozen=True)
class Filters:
    montant_min: float | None = None
    montant_max: float | None = None
    departement_code: str | None = None
    date_min: date | None = None
    date_max: date | None = None
    marche_type: str | None = None
    code_cpv: str | None = None


def extract_filters(question: str) -> Filters:
    """Parse an amount range, a département, a year, a type, and/or a CPV
    code out of a free-text French question. Any field left unmentioned is
    ``None`` and simply isn't applied as a filter."""
    montant_min: float | None = None
    montant_max: float | None = None

    range_match = _MONTANT_RANGE_RE.search(question)
    if range_match:
        montant_min = _parse_amount(range_match.group(1), range_match.group(2))
        montant_max = _parse_amount(range_match.group(3), range_match.group(4))
    else:
        max_match = _MONTANT_MAX_RE.search(question)
        if max_match:
            montant_max = _parse_amount(max_match.group(1), max_match.group(2))
        min_match = _MONTANT_MIN_RE.search(question)
        if min_match:
            montant_min = _parse_amount(min_match.group(1), min_match.group(2))

    normalized = _normalize(question)
    departement_code = None
    # Longest name first: "maine-et-loire" must win over "loire", which is
    # itself a hyphen-bounded (so \b-matching) substring of it — same trap
    # for "savoie"/"haute-savoie" and "marne"/"seine-et-marne".
    for name, code in sorted(DEPARTMENTS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(name)}\b", normalized):
            departement_code = code
            break

    date_min: date | None = None
    date_max: date | None = None
    since_match = _YEAR_SINCE_RE.search(question)
    in_year_match = _YEAR_IN_RE.search(question)
    if since_match:
        date_min = date(int(since_match.group(1)), 1, 1)
    elif in_year_match:
        year = int(in_year_match.group(1))
        date_min = date(year, 1, 1)
        date_max = date(year, 12, 31)

    marche_type = None
    for keyword, label in _MARKET_TYPES.items():
        if re.search(rf"\b{keyword}\b", normalized):
            marche_type = label
            break

    cpv_match = _CPV_RE.search(question)
    code_cpv = cpv_match.group(1) if cpv_match else None

    return Filters(
        montant_min=montant_min,
        montant_max=montant_max,
        departement_code=departement_code,
        date_min=date_min,
        date_max=date_max,
        marche_type=marche_type,
        code_cpv=code_cpv,
    )
