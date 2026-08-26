content = open(r'C:\Users\Acer\.gemini\antigravity-ide\brain\701d4c68-6d41-48ca-bf49-61c970e2b9db\.system_generated\steps\112\content.md', encoding='utf-8', errors='replace').read()

patterns = ['main_img', 'bigimage', 'product-info', 'product_detail', 'detail_spec', 'tab-content', 'slick-slide', 'product-pic']
for p in patterns:
    idx = content.find(p)
    if idx >= 0:
        print(f'Found: {p} at pos {idx}')
        print(content[idx-200:idx+400])
        print('---')
    else:
        print(f'NOT FOUND: {p}')
