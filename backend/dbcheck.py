import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
jib   = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
ihc   = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
imgs  = cur.execute("SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url)>5").fetchone()[0]
print(f'total={total} jib={jib} ihc={ihc} imgs={imgs}')
schema = cur.execute("SELECT sql FROM sqlite_master WHERE name='products'").fetchone()[0]
print('UNIQUE fields in schema:', 'product_id' in schema, 'p_name' in schema)
# Check UNIQUE constraint
has_unique_pname = 'UNIQUE' in schema.upper() and 'p_name' in schema.lower()
print('UNIQUE on p_name?', has_unique_pname)
print()
# Test insert manually
try:
    cur.execute('''INSERT OR IGNORE INTO products
        (product_id,p_name,p_description,p_price,price_advice,price_jib,price_ihavecpu,
         p_stock,cid,category,img_url,specs,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        ('test_001','TEST PRODUCT SCRAPER','',9999,0,5000,0,99,'c03','GPU',
         'https://test.com/img.jpg','','2025-01-01'))
    conn.commit()
    check = cur.execute("SELECT product_id FROM products WHERE product_id='test_001'").fetchone()
    print('Test insert result:', check)
    cur.execute("DELETE FROM products WHERE product_id='test_001'")
    conn.commit()
    print('Test passed - inserts work')
except Exception as e:
    print('Insert error:', e)
conn.close()
