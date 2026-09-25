import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

import product_image_cache as images


class ProductImageCacheTests(unittest.TestCase):
    def test_rejects_unapproved_or_insecure_hosts(self):
        for url in (
            "http://www.jib.co.th/picture.jpg",
            "https://eviljib.co.th/picture.jpg",
            "https://www.jib.co.th.evil.test/picture.jpg",
            "https://127.0.0.1/picture.jpg",
            "https://user@www.jib.co.th/picture.jpg",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                images.validated_host(url)
        self.assertEqual(images.validated_host(
            "https://img.advice.co.th/product.jpg"), "img.advice.co.th")

    def test_downloads_real_image_and_reuses_local_copy(self):
        url = "https://www.jib.co.th/img_master/product/one.jpg"
        jpeg = b"\xff\xd8\xff" + b"test-image" * 10
        calls = []

        def handler(request):
            calls.append(request.url)
            return httpx.Response(200, content=jpeg,
                                  headers={"content-type": "image/jpeg"})

        async def check():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                first = await images.fetch_image(url, client)
                second = await images.fetch_image(url, client)
                self.assertEqual(first, second)
                self.assertEqual(first[0].read_bytes(), jpeg)
                self.assertEqual(first[1], "image/jpeg")

        with TemporaryDirectory() as temp, patch.object(images, "CACHE_DIR", Path(temp)):
            asyncio.run(check())
        self.assertEqual(len(calls), 1)

    def test_rejects_html_disguised_as_image(self):
        url = "https://ihavecpu.com/image.jpg"

        async def check():
            transport = httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=b"<html>blocked</html>",
                    headers={"content-type": "image/jpeg"},
                )
            )
            async with httpx.AsyncClient(transport=transport) as client:
                with self.assertRaisesRegex(ValueError, "non-image"):
                    await images.fetch_image(url, client)

        with TemporaryDirectory() as temp, patch.object(images, "CACHE_DIR", Path(temp)):
            asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
