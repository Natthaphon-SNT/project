import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch

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

    def test_bucket_upload_uses_same_key_as_lookup_and_signed_route(self):
        url = "https://www.jib.co.th/img_master/product/one.jpg"
        jpeg = b"\xff\xd8\xff" + b"real-image"
        stored = {}

        class MissingObject(Exception):
            response = {"Error": {"Code": "404"}}

        class Bucket:
            def head_object(self, *, Bucket, Key):
                if Key not in stored:
                    raise MissingObject()

            def put_object(self, *, Bucket, Key, Body, ContentType, CacheControl):
                stored[Key] = (Body, ContentType)

            def generate_presigned_url(self, operation, Params, ExpiresIn):
                self.head_object(Bucket=Params["Bucket"], Key=Params["Key"])
                return "https://bucket.example/signed-image"

        bucket = Bucket()
        config = {"bucket": "images"}

        async def check():
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=jpeg)
            )) as client:
                self.assertIsNone(images.get_cached_url(url))
                path, mime = await images.fetch_and_upload(url, client)
                self.assertEqual(path, images.get_cached_url(url))
                self.assertEqual(mime, "image/jpeg")
                digest = path.rsplit("/", 1)[-1]
                self.assertEqual(images.presigned_image_url(digest),
                                 "https://bucket.example/signed-image")
                self.assertEqual(stored[images._object_key(url)][0], jpeg)

        with patch.object(images, "_s3_client", return_value=(bucket, config)):
            asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
