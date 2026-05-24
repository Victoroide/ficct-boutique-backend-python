"""Unit tests for the embedding service — no Django or DynamoDB dependency."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

from apps.ai_catalog.services.embedding_service import cosine_similarity, encode_image


def _make_image(color: tuple[int, int, int], size: int = 128) -> bytes:
    img = Image.new("RGB", (size, size), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_encode_image_returns_normalized_vector():
    vec = encode_image(_make_image((200, 50, 30)))
    arr = np.array(vec, dtype=np.float32)
    assert len(vec) == 64 + 48
    assert abs(np.linalg.norm(arr) - 1.0) < 1e-3


def test_same_image_gives_high_similarity():
    img = _make_image((40, 200, 80))
    a = encode_image(img)
    b = encode_image(img)
    assert cosine_similarity(a, b) > 0.99


def test_different_color_gives_lower_similarity():
    a = encode_image(_make_image((255, 0, 0)))
    b = encode_image(_make_image((0, 0, 255)))
    assert cosine_similarity(a, b) < 0.95
