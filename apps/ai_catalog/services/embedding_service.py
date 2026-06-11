"""Image embeddings.

The boutique team does not need a heavy CV model on every request; for the
academic delivery we ship a deterministic feature vector built from two
production-proven signals:

1. Perceptual hash (pHash) — robust against resizing/compression.
2. HSV color histogram (16 bins per channel = 48 dims).

The result is a 64+48 = 112-dim float vector that survives JSON round-trips
and can be compared with cosine similarity. An interface seam (``encode_image``)
makes it trivial to swap in a ResNet/CLIP backbone later without touching the
similarity service.
"""

from __future__ import annotations

import io
from typing import List

import imagehash
import numpy as np
from PIL import Image


def _phash_bits(img: Image.Image) -> np.ndarray:
    h = imagehash.phash(img, hash_size=8)  # 8x8 = 64 bits
    bits = np.array(h.hash, dtype=np.float32).flatten()  # 64 dims, 0/1
    return bits


def _color_histogram(img: Image.Image) -> np.ndarray:
    rgb = img.convert("RGB").resize((128, 128))
    arr = np.array(rgb, dtype=np.float32) / 255.0
    hsv = _rgb_to_hsv(arr)
    bins_per = 16
    hist = []
    for c in range(3):
        h, _ = np.histogram(hsv[..., c], bins=bins_per, range=(0.0, 1.0), density=True)
        hist.append(h.astype(np.float32))
    return np.concatenate(hist, axis=0)


def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """Vectorized RGB->HSV. rgb in [0,1]."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-9), 0.0)
    rc = np.where(delta > 0, (maxc - r) / np.maximum(delta, 1e-9), 0.0)
    gc = np.where(delta > 0, (maxc - g) / np.maximum(delta, 1e-9), 0.0)
    bc = np.where(delta > 0, (maxc - b) / np.maximum(delta, 1e-9), 0.0)
    h = np.where(maxc == r, bc - gc, np.where(maxc == g, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (h / 6.0) % 1.0
    return np.stack([h, s, v], axis=-1)


def encode_image(image_bytes: bytes) -> List[float]:
    """Return the 112-dim L2-normalized embedding for the given image."""
    img = Image.open(io.BytesIO(image_bytes))
    img.load()
    phash = _phash_bits(img)
    hist = _color_histogram(img)
    vec = np.concatenate([phash, hist], axis=0)
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return [float(x) for x in vec.tolist()]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Return the cosine similarity of two equal-length embedding vectors."""
    if len(a) != len(b):
        raise ValueError("embedding dimension mismatch")
    av = np.array(a, dtype=np.float32)
    bv = np.array(b, dtype=np.float32)
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(av, bv) / (na * nb))
