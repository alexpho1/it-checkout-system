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
cursor.execute("""SELECT
    c.CheckoutID,
    i.ItemName,
    e.FullName,
    e.Email,
    c.CheckoutDate,
    c.DueDate
FROM
    CHECKOUTS c
JOIN
    ITEMS i ON c.ItemID = i.ItemID
JOIN
    ENDUSER e ON c.UserID = e.UserID
WHERE
    ((DATEDIFF(Day,GETDATE(),DueDate) = 3 AND c.CheckinDate IS NULL)
    OR
    (CAST(GETDATE() AS DATE) = DueDate AND c.CheckinDate IS NULL)
    OR
    (DATEDIFF(Day, DueDate, GETDATE()) > 0 AND DATEDIFF(Day, DueDate, GETDATE()) % 3 = 0 AND c.CheckinDate IS NULL))
    AND NOT EXISTS (SELECT 1 FROM REMINDER_LOG r WHERE r.CheckoutID = c.CheckoutID AND r.SentDate = CAST(GETDATE() AS DATE) AND r.ReminderType = CASE WHEN DATEDIFF(Day, GETDATE(), DueDate) = 3 THEN 'Early' WHEN (DATEDIFF(Day, DueDate, GETDATE()) > 0 AND DATEDIFF(Day, DueDate, GETDATE()) % 3 = 0) THEN 'Late' ELSE 'Due' END)
""")
result = cursor.fetchall()
for row in result:
    print(row)

print(len(result))