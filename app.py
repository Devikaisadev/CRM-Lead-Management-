
import os
from dotenv import load_dotenv

load_dotenv()
import re
from datetime import datetime
from functools import wraps

import mysql.connector
from mysql.connector import Error

from flask import (
    Flask, jsonify, render_template, request,
    redirect, url_for, session, flash
)

from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Devika@2005"),
    "database": os.getenv("DB_NAME", "mini_crm"),
}

STATUSES = ("New", "Contacted", "Interested", "Converted", "Lost")

SOURCES = (
    "Website", "Referral", "Social Media",
    "Email", "Phone", "Advertisement", "Other"
)


# Connect to MySQL
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


# Execute database queries
def query_db(sql, params=(), fetch="all", commit=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(sql, params)

        if commit:
            conn.commit()
            return cursor.lastrowid

        if fetch == "one":
            return cursor.fetchone()

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# Login protection
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401

            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper


# Validate lead information
def validate_lead(data):
    errors = {}

    required = (
        "full_name", "email", "phone",
        "company_name", "lead_source", "lead_status"
    )

    for field in required:
        if not str(data.get(field, "")).strip():
            errors[field] = "This field is required."

    email = str(data.get("email", "")).strip()

    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors["email"] = "Enter a valid email address."

    phone = str(data.get("phone", "")).strip()

    if phone and not re.match(r"^[0-9+\-\s()]{7,20}$", phone):
        errors["phone"] = "Enter a valid phone number."

    if data.get("lead_status") and data["lead_status"] not in STATUSES:
        errors["lead_status"] = "Choose a valid lead status."

    if data.get("lead_source") and data["lead_source"] not in SOURCES:
        errors["lead_source"] = "Choose a valid lead source."

    return errors


# Format date before sending JSON
def lead_payload(row):
    if not row:
        return None

    if isinstance(row.get("created_at"), datetime):
        row["created_at"] = row["created_at"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    return row


# Home page
@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# Registration
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if (
            not name
            or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)
            or len(password) < 8
        ):
            flash(
                "Enter a valid name, email and password of at least 8 characters.",
                "danger"
            )
            return render_template("register.html")

        try:
            hashed_password = generate_password_hash(password)

            query_db(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password),
                commit=True
            )

            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))

        except Error as e:
            print("Registration database error:", e)

            if e.errno == 1062:
                flash("This email is already registered.", "danger")
            else:
                flash("Registration failed. Please check your database.", "danger")

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            user = query_db(
                "SELECT id, name, email, password FROM users WHERE email=%s",
                (email,),
                "one"
            )

            if user and check_password_hash(user["password"], password):

                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]

                return redirect(url_for("dashboard"))

            flash("Invalid email or password.", "danger")

        except Error as e:
            print("Login database error:", e)
            flash("Unable to connect to the database.", "danger")

    return render_template("login.html")


# Logout
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        statuses=STATUSES,
        sources=SOURCES
    )


# Dashboard statistics
@app.route("/api/dashboard/stats")
@login_required
def dashboard_stats():

    rows = query_db(
        """
        SELECT
            COUNT(*) AS total,
            SUM(lead_status='New') AS new_leads,
            SUM(lead_status='Contacted') AS contacted_leads,
            SUM(lead_status='Converted') AS converted_leads
        FROM leads
        WHERE user_id=%s
        """,
        (session["user_id"],),
        "one"
    )

    return jsonify({
        key: int(value or 0)
        for key, value in rows.items()
    })


# Get and create leads
@app.route("/api/leads", methods=["GET", "POST"])
@login_required
def leads_api():

    uid = session["user_id"]

    if request.method == "GET":

        search = request.args.get("search", "").strip()
        status = request.args.get("status", "").strip()

        sql = """
            SELECT id, full_name, email, phone,
                   company AS company_name,
                   lead_source, lead_status, created_at
            FROM leads
            WHERE user_id=%s
        """

        params = [uid]

        if search:
            like = f"%{search}%"
            sql += """
                AND (
                    full_name LIKE %s
                    OR email LIKE %s
                    OR company LIKE %s
                )
            """
            params.extend([like, like, like])

        if status and status in STATUSES:
            sql += " AND lead_status=%s"
            params.append(status)

        sql += " ORDER BY created_at DESC"

        results = query_db(sql, tuple(params))

        return jsonify([lead_payload(row) for row in results])

    data = request.get_json(silent=True) or request.form.to_dict()

    errors = validate_lead(data)

    if errors:
        return jsonify({
            "error": "Validation failed",
            "fields": errors
        }), 400

    lead_id = query_db(
        """
        INSERT INTO leads
        (user_id, full_name, email, phone, company,
         lead_source, lead_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            uid,
            data["full_name"].strip(),
            data["email"].strip().lower(),
            data["phone"].strip(),
            data["company_name"].strip(),
            data["lead_source"],
            data["lead_status"]
        ),
        commit=True
    )

    return jsonify({
        "message": "Lead created successfully",
        "id": lead_id
    }), 201


# View, update and delete individual leads
@app.route("/api/leads/<int:lead_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def lead_detail_api(lead_id):

    uid = session["user_id"]

    existing = query_db(
        """
        SELECT id, user_id, full_name, email, phone,
               company AS company_name,
               lead_source, lead_status, created_at
        FROM leads
        WHERE id=%s AND user_id=%s
        """,
        (lead_id, uid),
        "one"
    )

    if not existing:
        return jsonify({"error": "Lead not found"}), 404

    if request.method == "GET":
        return jsonify(lead_payload(existing))

    if request.method == "DELETE":

        query_db(
            "DELETE FROM leads WHERE id=%s AND user_id=%s",
            (lead_id, uid),
            commit=True
        )

        return jsonify({"message": "Lead deleted successfully"})

    data = request.get_json(silent=True) or request.form.to_dict()

    errors = validate_lead(data)

    if errors:
        return jsonify({
            "error": "Validation failed",
            "fields": errors
        }), 400

    query_db(
        """
        UPDATE leads
        SET full_name=%s, email=%s, phone=%s,
            company=%s, lead_source=%s, lead_status=%s
        WHERE id=%s AND user_id=%s
        """,
        (
            data["full_name"].strip(),
            data["email"].strip().lower(),
            data["phone"].strip(),
            data["company_name"].strip(),
            data["lead_source"],
            data["lead_status"],
            lead_id,
            uid
        ),
        commit=True
    )

    return jsonify({"message": "Lead updated successfully"})


# Handle database errors in API requests
@app.errorhandler(Error)
def handle_database_error(error):

    print("MySQL error:", error)

    if request.path.startswith("/api/"):
        return jsonify({
            "error": "Database connection or query failed."
        }), 500

    flash("Database error. Please check your MySQL connection.", "danger")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
