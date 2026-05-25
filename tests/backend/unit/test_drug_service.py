"""
Unit tests for backend.services.drug_service.

Pure-function tests run without a DB; search/fuzzy/find_alt tests use db_conn.
"""

import pytest
from backend.services.drug_service import (
    normalize,
    search_drugs,
    fuzzy_search,
    find_alt_drug_id,
    get_drug_by_id,
)


# ── Pure function: normalize ──────────────────────────────────────────────────

def test_normalize_removes_dosage():
    # DRUG-U-01
    assert normalize("Metformin 500 mg") == "metformin"


def test_normalize_removes_salt():
    # DRUG-U-02: "calcium" not in suffix list; use "sodium" which IS listed
    assert normalize("Aspirin sodium") == "aspirin"


def test_normalize_removes_form():
    # DRUG-U-03
    result = normalize("Aspirin oral tablet")
    assert result == "aspirin"


def test_normalize_strips_hbr():
    assert normalize("citalopram hbr") == "citalopram"


def test_normalize_lowercases():
    assert normalize("WARFARIN") == "warfarin"


# ── DB-backed: search_drugs ───────────────────────────────────────────────────

def test_search_prefix_returns_match(db_conn):
    # DRUG-U-04
    results = search_drugs("met", db_conn)
    assert results, "prefix 'met' should match metformin"
    assert any("metformin" in r["name"].lower() for r in results)


def test_search_alias_resolves_to_canonical(db_conn):
    # DRUG-U-05
    results = search_drugs("glucophage", db_conn)
    assert results, "alias 'glucophage' should resolve to metformin"
    assert any("metformin" in r["name"].lower() for r in results)
    assert results[0]["match_type"] == "alias"


def test_search_no_results_for_gibberish(db_conn):
    # DRUG-U-06
    assert search_drugs("zzzxxxq", db_conn) == []


# ── DB-backed: fuzzy_search ───────────────────────────────────────────────────

def test_fuzzy_typo_amoxicillin(db_conn):
    # DRUG-U-07: "amoxcillin" (missing 'i') → amoxicillin, score ≥ 0.85
    results = fuzzy_search("amoxcillin", db_conn)
    assert results, "fuzzy 'amoxcillin' should match 'amoxicillin'"
    assert any("amoxicillin" in r["name"].lower() for r in results)
    assert results[0]["score"] >= 0.85


def test_fuzzy_no_match_for_gibberish(db_conn):
    # DRUG-U-08: clearly non-drug string stays below 72% cutoff
    results = fuzzy_search("zzzzqq", db_conn)
    assert results == []


# ── DB-backed: find_alt_drug_id ───────────────────────────────────────────────

def test_find_alt_salt_variant(db_conn):
    # DRUG-U-09: "citalopram hbr" (drug_id=13) → base compound citalopram (id=12)
    result = find_alt_drug_id(13, "citalopram hbr", db_conn)
    assert result == 12


def test_find_alt_combo_drug(db_conn):
    # DRUG-U-10: "hydrocodone-acetaminophen" (id=15) → "hydrocodone" (id=14)
    result = find_alt_drug_id(15, "hydrocodone-acetaminophen", db_conn)
    assert result == 14


# ── get_drug_by_id ────────────────────────────────────────────────────────────

def test_get_drug_by_id_not_found(db_conn):
    # DRUG-U-11
    assert get_drug_by_id(999999, db_conn) is None


def test_get_drug_by_id_found(db_conn):
    result = get_drug_by_id(1, db_conn)
    assert result is not None
    assert result["name"] == "Metformin"
