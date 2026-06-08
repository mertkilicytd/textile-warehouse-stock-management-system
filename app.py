from functools import wraps
import sqlite3
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "warehouse.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-for-production"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    schema_path = BASE_DIR / "schema.sql"
    conn = get_db_connection()
    with open(schema_path, "r", encoding="utf-8") as file:
        conn.executescript(file.read())

    employee_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if employee_count == 0:
        conn.execute(
            "INSERT INTO employees (full_name, username, password) VALUES (?, ?, ?)",
            ("Adil Topçu", "admin", generate_password_hash("admin123")),
        )
        conn.execute(
            "INSERT INTO employees (full_name, username, password) VALUES (?, ?, ?)",
            ("Mert Kılıç", "mert", generate_password_hash("mert123")),
        )

        categories = ["T-Shirt", "Pants", "Jacket", "Shirt", "Sweatshirt"]
        conn.executemany("INSERT INTO categories (category_name) VALUES (?)", [(c,) for c in categories])

        suppliers = [
            ("Marmara Textile", "+90 212 111 11 11", "info@marmaratextile.com", "Istanbul"),
            ("Anatolia Fabric", "+90 216 222 22 22", "sales@anatoliafabric.com", "Bursa"),
            ("Ege Clothing Supply", "+90 232 333 33 33", "contact@egeclothing.com", "Izmir"),
        ]
        conn.executemany(
            "INSERT INTO suppliers (supplier_name, phone, email, address) VALUES (?, ?, ?, ?)",
            suppliers,
        )

        products = [
            ("Basic Cotton T-Shirt", 1, 1, "CottonLine", 249.90),
            ("Slim Fit Pants", 2, 2, "UrbanWear", 699.90),
            ("Winter Jacket", 3, 3, "NorthStyle", 1499.90),
            ("Classic Oxford Shirt", 4, 1, "OfficeMode", 549.90),
            ("Hooded Sweatshirt", 5, 2, "StreetLab", 799.90),
        ]
        conn.executemany(
            """
            INSERT INTO products (product_name, category_id, supplier_id, brand, price)
            VALUES (?, ?, ?, ?, ?)
            """,
            products,
        )

        variants = [
            (1, "S", "White", 25),
            (1, "M", "Black", 8),
            (1, "L", "Navy", 40),
            (2, "32", "Black", 15),
            (2, "34", "Blue", 5),
            (3, "M", "Khaki", 12),
            (3, "L", "Black", 3),
            (4, "M", "White", 28),
            (5, "L", "Gray", 17),
        ]
        conn.executemany(
            "INSERT INTO product_variants (product_id, size, color, stock_quantity) VALUES (?, ?, ?, ?)",
            variants,
        )

        movements = [
            (1, 1, "ENTRY", 25),
            (2, 1, "ENTRY", 8),
            (4, 2, "EXIT", 3),
            (7, 1, "ENTRY", 3),
        ]
        conn.executemany(
            """
            INSERT INTO stock_movements (variant_id, employee_id, movement_type, quantity)
            VALUES (?, ?, ?, ?)
            """,
            movements,
        )

    conn.commit()
    conn.close()


@app.before_request
def setup_database():
    if not DB_PATH.exists():
        init_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "employee_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        employee = conn.execute("SELECT * FROM employees WHERE username = ?", (username,)).fetchone()
        conn.close()

        if employee and check_password_hash(employee["password"], password):
            session.clear()
            session["employee_id"] = employee["employee_id"]
            session["full_name"] = employee["full_name"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    conn = get_db_connection()
    product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    variant_count = conn.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]
    total_stock = conn.execute("SELECT COALESCE(SUM(stock_quantity), 0) FROM product_variants").fetchone()[0]
    low_stock_count = conn.execute("SELECT COUNT(*) FROM product_variants WHERE stock_quantity < 10").fetchone()[0]
    recent_movements = conn.execute(
        """
        SELECT sm.movement_type, sm.quantity, sm.movement_date,
               e.full_name, p.product_name, pv.size, pv.color
        FROM stock_movements sm
        JOIN employees e ON sm.employee_id = e.employee_id
        JOIN product_variants pv ON sm.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        ORDER BY sm.movement_date DESC
        LIMIT 8
        """
    ).fetchall()
    conn.close()
    return render_template(
        "dashboard.html",
        product_count=product_count,
        variant_count=variant_count,
        total_stock=total_stock,
        low_stock_count=low_stock_count,
        recent_movements=recent_movements,
    )


@app.route("/products")
@login_required
def products():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT p.product_id, p.product_name, p.brand, p.price,
               c.category_name, s.supplier_name,
               COUNT(pv.variant_id) AS variant_count,
               COALESCE(SUM(pv.stock_quantity), 0) AS total_stock
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        LEFT JOIN product_variants pv ON p.product_id = pv.product_id
        GROUP BY p.product_id
        ORDER BY p.product_name
        """
    ).fetchall()
    conn.close()
    return render_template("products.html", products=rows)


@app.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY category_name").fetchall()
    suppliers = conn.execute("SELECT * FROM suppliers ORDER BY supplier_name").fetchall()

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        category_id = request.form.get("category_id")
        supplier_id = request.form.get("supplier_id")
        brand = request.form.get("brand", "").strip()
        price = request.form.get("price", 0)

        if not product_name:
            flash("Product name is required.", "danger")
        else:
            conn.execute(
                """
                INSERT INTO products (product_name, category_id, supplier_id, brand, price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (product_name, category_id, supplier_id, brand, price),
            )
            conn.commit()
            conn.close()
            flash("Product added successfully.", "success")
            return redirect(url_for("products"))

    conn.close()
    return render_template("product_form.html", categories=categories, suppliers=suppliers, product=None)


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        flash("Product not found.", "danger")
        return redirect(url_for("products"))

    categories = conn.execute("SELECT * FROM categories ORDER BY category_name").fetchall()
    suppliers = conn.execute("SELECT * FROM suppliers ORDER BY supplier_name").fetchall()

    if request.method == "POST":
        conn.execute(
            """
            UPDATE products
            SET product_name = ?, category_id = ?, supplier_id = ?, brand = ?, price = ?
            WHERE product_id = ?
            """,
            (
                request.form.get("product_name", "").strip(),
                request.form.get("category_id"),
                request.form.get("supplier_id"),
                request.form.get("brand", "").strip(),
                request.form.get("price", 0),
                product_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Product updated successfully.", "success")
        return redirect(url_for("products"))

    conn.close()
    return render_template("product_form.html", categories=categories, suppliers=suppliers, product=product)


@app.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()
        flash("Product deleted successfully.", "success")
    except sqlite3.IntegrityError:
        flash("This product has related variants or stock movements. Delete related records first.", "danger")
    finally:
        conn.close()
    return redirect(url_for("products"))


@app.route("/variants")
@login_required
def variants():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT pv.variant_id, pv.size, pv.color, pv.stock_quantity,
               p.product_name, p.brand, c.category_name
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        ORDER BY p.product_name, pv.size, pv.color
        """
    ).fetchall()
    conn.close()
    return render_template("variants.html", variants=rows)


@app.route("/variants/add", methods=["GET", "POST"])
@login_required
def add_variant():
    conn = get_db_connection()
    product_list = conn.execute("SELECT product_id, product_name FROM products ORDER BY product_name").fetchall()

    if request.method == "POST":
        conn.execute(
            """
            INSERT INTO product_variants (product_id, size, color, stock_quantity)
            VALUES (?, ?, ?, ?)
            """,
            (
                request.form.get("product_id"),
                request.form.get("size", "").strip(),
                request.form.get("color", "").strip(),
                int(request.form.get("stock_quantity", 0)),
            ),
        )
        conn.commit()
        conn.close()
        flash("Product variant added successfully.", "success")
        return redirect(url_for("variants"))

    conn.close()
    return render_template("variant_form.html", products=product_list, variant=None)


@app.route("/variants/<int:variant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_variant(variant_id):
    conn = get_db_connection()
    variant = conn.execute("SELECT * FROM product_variants WHERE variant_id = ?", (variant_id,)).fetchone()
    if variant is None:
        conn.close()
        flash("Variant not found.", "danger")
        return redirect(url_for("variants"))

    product_list = conn.execute("SELECT product_id, product_name FROM products ORDER BY product_name").fetchall()

    if request.method == "POST":
        conn.execute(
            """
            UPDATE product_variants
            SET product_id = ?, size = ?, color = ?, stock_quantity = ?
            WHERE variant_id = ?
            """,
            (
                request.form.get("product_id"),
                request.form.get("size", "").strip(),
                request.form.get("color", "").strip(),
                int(request.form.get("stock_quantity", 0)),
                variant_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Variant updated successfully.", "success")
        return redirect(url_for("variants"))

    conn.close()
    return render_template("variant_form.html", products=product_list, variant=variant)


@app.route("/variants/<int:variant_id>/delete", methods=["POST"])
@login_required
def delete_variant(variant_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM product_variants WHERE variant_id = ?", (variant_id,))
        conn.commit()
        flash("Variant deleted successfully.", "success")
    except sqlite3.IntegrityError:
        flash("This variant has stock movements. Delete movement records first.", "danger")
    finally:
        conn.close()
    return redirect(url_for("variants"))


@app.route("/stock-movements")
@login_required
def stock_movements():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT sm.movement_id, sm.movement_type, sm.quantity, sm.movement_date,
               e.full_name, p.product_name, pv.size, pv.color
        FROM stock_movements sm
        JOIN employees e ON sm.employee_id = e.employee_id
        JOIN product_variants pv ON sm.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        ORDER BY sm.movement_date DESC
        """
    ).fetchall()
    conn.close()
    return render_template("stock_movements.html", movements=rows)


@app.route("/stock-movements/add", methods=["GET", "POST"])
@login_required
def add_stock_movement():
    conn = get_db_connection()
    variant_list = conn.execute(
        """
        SELECT pv.variant_id, pv.size, pv.color, pv.stock_quantity, p.product_name
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        ORDER BY p.product_name, pv.size, pv.color
        """
    ).fetchall()

    if request.method == "POST":
        variant_id = int(request.form.get("variant_id"))
        movement_type = request.form.get("movement_type")
        quantity = int(request.form.get("quantity", 0))
        employee_id = session["employee_id"]

        variant = conn.execute(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = ?",
            (variant_id,),
        ).fetchone()

        if quantity <= 0:
            flash("Quantity must be greater than zero.", "danger")
        elif movement_type == "EXIT" and variant["stock_quantity"] < quantity:
            flash("Stock exit cannot be greater than current stock.", "danger")
        else:
            conn.execute(
                """
                INSERT INTO stock_movements (variant_id, employee_id, movement_type, quantity, movement_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (variant_id, employee_id, movement_type, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )

            operator = "+" if movement_type == "ENTRY" else "-"
            conn.execute(
                f"UPDATE product_variants SET stock_quantity = stock_quantity {operator} ? WHERE variant_id = ?",
                (quantity, variant_id),
            )
            conn.commit()
            conn.close()
            flash("Stock movement saved and stock quantity updated.", "success")
            return redirect(url_for("stock_movements"))

    conn.close()
    return render_template("stock_movement_form.html", variants=variant_list)


@app.route("/low-stock")
@login_required
def low_stock():
    threshold = request.args.get("threshold", 10, type=int)
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT p.product_name, p.brand, pv.size, pv.color, pv.stock_quantity,
               c.category_name, s.supplier_name
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        WHERE pv.stock_quantity < ?
        ORDER BY pv.stock_quantity ASC
        """,
        (threshold,),
    ).fetchall()
    conn.close()
    return render_template("low_stock.html", variants=rows, threshold=threshold)


@app.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    conn = get_db_connection()
    if request.method == "POST":
        category_name = request.form.get("category_name", "").strip()
        if category_name:
            try:
                conn.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))
                conn.commit()
                flash("Category added successfully.", "success")
            except sqlite3.IntegrityError:
                flash("This category already exists.", "danger")
        return redirect(url_for("categories"))

    rows = conn.execute("SELECT * FROM categories ORDER BY category_name").fetchall()
    conn.close()
    return render_template("categories.html", categories=rows)


@app.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
def delete_category(category_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
        conn.commit()
        flash("Category deleted successfully.", "success")
    except sqlite3.IntegrityError:
        flash("This category is used by products. Delete related products first.", "danger")
    finally:
        conn.close()
    return redirect(url_for("categories"))


@app.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():
    conn = get_db_connection()
    if request.method == "POST":
        conn.execute(
            """
            INSERT INTO suppliers (supplier_name, phone, email, address)
            VALUES (?, ?, ?, ?)
            """,
            (
                request.form.get("supplier_name", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("address", "").strip(),
            ),
        )
        conn.commit()
        flash("Supplier added successfully.", "success")
        return redirect(url_for("suppliers"))

    rows = conn.execute("SELECT * FROM suppliers ORDER BY supplier_name").fetchall()
    conn.close()
    return render_template("suppliers.html", suppliers=rows)


@app.route("/suppliers/<int:supplier_id>/delete", methods=["POST"])
@login_required
def delete_supplier(supplier_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,))
        conn.commit()
        flash("Supplier deleted successfully.", "success")
    except sqlite3.IntegrityError:
        flash("This supplier is used by products. Delete related products first.", "danger")
    finally:
        conn.close()
    return redirect(url_for("suppliers"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
