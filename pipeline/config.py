from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_RAW       = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
FAERS_DIR      = DATA_RAW / "faers"
WEBMD_DIR      = DATA_RAW / "webmd"
DB_PATH        = DATA_PROCESSED / "medinsight.db"
