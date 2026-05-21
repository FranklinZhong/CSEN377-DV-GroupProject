"""
Create a tiny local MedInsight dataset for development.

This avoids the 9 GB first-time dataset download and writes:
  - data/processed/medinsight.db
  - data/processed/FAERS/cleaned_faers_signals_prr_ror.csv

The data is synthetic and intended only for UI/API testing.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FAERS_DIR = PROCESSED_DIR / "FAERS"
DB_PATH = PROCESSED_DIR / "medinsight.db"
DATA_VERSION = "sample-2026Q1"

BODY_TO_SVG = {
    "brain": "nervous_system",
    "eye": "ophthalmologic_system",
    "heart": "cardiovascular_system",
    "lung": "respiratory_system",
    "stomach": "digestive_system",
    "liver": "hepatobiliary_system",
    "kidney": "renal_system",
    "skin": "integumentary_system",
    "muscle": "musculoskeletal_system",
    "blood": "hematologic_system",
    "vascular": "vascular_system",
    "endocrine": "endocrine_system",
    "immune": "immune_system",
}

DRUGS = [
    {
        "name": "metformin",
        "brand_name": "Glucophage",
        "manufacturer": "Sample Pharma",
        "main_use": "Treatment of type 2 diabetes mellitus as an adjunct to diet and exercise.",
        "mechanism": "Decreases hepatic glucose production and improves insulin sensitivity.",
        "dosage": "Tablet; extended-release tablet",
        "route": "oral",
        "rating": 4.1,
        "risk": "medium",
        "benefits": [("endocrine", "glycemic control", "high"), ("vascular", "cardiometabolic support", "medium")],
        "side_effects": [("stomach", "nausea", 42, "medium"), ("stomach", "diarrhea", 37, "medium"), ("brain", "headache", 11, "low")],
        "reviews": [
            (4.5, "positive", "My blood sugar improved and stomach upset settled after the first week.", ["endocrine", "stomach"]),
            (3.0, "mixed", "Helpful for glucose control, but nausea made the dose increase difficult.", ["endocrine", "stomach"]),
            (4.0, "positive", "Once daily dosing is easy and my A1C numbers are better.", ["endocrine"]),
        ],
    },
    {
        "name": "ibuprofen",
        "brand_name": "Advil",
        "manufacturer": "Sample Pharma",
        "main_use": "Temporary relief of minor aches, pain, inflammation, and fever.",
        "mechanism": "Inhibits cyclooxygenase enzymes and reduces prostaglandin synthesis.",
        "dosage": "Tablet; capsule; oral suspension",
        "route": "oral",
        "rating": 3.8,
        "risk": "medium",
        "benefits": [("muscle", "pain relief", "high"), ("immune", "fever reduction", "medium")],
        "side_effects": [("stomach", "abdominal pain", 33, "medium"), ("kidney", "renal function change", 9, "low"), ("skin", "rash", 7, "low")],
        "reviews": [
            (4.0, "positive", "Works quickly for muscle pain after exercise.", ["muscle"]),
            (2.0, "negative", "It helped my headache but caused stomach pain.", ["brain", "stomach"]),
        ],
    },
    {
        "name": "aspirin",
        "brand_name": "Bayer",
        "manufacturer": "Sample Pharma",
        "main_use": "Pain relief, fever reduction, and antiplatelet therapy when directed by a clinician.",
        "mechanism": "Irreversibly inhibits platelet cyclooxygenase and reduces thromboxane formation.",
        "dosage": "Tablet; chewable tablet",
        "route": "oral",
        "rating": 3.7,
        "risk": "high",
        "benefits": [("heart", "antiplatelet effect", "high"), ("muscle", "pain relief", "medium")],
        "side_effects": [("blood", "bleeding", 29, "high"), ("stomach", "gastric irritation", 21, "medium")],
        "reviews": [
            (4.0, "positive", "Useful for daily heart protection under my doctor's plan.", ["heart", "blood"]),
            (2.5, "negative", "Stomach irritation was hard to tolerate.", ["stomach"]),
        ],
    },
    {
        "name": "lisinopril",
        "brand_name": "Prinivil",
        "manufacturer": "Sample Pharma",
        "main_use": "Treatment of hypertension and support for selected heart failure patients.",
        "mechanism": "Inhibits angiotensin-converting enzyme, lowering angiotensin II production.",
        "dosage": "Tablet",
        "route": "oral",
        "rating": 3.6,
        "risk": "medium",
        "benefits": [("heart", "blood pressure control", "high"), ("kidney", "renal protection in selected patients", "medium")],
        "side_effects": [("lung", "dry cough", 26, "medium"), ("vascular", "dizziness", 12, "low")],
        "reviews": [(3.5, "mixed", "Blood pressure is lower, but the dry cough is annoying.", ["heart", "lung"])],
    },
    {
        "name": "amoxicillin",
        "brand_name": "Amoxil",
        "manufacturer": "Sample Pharma",
        "main_use": "Treatment of susceptible bacterial infections.",
        "mechanism": "Inhibits bacterial cell wall synthesis.",
        "dosage": "Capsule; tablet; oral suspension",
        "route": "oral",
        "rating": 4.0,
        "risk": "low",
        "benefits": [("immune", "infection treatment", "high"), ("lung", "respiratory infection treatment", "medium")],
        "side_effects": [("stomach", "diarrhea", 18, "medium"), ("skin", "rash", 14, "medium")],
        "reviews": [(4.0, "positive", "Cleared my sinus infection, with mild stomach discomfort.", ["immune", "stomach"])],
    },
    {
        "name": "sertraline",
        "brand_name": "Zoloft",
        "manufacturer": "Sample Pharma",
        "main_use": "Treatment of depression, anxiety disorders, and related conditions.",
        "mechanism": "Selectively inhibits serotonin reuptake in the central nervous system.",
        "dosage": "Tablet; oral solution",
        "route": "oral",
        "rating": 3.4,
        "risk": "medium",
        "benefits": [("brain", "mood symptom improvement", "high")],
        "side_effects": [("brain", "insomnia", 22, "medium"), ("stomach", "nausea", 17, "medium")],
        "reviews": [(3.5, "mixed", "Anxiety improved, but sleep was worse for a few weeks.", ["brain"])],
    },
    {
        "name": "warfarin",
        "brand_name": "Coumadin",
        "manufacturer": "Sample Pharma",
        "main_use": "Anticoagulation for prevention and treatment of thromboembolic disorders.",
        "mechanism": "Inhibits vitamin K-dependent clotting factor synthesis.",
        "dosage": "Tablet",
        "route": "oral",
        "rating": 3.2,
        "risk": "high",
        "benefits": [("blood", "anticoagulation", "high"), ("heart", "stroke risk reduction", "medium")],
        "side_effects": [("blood", "bleeding", 45, "high"), ("skin", "bruising", 20, "medium")],
        "reviews": [(3.0, "mixed", "Effective anticoagulation, but bruising and INR checks are inconvenient.", ["blood", "skin"])],
    },
    {
        "name": "prednisone",
        "brand_name": "Deltasone",
        "manufacturer": "Sample Pharma",
        "main_use": "Anti-inflammatory and immunosuppressive treatment for many conditions.",
        "mechanism": "Glucocorticoid receptor agonist that suppresses inflammatory signaling.",
        "dosage": "Tablet; oral solution",
        "route": "oral",
        "rating": 3.3,
        "risk": "medium",
        "benefits": [("immune", "inflammation reduction", "high"), ("lung", "airway inflammation relief", "medium")],
        "side_effects": [("endocrine", "weight gain", 24, "medium"), ("brain", "mood change", 16, "medium")],
        "reviews": [(3.0, "mixed", "Breathing improved, but appetite and mood changes were noticeable.", ["lung", "brain", "endocrine"])],
    },
    {
        "name": "adalimumab",
        "brand_name": "Humira",
        "manufacturer": "Sample Pharma",
        "main_use": "Treatment of selected autoimmune inflammatory diseases.",
        "mechanism": "Binds tumor necrosis factor alpha and reduces inflammatory activity.",
        "dosage": "Injection",
        "route": "subcutaneous",
        "rating": 3.9,
        "risk": "medium",
        "benefits": [("immune", "autoimmune inflammation control", "high"), ("skin", "plaque improvement", "medium")],
        "side_effects": [("skin", "injection site reaction", 19, "medium"), ("immune", "infection risk", 13, "medium")],
        "reviews": [(4.0, "positive", "Joint stiffness and skin plaques improved after several doses.", ["immune", "skin", "muscle"])],
    },
    {
        "name": "gabapentin",
        "brand_name": "Neurontin",
        "manufacturer": "Sample Pharma",
        "main_use": "Treatment of neuropathic pain and adjunctive therapy for partial seizures.",
        "mechanism": "Modulates voltage-gated calcium channel activity in nervous tissue.",
        "dosage": "Capsule; tablet; oral solution",
        "route": "oral",
        "rating": 3.5,
        "risk": "medium",
        "benefits": [("brain", "seizure support", "medium"), ("muscle", "nerve pain relief", "high")],
        "side_effects": [("brain", "dizziness", 31, "medium"), ("muscle", "fatigue", 15, "low")],
        "reviews": [(3.5, "mixed", "Nerve pain is better, but dizziness limits daytime use.", ["muscle", "brain"])],
    },
]


def normalize(name: str) -> str:
    return " ".join(name.lower().strip().split())


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS drugs;
        DROP TABLE IF EXISTS drug_aliases;
        DROP TABLE IF EXISTS search_index;
        DROP TABLE IF EXISTS effects;
        DROP TABLE IF EXISTS faers_quarterly;
        DROP TABLE IF EXISTS reviews;
        DROP TABLE IF EXISTS review_clusters;
        DROP TABLE IF EXISTS api_cache;

        CREATE TABLE drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            generic_name TEXT,
            brand_name TEXT,
            manufacturer TEXT,
            fda_id TEXT,
            indication_summary TEXT,
            mechanism_of_action TEXT,
            dosage_form TEXT,
            route TEXT,
            overall_rating REAL,
            risk_level TEXT DEFAULT 'unknown',
            data_version TEXT DEFAULT '2026Q1',
            updated_at TEXT
        );
        CREATE TABLE drug_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            confidence REAL DEFAULT 1.0
        );
        CREATE INDEX idx_alias ON drug_aliases(alias);
        CREATE TABLE search_index (
            drug_id INTEGER,
            normalized_name TEXT,
            first_letter TEXT,
            first_two_letters TEXT
        );
        CREATE INDEX idx_search_norm ON search_index(normalized_name);
        CREATE INDEX idx_search_letter ON search_index(first_letter, first_two_letters);
        CREATE TABLE effects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL,
            body_part TEXT NOT NULL,
            svg_region TEXT NOT NULL,
            effect_name TEXT NOT NULL,
            effect_type TEXT NOT NULL,
            severity TEXT DEFAULT 'unknown',
            source TEXT NOT NULL,
            frequency REAL,
            confidence TEXT DEFAULT 'medium',
            description TEXT
        );
        CREATE INDEX idx_effects_drug ON effects(drug_id, effect_type);
        CREATE TABLE faers_quarterly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            body_part TEXT NOT NULL,
            svg_region TEXT NOT NULL,
            side_effect TEXT NOT NULL,
            report_count INTEGER DEFAULT 0,
            normalized_frequency REAL,
            signal_flag INTEGER DEFAULT 0,
            missing INTEGER DEFAULT 0,
            confidence TEXT DEFAULT 'medium'
        );
        CREATE INDEX idx_fq_drug ON faers_quarterly(drug_id, quarter);
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL,
            rating REAL,
            sentiment TEXT,
            review_text TEXT,
            extracted_body_parts TEXT,
            extracted_effects TEXT,
            source TEXT DEFAULT 'WebMD'
        );
        CREATE TABLE review_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL,
            body_part TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            review_count INTEGER NOT NULL,
            top_terms TEXT,
            representative_quotes TEXT
        );
        CREATE INDEX idx_rc_drug ON review_clusters(drug_id);
        CREATE TABLE api_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE INDEX idx_cache_key ON api_cache(cache_key);
        """
    )


def confidence(count: int) -> str:
    if count >= 50:
        return "high"
    if count >= 10:
        return "medium"
    if count >= 3:
        return "low"
    return "insufficient"


def quarters() -> list[str]:
    return [f"{year}Q{q}" for year in range(2024, 2027) for q in range(1, 5) if not (year == 2026 and q > 1)]


def insert_data(conn: sqlite3.Connection) -> None:
    now = datetime.now(UTC).replace(tzinfo=None).isoformat()
    drug_ids: dict[str, int] = {}

    for drug in DRUGS:
        cur = conn.execute(
            """
            INSERT INTO drugs (
                name, generic_name, brand_name, manufacturer, fda_id,
                indication_summary, mechanism_of_action, dosage_form, route,
                overall_rating, risk_level, data_version, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                drug["name"],
                drug["name"],
                drug["brand_name"],
                drug["manufacturer"],
                f"sample-{drug['name']}",
                drug["main_use"],
                drug["mechanism"],
                drug["dosage"],
                drug["route"],
                drug["rating"],
                drug["risk"],
                DATA_VERSION,
                now,
            ),
        )
        drug_id = int(cur.lastrowid)
        drug_ids[drug["name"]] = drug_id

        names = {drug["name"], drug["brand_name"], f"{drug['name']} tablet"}
        for alias in sorted(names):
            norm = normalize(alias)
            conn.execute(
                "INSERT INTO drug_aliases (alias, canonical_name, confidence) VALUES (?, ?, ?)",
                (norm, drug["name"], 1.0 if norm == drug["name"] else 0.92),
            )
            conn.execute(
                "INSERT INTO search_index (drug_id, normalized_name, first_letter, first_two_letters) VALUES (?, ?, ?, ?)",
                (drug_id, norm, norm[:1].upper(), norm[:2].upper()),
            )

        for body_part, effect_name, severity in drug["benefits"]:
            conn.execute(
                """
                INSERT INTO effects (
                    drug_id, body_part, svg_region, effect_name, effect_type,
                    severity, source, frequency, confidence, description
                )
                VALUES (?, ?, ?, ?, 'benefit', ?, 'Synthetic FDA label sample', ?, 'medium', ?)
                """,
                (
                    drug_id,
                    body_part,
                    BODY_TO_SVG[body_part],
                    effect_name,
                    severity,
                    0.8 if severity == "high" else 0.55,
                    f"Sample indication mapping for {effect_name}.",
                ),
            )

        for body_part, effect_name, count, severity in drug["side_effects"]:
            conn.execute(
                """
                INSERT INTO effects (
                    drug_id, body_part, svg_region, effect_name, effect_type,
                    severity, source, frequency, confidence, description
                )
                VALUES (?, ?, ?, ?, 'side_effect', ?, 'Synthetic FAERS sample', ?, ?, ?)
                """,
                (
                    drug_id,
                    body_part,
                    BODY_TO_SVG[body_part],
                    effect_name,
                    severity,
                    count / 100.0,
                    confidence(count),
                    f"Synthetic adverse event count used for local testing: {count}.",
                ),
            )

        for rating, sentiment, text, body_parts in drug["reviews"]:
            conn.execute(
                """
                INSERT INTO reviews (
                    drug_id, rating, sentiment, review_text,
                    extracted_body_parts, extracted_effects, source
                )
                VALUES (?, ?, ?, ?, ?, ?, 'Synthetic WebMD sample')
                """,
                (drug_id, rating, sentiment, text, json.dumps(body_parts), None),
            )

        build_review_clusters(conn, drug_id)
        build_quarterly_rows(conn, drug_id, drug)
        cache_trend(conn, drug_id, drug)

    conn.commit()


def build_review_clusters(conn: sqlite3.Connection, drug_id: int) -> None:
    rows = conn.execute(
        "SELECT sentiment, review_text, extracted_body_parts FROM reviews WHERE drug_id = ?",
        (drug_id,),
    ).fetchall()
    grouped: dict[tuple[str, str], list[str]] = {}
    for sentiment, text, parts_json in rows:
        for body_part in json.loads(parts_json):
            grouped.setdefault((body_part, sentiment), []).append(text)

    for (body_part, sentiment), texts in grouped.items():
        conn.execute(
            """
            INSERT INTO review_clusters (
                drug_id, body_part, sentiment, review_count, top_terms, representative_quotes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                drug_id,
                body_part,
                sentiment,
                len(texts),
                json.dumps([body_part, "sample", "review"]),
                json.dumps(texts[:2]),
            ),
        )


def build_quarterly_rows(conn: sqlite3.Connection, drug_id: int, drug: dict) -> None:
    qs = quarters()
    for effect_index, (body_part, side_effect, base_count, _severity) in enumerate(drug["side_effects"]):
        peak = max(base_count, 1)
        for quarter_index, quarter in enumerate(qs):
            seasonal = (quarter_index % 4) + 1
            count = max(1, int(base_count * (0.35 + seasonal * 0.12 + effect_index * 0.05)))
            signal = 1 if quarter in {"2025Q4", "2026Q1"} and count > 15 and effect_index == 0 else 0
            conn.execute(
                """
                INSERT INTO faers_quarterly (
                    drug_id, quarter, body_part, svg_region, side_effect,
                    report_count, normalized_frequency, signal_flag, missing, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    drug_id,
                    quarter,
                    body_part,
                    BODY_TO_SVG[body_part],
                    side_effect,
                    count,
                    round(count / peak, 4),
                    signal,
                    confidence(count),
                ),
            )


def cache_trend(conn: sqlite3.Connection, drug_id: int, drug: dict) -> None:
    rows = conn.execute(
        """
        SELECT quarter, body_part, svg_region, report_count, normalized_frequency,
               signal_flag, missing, confidence
        FROM faers_quarterly
        WHERE drug_id = ?
        ORDER BY quarter, body_part
        """,
        (drug_id,),
    ).fetchall()
    timeline = [
        {
            "quarter": row[0],
            "body_part": row[1],
            "svg_region": row[2],
            "report_count": row[3],
            "normalized_frequency": row[4],
            "signal_flag": bool(row[5]),
            "missing": bool(row[6]),
            "confidence": row[7],
        }
        for row in rows
    ]
    signal_events = [
        {
            "quarter": point["quarter"],
            "body_part": point["body_part"],
            "report_count": point["report_count"],
            "increase_pct": 35,
        }
        for point in timeline
        if point["signal_flag"]
    ]
    now = datetime.now(UTC).replace(tzinfo=None)
    conn.execute(
        """
        INSERT INTO api_cache (cache_key, response_json, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            f"faers_trend:v1:{drug['name']}",
            json.dumps({"timeline": timeline, "signal_events": signal_events}),
            now.isoformat(),
            (now + timedelta(days=365)).isoformat(),
        ),
    )


def write_sample_faers_csv() -> None:
    FAERS_DIR.mkdir(parents=True, exist_ok=True)
    path = FAERS_DIR / "cleaned_faers_signals_prr_ror.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["DRUGNAME_NORM", "PT_NORM", "QTR", "n_reports", "PRR", "ROR", "any_signal"],
        )
        writer.writeheader()
        for drug in DRUGS:
            for quarter in quarters():
                for body_part, effect_name, count, _severity in drug["side_effects"]:
                    writer.writerow(
                        {
                            "DRUGNAME_NORM": drug["name"].upper(),
                            "PT_NORM": effect_name.upper(),
                            "QTR": quarter,
                            "n_reports": max(1, int(count / 3)),
                            "PRR": "1.5",
                            "ROR": "1.8",
                            "any_signal": "1" if count > 20 else "0",
                        }
                    )


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_sample_faers_csv()

    for suffix in ("", "-journal", "-wal", "-shm"):
        path = Path(f"{DB_PATH}{suffix}")
        if path.exists():
            path.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        init_schema(conn)
        insert_data(conn)
    finally:
        conn.close()

    print(f"Created sample database: {DB_PATH}")
    print(f"Created sample FAERS CSV: {FAERS_DIR / 'cleaned_faers_signals_prr_ror.csv'}")
    print("Synthetic drugs:", ", ".join(d["name"] for d in DRUGS))


if __name__ == "__main__":
    main()
