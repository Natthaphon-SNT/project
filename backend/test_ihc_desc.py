"""
Test script: ดึง description จาก ihavecpu ด้วย Playwright
ทดสอบก่อนแก้ fetch_descriptions.py จริง
"""
import asyncio
from playwright.async_api import async_playwright

URL = "https://ihavecpu.com/product/46353/mouse-(%E0%B9%80%E0%B8%A1%E0%B8%B2%E0%B8%AA%E0%B9%8C)-asus-rog-keris-ii-origin-kjp-wireless-(white)-(p727)-(2y)"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        print(f"Going to: {URL}")
        await page.goto(URL, timeout=40000, wait_until="networkidle")
        await page.wait_for_timeout(4000)

        # ─── วิธีที่ 1: ดึงตาราง spec จาก Next.js data ใน __NEXT_DATA__ ───
        print("\n=== Method 1: __NEXT_DATA__ ===")
        try:
            next_data = await page.evaluate("""
                () => {
                    const el = document.getElementById('__NEXT_DATA__');
                    if (!el) return null;
                    const data = JSON.parse(el.textContent);
                    return JSON.stringify(data).substring(0, 3000);
                }
            """)
            if next_data:
                print(next_data[:2000])
            else:
                print("No __NEXT_DATA__ found")
        except Exception as e:
            print(f"Error: {e}")

        # ─── วิธีที่ 2: ดึงตาราง spec rows ───
        print("\n=== Method 2: Spec Table Rows ===")
        try:
            specs = await page.evaluate("""
                () => {
                    // ลอง query หา table rows ที่มี spec
                    const rows = document.querySelectorAll('table tr');
                    if (rows.length > 0) {
                        return Array.from(rows).map(r => r.innerText.trim()).filter(t => t).join('\\n');
                    }
                    return null;
                }
            """)
            if specs:
                print(specs[:2000])
            else:
                print("No table rows found")
        except Exception as e:
            print(f"Error: {e}")

        # ─── วิธีที่ 3: ดึงทุก element ที่มีข้อความ "Brand" หรือ "คุณสมบัติ" ───
        print("\n=== Method 3: Find spec section by heading ===")
        try:
            result = await page.evaluate("""
                () => {
                    // หา element ที่มีข้อความ "คุณสมบัติสินค้า"
                    const allEls = document.querySelectorAll('*');
                    let specSection = null;
                    for (const el of allEls) {
                        if (el.childNodes.length === 1 && 
                            el.textContent.trim() === 'คุณสมบัติสินค้า') {
                            specSection = el;
                            break;
                        }
                    }
                    if (!specSection) return 'Not found: คุณสมบัติสินค้า heading';
                    
                    // ไปหา parent section ที่ใหญ่กว่า
                    let container = specSection.parentElement;
                    for (let i = 0; i < 5; i++) {
                        if (container && container.innerText && container.innerText.length > 100) break;
                        container = container ? container.parentElement : null;
                    }
                    
                    return {
                        heading_tag: specSection.tagName,
                        heading_class: specSection.className,
                        container_tag: container ? container.tagName : 'null',
                        container_class: container ? container.className : 'null',
                        container_text: container ? container.innerText.substring(0, 500) : 'null'
                    };
                }
            """)
            print(result)
        except Exception as e:
            print(f"Error: {e}")

        # ─── วิธีที่ 4: page.evaluate เพื่อดึง spec table โดยตรง ───
        print("\n=== Method 4: Direct spec table extraction ===")
        try:
            result = await page.evaluate("""
                () => {
                    // หา element ที่มีข้อความ "Brand" + "ASUS" (คือ row ใน spec table)
                    const allDivs = Array.from(document.querySelectorAll('div, section, article'));
                    let specDiv = null;
                    for (const div of allDivs) {
                        const text = div.innerText || '';
                        if (text.includes('Brand') && text.includes('Sensor Resolution') && 
                            text.includes('Dimensions')) {
                            // ตรวจว่า element นี้ไม่ใหญ่เกินไป
                            if (text.length < 3000) {
                                specDiv = div;
                                break;
                            }
                        }
                    }
                    if (!specDiv) return 'Spec div not found';
                    return {
                        tag: specDiv.tagName,
                        className: specDiv.className,
                        text: specDiv.innerText.substring(0, 1000),
                        innerHTML_sample: specDiv.innerHTML.substring(0, 500)
                    };
                }
            """)
            print(result)
        except Exception as e:
            print(f"Error: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
