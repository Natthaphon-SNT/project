import sqlite3
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
for store in ['advice', 'jib', 'ihavecpu']:
    url_col = 'url_' + store
    price_col = 'price_' + store
    desc_col = 'desc_' + store
    cur.execute("SELECT COUNT(*) FROM products WHERE " + url_col + " != '' AND " + url_col + " IS NOT NULL AND " + price_col + " > 0")
    with_url = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM products WHERE " + price_col + " > 0")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM products WHERE " + desc_col + " != '' AND " + desc_col + " IS NOT NULL AND " + price_col + " > 0")
    has_desc = cur.fetchone()[0]
    print(store + ': total=' + str(total) + ', with_url=' + str(with_url) + ', has_desc=' + str(has_desc))
conn.close()
