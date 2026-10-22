from datetime import datetime
import re

from flask import Flask, g, render_template, request, redirect, url_for
from dotenv import load_dotenv
import pyodbc
import os

app = Flask(__name__)


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

def get_db():
    if "db" not in g:
        g.db = pyodbc.connect(conn_string)
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.route("/items")
def items():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            i.ItemName,
            i.AssetTag,
            i.Status,
            c.DueDate,
            e.FullName
        FROM ITEMS i
        LEFT JOIN Checkouts c ON i.ItemID = c.ItemID AND c.CheckinDate IS NULL
        LEFT JOIN ENDUSER e ON c.UserID = e.UserID
    """)
    result = cursor.fetchall()
    return render_template("items.html", items=result)

@app.route("/add-item", methods=["GET", "POST"])
def add_item():
    if request.method == "POST":
        item_name = request.form["item_name"]
        asset_tag = request.form["asset_tag"]
        category_id = request.form["category_id"]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO ITEMS (AssetTag, ItemName, CategoryID) VALUES (?, ?, ?)""",
            (asset_tag,item_name,category_id)
        )
        db.commit()

        return redirect(url_for("items"))  # send them to the inventory page after adding
    else:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT CategoryID, CategoryName FROM Categories")
        categories = cursor.fetchall()
        return render_template("add_item.html", categories=categories)

@app.route("/add-category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category_name = request.form["category_name"]
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO Categories (CategoryName) VALUES (?)""",
                (category_name,)
            )
            db.commit()
            return redirect(url_for("add_item"))  # send them to the add items page after adding
        except:
            return render_template("add_category.html", error="That category already exists.")
    else:
        return render_template("add_category.html")

def get_form_data():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT ItemID, ItemName FROM ITEMS WHERE Status = 'Available' AND IsActive = 1")
    items = cursor.fetchall()
    cursor.execute("SELECT UserID, FullName FROM ENDUSER WHERE IsActive = 1 ORDER BY FullName")
    users = cursor.fetchall()
    date_today = datetime.now().date()
    return {"items": items, "users": users, "today": date_today}

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "GET":
        return render_template("checkout.html", **get_form_data())
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()
        ItemId = request.form["item_id"]
        UserId = request.form["user_id"]
        TicketNumber = request.form["ticket_number"]
        DueDate = request.form["due_date"]
        try:
            checkoutsp = "EXEC sp_CheckoutItem @ItemID=?, @UserID=?, @TicketNumber=?, @DueDate=?"
            cursor.execute(
                checkoutsp,
                (ItemId, UserId, TicketNumber, DueDate)
            )
            while cursor.nextset():
                pass
            db.commit()
            return redirect(url_for("items"))  # send them to the inventory page after checkout
        except Exception as e:
            print("Error during checkout:", e)
            db.rollback()  # Rollback the transaction in case of error
            return render_template("checkout.html", **get_form_data(), error = "An error occurred during checkout. Please try again.")


def get_checkouts():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            c.CheckoutID,
            i.ItemName,
            e.FullName,
            c.DueDate
        FROM Checkouts c
        JOIN ITEMS i ON c.ItemID = i.ItemID
        JOIN ENDUSER e ON c.UserID = e.UserID
        WHERE c.CheckinDate IS NULL
    """)
    checkouts = cursor.fetchall()
    return {"checkouts": checkouts}

@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    if request.method == "GET":
        return render_template("checkin.html", **get_checkouts())
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()
        CheckoutId = request.form["checkout_id"]
        try:
            checkinsp = "EXEC sp_CheckinItem @CheckoutID=?"
            cursor.execute(
                checkinsp,
                (CheckoutId,)
            )
            while cursor.nextset():
                pass
            db.commit()
            return redirect(url_for("items"))  # send them to the inventory page after checkin
        except Exception as e:
            print("Error during checkin:", e)
            db.rollback()  # Rollback the transaction in case of error
            return render_template("checkin.html", **get_checkouts(), error = "An error occurred during checkin. Please try again.")  # Redirect back to the checkin page on error

if __name__ == "__main__":
    app.run(debug=True, port=5001)