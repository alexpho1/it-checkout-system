import os
from dotenv import load_dotenv
import pyodbc

load_dotenv()

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

conn =pyodbc.connect(conn_string)

cursor = conn.cursor()
cursor.execute("""WITH CheckoutsWithType AS (
    SELECT
        c.CheckoutID,
        c.ItemID,
        c.UserID,
        c.CheckoutDate,
        c.DueDate,
        c.CheckinDate,
        CASE
            WHEN (DATEDIFF(Day,GETDATE(),DueDate) = 3) THEN 'Early'
            WHEN (CAST(GETDATE() AS DATE) = DueDate) THEN 'Due'
            WHEN (DATEDIFF(Day, DueDate, GETDATE()) > 0 AND DATEDIFF(Day, DueDate, GETDATE()) % 3 = 0) THEN 'Late'
            ELSE NULL

        END AS ReminderType
    FROM Checkouts c
)
SELECT
    cwt.CheckoutID,
    i.ItemName,
    e.FullName,
    e.Email,
    cwt.DueDate,
    cwt.ReminderType
FROM CheckoutsWithType cwt
JOIN ITEMS i ON cwt.ItemID = i.ItemID
JOIN ENDUSER e ON cwt.UserID = e.UserID
WHERE
    cwt.ReminderType IS NOT NULL
    AND cwt.CheckinDate IS NULL
    AND NOT EXISTS (
        SELECT 1 FROM Reminder_Log r
        WHERE r.CheckoutID = cwt.CheckoutID
          AND r.SentDate = CAST(GETDATE() AS DATE)
          AND r.ReminderType = cwt.ReminderType
    )""")
result = cursor.fetchall()

for row in result:
    print(f"Would send email to {row.Email} about {row.ItemName}, due {row.DueDate}")