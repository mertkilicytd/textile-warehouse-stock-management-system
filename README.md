# Textile Warehouse Stock Management System

A simple web-based warehouse stock management system for a textile company.

The project is designed for the Applied SQL course milestone. Warehouse employees can log in, add products, manage product variants, update stock with entry/exit movements, and monitor low-stock product variants.

Video Link: https://drive.google.com/file/d/17K6Pj_9K0w2cLW7UqGSvNxvm7xI_Xy_S/view?usp=drive_link

## Project Scope

The system follows the database structure in the milestone report:

- `employees`
- `categories`
- `suppliers`
- `products`
- `product_variants`
- `stock_movements`

## Technologies

- Python
- Flask
- SQLite
- HTML
- CSS

## Main Features

- Employee login system
- Dashboard with stock summary
- Product CRUD operations
- Product variant CRUD operations
- Category management
- Supplier management
- Stock entry and stock exit records
- Automatic stock quantity update after stock movement
- Low-stock product list
- SQL joins and aggregate queries in dashboard/list pages

## How to Run

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

macOS / Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Demo Login

```text
Username: admin
Password: admin123
```

## Database Design Summary

### employees
Stores warehouse employee login and identification information.

### categories
Stores textile product categories such as T-Shirt, Pants, Jacket, Shirt.

### suppliers
Stores supplier company information.

### products
Stores general product information such as product name, brand, category, supplier, and price.

### product_variants
Stores product size and color combinations. Stock is tracked at variant level.

### stock_movements
Stores stock entry and exit operations. Each movement is connected to an employee and a product variant.

## Relationships

- One category can have many products.
- One supplier can provide many products.
- One product can have many product variants.
- One product variant can have many stock movements.
- One employee can perform many stock movements.

## Sample SQL Queries

### Low stock products

```sql
SELECT p.product_name, pv.size, pv.color, pv.stock_quantity
FROM product_variants pv
JOIN products p ON pv.product_id = p.product_id
WHERE pv.stock_quantity < 10;
```

### Product list with category and supplier

```sql
SELECT p.product_name, c.category_name, s.supplier_name, p.brand, p.price
FROM products p
JOIN categories c ON p.category_id = c.category_id
JOIN suppliers s ON p.supplier_id = s.supplier_id;
```

### Stock movement history

```sql
SELECT sm.movement_type, sm.quantity, sm.movement_date,
       e.full_name, p.product_name, pv.size, pv.color
FROM stock_movements sm
JOIN employees e ON sm.employee_id = e.employee_id
JOIN product_variants pv ON sm.variant_id = pv.variant_id
JOIN products p ON pv.product_id = p.product_id
ORDER BY sm.movement_date DESC;
```

## Suggested Git Commits

```bash
git add .
git commit -m "Create Flask project structure"

git add .
git commit -m "Add SQLite database schema and seed data"

git add .
git commit -m "Implement product and stock management pages"

git add .
git commit -m "Add low stock report and final styling"
```
