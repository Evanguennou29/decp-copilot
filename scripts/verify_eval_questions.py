"""Verify eval/questions.jsonl against the real corpus.

For every question: runs the real ``extract_filters`` and checks that
each expected market's real montant/département/type genuinely satisfies
whatever filter was parsed out of the question text (catching both typos
in the question and bugs in filter extraction — this is exactly how the
lot 2 département-matching bug was caught while authoring this set), and
that every expected uid actually exists in ``data/decp.duckdb``.

Run by hand: ``python scripts/verify_eval_questions.py``. Not part of CI
or the pytest suite (it needs the real ingested database on disk).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from decp.retrieval.filters import extract_filters

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "eval" / "questions.jsonl"
DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "decp.duckdb"


def main() -> int:
    questions = [
        json.loads(line)
        for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    con = duckdb.connect(str(DATABASE_PATH), read_only=True)
    ok = True
    for q in questions:
        filters = extract_filters(q["question"])
        placeholders = ",".join(["?"] * len(q["expected_uids"]))
        rows = con.execute(
            "SELECT uid, montant, acheteur_departement_code, type "
            f"FROM marches WHERE uid IN ({placeholders})",
            q["expected_uids"],
        ).fetchall()
        found_uids = {r[0] for r in rows}
        missing = set(q["expected_uids"]) - found_uids
        if missing:
            print(f"{q['id']}: !!! expected uid(s) not found in database: {missing}")
            ok = False
        for uid, montant, dep_code, typ in rows:
            problems = []
            montant_max = filters.montant_max
            montant_min = filters.montant_min
            if montant_max is not None and montant is not None and montant > montant_max:
                problems.append(f"montant {montant} > montant_max {montant_max}")
            if montant_min is not None and montant is not None and montant < montant_min:
                problems.append(f"montant {montant} < montant_min {montant_min}")
            if filters.departement_code is not None and dep_code != filters.departement_code:
                problems.append(f"departement {dep_code} != filter {filters.departement_code}")
            if filters.marche_type is not None and typ != filters.marche_type:
                problems.append(f"type {typ} != filter {filters.marche_type}")
            if problems:
                print(f"{q['id']}: !!! {uid}: {'; '.join(problems)}")
                ok = False
    con.close()

    if ok:
        print(f"All {len(questions)} questions verified against {DATABASE_PATH}.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
