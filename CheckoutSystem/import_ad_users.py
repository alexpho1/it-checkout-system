# import_ad_users.py
import csv
import os
import sys

import pyodbc
from dotenv import load_dotenv

load_dotenv()

# --- 1. Config ---------------------------------------------------------
dbuser = os.getenv("DB_USER")
dbpassword = os.getenv("DB_PASSWORD")
dbserver = os.getenv("DB_SERVER")
dbname = os.getenv("DB_NAME")

conn_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={dbserver};"
    f"DATABASE={dbname};"
    f"UID={dbuser};"
    f"PWD={dbpassword};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
import_dir = os.getenv("IMPORT_DIR", os.path.join(BASE_DIR, "Imports"))


def get_csv_path():
    # 1. Did the user type a filename?
    if len(sys.argv) < 2:
        print("Usage: python import_ad_users.py <filename.csv>")
        sys.exit(1)

    path = os.path.join(import_dir, sys.argv[1])

    # 2. Does the file exist?
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Importing from: {path}")
    return path


# Map CSV headers (AD names) to staging columns
# CSV:     ObjectGUID, SamAccountName, DisplayName, Mail, Enabled
# Staging: OBJECTGUID, ADusername,     FullName,    Email, IsActive


# --- 2. Read the CSV ---------------------------------------------------
def clean(value):
    """Blank or missing cell -> None, otherwise the trimmed text."""
    if value is None:
        return None
    value = value.strip()
    return value if value != "" else None


def to_bit(value):
    """'TRUE'/'FALSE' -> 1/0. Blank -> None. Anything else -> stop."""
    value = clean(value)
    if value is None:
        return None
    if value.upper() == "TRUE":
        return 1
    if value.upper() == "FALSE":
        return 0
    print(f"Unexpected value for Enabled: {value!r}")
    sys.exit(1)

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        needed = ["ObjectGUID", "SamAccountName", "DisplayName", "Mail", "Enabled"]
        missing = [h for h in needed if h not in (reader.fieldnames or [])]
        if missing:
            print(f"CSV is missing columns: {', '.join(missing)}")
            sys.exit(1)

        rows = []
        for row in reader:
            rows.append((
                clean(row["ObjectGUID"]),
                clean(row["SamAccountName"]),
                clean(row["DisplayName"]),
                clean(row["Mail"]),
                to_bit(row["Enabled"]),
            ))
    return rows

# --- 3. Load staging ---------------------------------------------------
def load_staging(cursor, rows):
    cursor.execute("DELETE FROM stg_ADUsers")
    cursor.executemany(
        "INSERT INTO stg_ADUsers (OBJECTGUID, ADusername, FullName, Email, IsActive) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )


# --- 4. Run the procedure ----------------------------------------------
def run_import(cursor):
    cursor.execute("EXEC sp_ImportADUsers")
    while cursor.nextset():
        pass


# --- 5. Main -----------------------------------------------------------
def main():
    rows = read_csv(get_csv_path())
    print(f"Read {len(rows)} rows")

    conn = None
    try:
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()
        load_staging(cursor, rows)
        run_import(cursor)
        conn.commit()
        print("Import complete. Check import_log for the counts.")
    except pyodbc.Error as e:
        if conn:
            conn.rollback()
        print("Import FAILED:", e)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()


