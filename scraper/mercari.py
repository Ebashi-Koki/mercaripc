"""メルカリで販売中のゲーミングデスクトップPCを集める。"""
import asyncio

from mercapi import Mercapi
from mercapi.requests import SearchRequestData as S

GAMING_DESKTOP = 10713  # カテゴリ: スマホ・タブレット・パソコン > ゲーミングPC > ゲーミングデスクトップ
QUERIES = ["", "RTX", "GeForce", "Radeon", "ゲーミングPC"]


async def search_items(price_min=20000, pages_per_query=6, sleep=1.0):
    api = Mercapi()
    items = {}
    for query in QUERIES:
        res = await api.search(
            query,
            categories=[GAMING_DESKTOP],
            status=[S.Status.STATUS_ON_SALE],
            sort_by=S.SortBy.SORT_CREATED_TIME,
            price_min=price_min,
        )
        for _ in range(pages_per_query):
            for it in res.items:
                items.setdefault(it.id_, it)
            if not res.meta.next_page_token:
                break
            await asyncio.sleep(sleep)
            res = await res.next_page()
        await asyncio.sleep(sleep)
    return list(items.values())


async def fetch_descriptions(items, cache, limit=150, sleep=0.7):
    """説明文を取得する（cache: id -> 説明文。取得済みは再取得しない）。"""
    fetched = 0
    for it in items:
        if it.id_ in cache or fetched >= limit:
            continue
        try:
            detail = await it.full_item()
            cache[it.id_] = getattr(detail, "description", "") or ""
        except Exception as e:  # 1件の失敗で全体を止めない
            print(f"description failed {it.id_}: {e}")
        fetched += 1
        await asyncio.sleep(sleep)
    return cache
