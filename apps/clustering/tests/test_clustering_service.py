from apps.clustering.services.clustering_service import ClusteringService, CustomerFeatures


def test_separates_two_obvious_groups():
    svc = ClusteringService()
    rows = [
        CustomerFeatures("a1", recency_days=1, frequency=20, monetary=5000),
        CustomerFeatures("a2", recency_days=2, frequency=22, monetary=5200),
        CustomerFeatures("a3", recency_days=3, frequency=19, monetary=4800),
        CustomerFeatures("b1", recency_days=200, frequency=1, monetary=100),
        CustomerFeatures("b2", recency_days=180, frequency=1, monetary=120),
        CustomerFeatures("b3", recency_days=220, frequency=2, monetary=80),
    ]
    segments = svc.fit_segments(rows, k=2)
    cluster_a = {s.cluster for s in segments if s.customer_id.startswith("a")}
    cluster_b = {s.cluster for s in segments if s.customer_id.startswith("b")}
    assert len(cluster_a) == 1
    assert len(cluster_b) == 1
    assert cluster_a != cluster_b


def test_returns_empty_for_empty_input():
    svc = ClusteringService()
    assert svc.fit_segments([], k=4) == []
