import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
# Show full schema
schema = cur.execute("SELECT sql FROM sqlite_master WHERE name='products'").fetchone()[0]
print(schema)
print()
# Check if p_name UNIQUE might be the culprit
# Try inserting same p_name with different product_id
try:
    cur.execute('''INSERT OR IGNORE INTO products
        (product_id,p_name,p_description,p_price,price_ihavecpu,p_stock,cid,category,img_url,specs,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        ('testa','GPU RTX TEST A','',9999,5000,99,'c03','GPU','https://a.com/img.jpg','','2025-01-01'))
    cur.execute('''INSERT OR IGNORE INTO products
        (product_id,p_name,p_description,p_price,price_ihavecpu,p_stock,cid,category,img_url,specs,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        ('testb','GPU RTX TEST B','',9999,5000,99,'c03','GPU','https://b.com/img.jpg','','2025-01-01'))
    conn.commit()
    rows = cur.execute("SELECT product_id, p_name FROM products WHERE product_id IN ('testa','testb')").fetchall()
    print('Inserted both:', rows)
    cur.execute("DELETE FROM products WHERE product_id IN ('testa','testb')")
    conn.commit()
except Exception as e:
    print('Error:', e)
conn.close()
