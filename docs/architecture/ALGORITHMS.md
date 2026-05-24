# Algorithms

This document describes what the AI service actually computes. Where the README says "image similarity" or "forecasting", this file shows the formula and the line of code that implements it.

## 1. Image embedding — `encode_image(bytes) → list[float]`

Source: [apps/ai_catalog/services/embedding_service.py](../../apps/ai_catalog/services/embedding_service.py).

The output is a 112-dimensional vector, L2-normalized, made of two concatenated components:

### 1.1 Perceptual hash (pHash) — 64 dimensions

```python
imagehash.phash(img, hash_size=8)
```

The `imagehash` library computes:

1. Convert the image to grayscale.
2. Resize to a 32×32 image.
3. Apply a 2D DCT and keep the top-left 8×8 block (low-frequency components).
4. Compare each value to the median; bit = 1 if above, 0 if below.

This yields 64 bits, which we cast to a `float32` array of zeros and ones. pHash is robust against:

- Resizing
- Mild compression
- Small rotations / crops

…but **not** robust against major lighting changes, recolorings, or substantive content changes. That's a fundamental property of pHash, not a limitation of our wrapper.

### 1.2 HSV color histogram — 48 dimensions

```python
img → resize to 128×128 → /255 → HSV → histogram(16 bins per channel)
```

The image is resized to 128×128, normalized into `[0, 1]`, converted to HSV with a vectorized formula (`_rgb_to_hsv`), then a 16-bin histogram is computed per channel (`density=True` so each channel sums to 1). The three histograms are concatenated to a length-48 vector.

### 1.3 Normalization

The two parts are concatenated (`np.concatenate([phash, hist])`), giving 112 values. We then divide by the L2 norm so cosine similarity == dot product. If the norm is 0 (a degenerate image), we skip normalization to avoid `NaN`.

### 1.4 Cosine similarity

```python
def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

Since both vectors are already L2-normalized by `encode_image`, the divide is technically redundant but the function is also used in tests with un-normalized inputs.

### 1.5 Honest limitations

- This is **not** a learned model. It cannot distinguish "two blouses with similar floral patterns but different cuts" from "two blouses with similar floral patterns and similar cuts" any better than a coin flip — both inputs hash to nearly the same DCT block and produce similar HSV histograms.
- For the demo catalog (4 SKUs with visibly distinct color palettes), the results are sensible.
- The whole pipeline runs in ~50–100ms per image on a developer laptop. There is no need for batching or GPU.

---

## 2. Forecasting — Holt's linear (double exponential) smoothing

Source: [apps/forecasting/services/forecast_service.py](../../apps/forecasting/services/forecast_service.py).

Given a series of observations `x_0, x_1, ..., x_{n-1}`, two smoothing parameters `α, β ∈ (0, 1)`, and a horizon `h`, the algorithm maintains two state variables:

```
level_t = α x_t + (1 - α) (level_{t-1} + trend_{t-1})
trend_t = β (level_t - level_{t-1}) + (1 - β) trend_{t-1}
```

The forecast `h` steps ahead is `level_n + h × trend_n`, clamped at 0 (we never forecast negative demand).

The current implementation hard-codes `α=0.6, β=0.2`. Both are inputs to `forecast_series` and could be exposed as request parameters; the viewset doesn't currently do so.

Edge cases:

- `n = 0`: returns an empty list.
- `n = 1`: returns the single value repeated `horizon` times. There is no trend signal to fit yet.

The output is rounded to 4 decimal places only when stored (DynamoDB receives strings); the response casts back to `float`.

---

## 3. Customer clustering — KMeans on standardized RFM

Source: [apps/clustering/services/clustering_service.py](../../apps/clustering/services/clustering_service.py).

### 3.1 Features

For each customer `i`, three numbers:

- `recency_days`: days since last purchase (a low number means recent).
- `frequency`: number of confirmed sales attributed to this customer.
- `monetary`: total spent (in `BOB`).

These are RFM features in the classical e-commerce sense.

### 3.2 Standardization

Before clustering, each column is standardized:

```
x_ij' = (x_ij - mean(x_j)) / std(x_j)    # with std=1 substituted for any zero-std column
```

Without this, `monetary` (often in the thousands) would dominate the distance metric and recency / frequency would barely affect cluster assignment.

### 3.3 KMeans

```python
KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(x)
```

`n_init=10` runs the algorithm 10 times from different random seeds and keeps the lowest-inertia result. `random_state=42` makes runs reproducible for a given input set.

If the caller passes `n < k`, the service silently lowers `k` to `n` so KMeans doesn't error.

### 3.4 Outputs

For each customer: cluster label (`0..k-1`) and Euclidean distance to its centroid (in the standardized space). The centroid distances are useful for:

- Identifying borderline cases (large distance ⇒ poor fit).
- Sorting "most representative" customers per cluster.

Cluster labels themselves are arbitrary — cluster `0` in one run isn't the same group as cluster `0` in another. If you need consistent labels across runs, you must align them yourself (e.g., re-label by ascending mean monetary).

### 3.5 What this is not

- It is **not** an online clustering. Every run is a fresh KMeans on the input batch.
- It is **not** a recommender. The clusters describe purchase behavior, not preferences over products.
- The `cluster_runs` table stores the metadata of each run but **does not store centroids**, so you cannot retroactively reproduce a past run's assignment without keeping the input.
