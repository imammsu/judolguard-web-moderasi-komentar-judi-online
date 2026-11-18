"""Uji Part 1: endpoint /health, error JSON, prepare(), rules, dan klasifikasi satu array."""

import time

from app.ml import get_registry
from app.ml.normalizer import prepare
from app.ml.rules import check_rule_hit

EXPECTED_HASH = "4a078a0c99576d727a8c6660334d91d5c9c209800bb21f896a02f8c7e1b8e214"


# ---------- /health ----------
def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "ok"
    assert data["ml"]["model_loaded"] is True
    assert data["ml"]["sklearn_version"] == "1.6.1"
    assert data["ml"]["sklearn_version_match"] is True
    assert data["ml"]["normalizer_hash"] == EXPECTED_HASH
    assert data["ml"]["normalizer_match"] is True
    assert data["ml"]["thresholds"]["t_high"] == 0.5
    assert data["database"]["mode"] == "session_pooler"


def test_api_health_alias(client):
    assert client.get("/api/health").status_code == 200


def test_unknown_api_route_returns_json_404(client):
    res = client.get("/api/tidak-ada")
    assert res.status_code == 404
    body = res.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "not_found"


# ---------- prepare() ----------
def test_prepare_unicode_and_brand_mask():
    assert "brandtoken" in prepare("Main di 𝗚𝗔𝗖𝗢𝗥77 pasti maxwin")


def test_prepare_spaced_letters():
    assert "gacor" in prepare("g a c o r")


def test_prepare_url_and_phone_tokens():
    out = prepare("cek www.situsku.com atau wa 0812-3456-7890")
    assert "urltoken" in out
    assert "phonetoken" in out


# ---------- rules ----------
def test_rule_hits_brandless_ads():
    assert check_rule_hit("info link gacor ketik di google ya")
    assert check_rule_hit("bonus chip gratis buat member baru")
    assert check_rule_hit("hubungi WA 081234567890 daftar dapat bonus")


def test_rule_ignores_normal_comment():
    assert not check_rule_hit("videonya bagus banget, makasih tutorialnya bang")


# ---------- klasifikasi satu array ----------
def test_classify_array_zones_and_dedup():
    reg = get_registry()
    texts = [
        "PULAUWIN gacor hari ini, deposit 10rb langsung maxwin! daftar sekarang",
        "videonya bagus banget, makasih tutorialnya bang",
        "videonya bagus banget, makasih tutorialnya bang",
        "info link gacor ketik di google",
    ]
    results = reg.classify_array(texts)
    assert len(results) == len(texts)
    assert results[0].zone == "judol"
    assert results[1].zone == "bukan"
    # Duplikat menerima hasil yang identik
    assert results[1] == results[2]
    # Aturan minimal menaikkan iklan tanpa brand ke "review"
    assert results[3].zone in ("review", "judol")
    for r in results:
        assert 0.0 <= r.score <= 1.0
        assert len(r.text_hash) == 64


def test_classify_array_empty():
    assert get_registry().classify_array([]) == []


def test_classify_1000_comments_under_10_seconds():
    texts = [f"komentar normal nomor {i} videonya keren" for i in range(990)]
    texts += ["SGI88 slot gacor wd berapapun dibayar"] * 10
    start = time.perf_counter()
    results = get_registry().classify_array(texts)
    elapsed = time.perf_counter() - start
    assert len(results) == 1000
    assert elapsed < 10
