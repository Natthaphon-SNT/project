# Advice catalogue import

`advice_full_scraper.py` imports all products from the 17 distinct Advice category links requested for this project, including Mainboard. The duplicate CPU link is only crawled once. It uses Advice's public guest catalogue endpoint, makes one paced request at a time, backs off on transient failures, and stops on access-denied/rate-limit responses. It does not require an account.

From `backend/`:

```powershell
python -B -u -X utf8 advice_full_scraper.py --interval 1.5
```

Re-running this command resumes unfinished listing pages and product details. To refresh the live catalogue from page one, use `--refresh-listings`; existing full specifications and images are retained when the product URL is unchanged. `--list-only` and `--details-only` split the stages, and `--categories cpu power-supply` limits either stage to selected source categories. The complete run updates `products` and refreshes compatibility knowledge. Use `--skip-compat-training` only when running a partial/import test.

`shop.db` contains:

- `advice_scrape_inventory`: one row per Advice source code, including product URL, first image, all image URLs as JSON, flattened detail text, structured specification groups as JSON, final category, and link to `products`.
- `advice_scrape_membership`: every requested source category containing a product, even when a product also appears in another category.
- `advice_scrape_category_audit`: resumable page offsets, counts, and completion state.

The storefront's normal `products` table receives the current price, category, detail text, primary image, and Advice product link. Monitor and headset subtypes have their own visible categories. Advice's own subcategory URLs separate liquid/air cooling, case fans, thermal compound, GPU holders, case accessories, in-ear headphones, and true-wireless earbuds; the latter accessories are kept out of PC Builder hardware slots.

An absent specification or image at the source is marked `missing` in inventory; it is never fabricated. A later run retries these records. Image URLs are stored in inventory, and the separate `prefetch_product_images.py` task downloads validated images to the local cache for reliable display.
