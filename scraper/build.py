"""メルカリ出品とドスパラ買取価格を突き合わせて docs/data/deals.json を作る。

使い方: python -m scraper.build
"""
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from . import dospara, mercari
from .parts import find_cpus, find_gpus

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUT_DIR = ROOT / "docs" / "data"
PRICE_CACHE = CACHE_DIR / "dospara_prices.json"
DESC_CACHE = CACHE_DIR / "descriptions.json"
PRICE_MAX_AGE = 24 * 3600

EXCLUDE_RE = re.compile(r"ジャンク|故障|起動しない|動作未確認|部品取り|ケースのみ|本体のみ.*(なし|無し)|グラボ(なし|無し)|GPU(なし|無し)|空箱|レンタル")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def dospara_prices():
    cached = load_json(PRICE_CACHE, None)
    if cached and time.time() - cached.get("fetched_at", 0) < PRICE_MAX_AGE:
        return cached
    prices = dospara.fetch_prices()
    prices["fetched_at"] = time.time()
    PRICE_CACHE.write_text(json.dumps(prices, ensure_ascii=False), encoding="utf-8")
    return prices


def match_parts(title, description, prices):
    gpus = find_gpus(title) or find_gpus(description)
    cpus = find_cpus(title) or find_cpus(description)
    gpu = next(((k, prices["gpu"][k]) for k in gpus if k in prices["gpu"]), None)
    cpu, approx = None, False
    for key in cpus:
        hit, approx = dospara.lookup_cpu(prices["cpu"], key)
        if hit:
            cpu = (key, hit)
            break
    return gpu, cpu, approx, len(gpus) > 1


async def main():
    CACHE_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prices = dospara_prices()
    print(f"dospara: cpu={len(prices['cpu'])} gpu={len(prices['gpu'])}")

    items = await mercari.search_items()
    items = [it for it in items if not EXCLUDE_RE.search(it.name)]
    print(f"mercari: {len(items)} items")

    # タイトルだけでは GPU/CPU が分からないものは説明文も見る
    descs = load_json(DESC_CACHE, {})
    need = [it for it in items if not (find_gpus(it.name) and find_cpus(it.name))]
    await mercari.fetch_descriptions(need, descs)
    live_ids = {it.id_ for it in items}
    descs = {k: v for k, v in descs.items() if k in live_ids}
    DESC_CACHE.write_text(json.dumps(descs, ensure_ascii=False), encoding="utf-8")

    deals = []
    for it in items:
        desc = descs.get(it.id_, "")
        if EXCLUDE_RE.search(desc):
            continue
        gpu, cpu, approx, multi_gpu = match_parts(it.name, desc, prices)
        if not gpu:
            continue
        deals.append({
            "id": it.id_,
            "name": it.name,
            "price": it.price,
            "thumb": it.thumbnails[0] if it.thumbnails else "",
            "created": it.created.replace(tzinfo=timezone.utc).isoformat() if it.created else None,
            "condition": it.item_condition_id,
            "shipping_payer": it.shipping_payer_id,
            "gpu": {"key": gpu[0], **gpu[1]},
            "cpu": {"key": cpu[0], "approx": approx, **cpu[1]} if cpu else None,
            "multi_gpu": multi_gpu,
        })

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "dospara_fetched_at": datetime.fromtimestamp(prices["fetched_at"], timezone.utc).isoformat(),
        "count": len(deals),
        "deals": deals,
    }
    (OUT_DIR / "deals.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(deals)} deals")


if __name__ == "__main__":
    asyncio.run(main())
