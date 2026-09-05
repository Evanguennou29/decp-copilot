from datetime import date

from decp.retrieval.filters import extract_filters


def test_amount_and_departement_from_spec_example():
    filters = extract_filters("moins de 50 000 euros dans le Finistère")
    assert filters.montant_max == 50000.0
    assert filters.montant_min is None
    assert filters.departement_code == "29"


def test_amount_with_k_suffix():
    filters = extract_filters("plus de 50k€ à Rennes")
    assert filters.montant_min == 50000.0


def test_amount_range():
    filters = extract_filters("entre 10 000 et 20 000 euros")
    assert filters.montant_min == 10000.0
    assert filters.montant_max == 20000.0


def test_departement_with_hyphen_and_apostrophe():
    filters = extract_filters("un marché en Ille-et-Vilaine")
    assert filters.departement_code == "35"


def test_year_since():
    filters = extract_filters("des marchés depuis 2025")
    assert filters.date_min == date(2025, 1, 1)
    assert filters.date_max is None


def test_year_in():
    filters = extract_filters("des marchés notifiés en 2024")
    assert filters.date_min == date(2024, 1, 1)
    assert filters.date_max == date(2024, 12, 31)


def test_market_type_keyword():
    filters = extract_filters("des travaux de voirie")
    assert filters.marche_type == "Travaux"


def test_explicit_cpv_code():
    filters = extract_filters("marchés de CPV 45000000")
    assert filters.code_cpv == "45000000"


def test_no_filters_found_on_plain_question():
    filters = extract_filters("nettoyage des locaux municipaux")
    assert filters == extract_filters("nettoyage des locaux municipaux")
    assert filters.montant_min is None
    assert filters.montant_max is None
    assert filters.departement_code is None
    assert filters.date_min is None
    assert filters.marche_type is None
    assert filters.code_cpv is None


def test_combined_question_from_spec_example():
    filters = extract_filters(
        "Quels marchés de moins de 50 000 euros dans le Finistère depuis 2024 ?"
    )
    assert filters.montant_max == 50000.0
    assert filters.departement_code == "29"
    assert filters.date_min == date(2024, 1, 1)
