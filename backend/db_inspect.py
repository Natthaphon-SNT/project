import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
c = conn.cursor()
print(f"Total products: {c.execute('SELECT COUNT(*) FROM products').fetchone()[0]}")
print(f"Total JIB: {c.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]}")
print(f"Total IHC: {c.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]}")
print(f"Total Advice: {c.execute('SELECT COUNT(*) FROM products WHERE price_advice > 0').fetchone()[0]}")
print("\nUnique store combinations:")
both = c.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0 AND price_ihavecpu > 0').fetchone()[0]
print(f"  JIB + IHC: {both}")
conn.close()
