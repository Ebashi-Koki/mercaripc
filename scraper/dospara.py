"""ドスパラ買取（cts.dospara.co.jp）の CPU / ビデオカード買取上限価格を取得する。"""
import html
import re
import statistics
import time

import httpx

from .parts import base_cpu_key, find_cpus, find_gpus

BASE = "https://cts.dospara.co.jp/buy/search.php"
CATEGORIES = {
    "cpu": {"br": 21, "cbr": 2101},
    "gpu": {"br": 21, "cbr": 2105, "sbr": 2105001},
}
ROW_RE = re.compile(
    r'<li class="name_col" title="([^"]*)">.*?<li class="price_col">([\d,]+)円', re.S
)
MIN_PRICE = 1000  # これより安いものは古すぎるので取得を打ち切る
HEADERS = {"User-Agent": "Mozilla/5.0 (mercaripc price checker)"}


def fetch_rows(kind, max_pages=60, sleep=1.0):
    rows = []
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            params = {**CATEGORIES[kind], "op": 50, "sc": "KAIAMT_MAX_DESC", "page": page}
            res = client.get(BASE, params=params)
            res.raise_for_status()
            page_rows = [
                (html.unescape(name), int(price.replace(",", "")))
                for name, price in ROW_RE.findall(res.text)
            ]
            if not page_rows:
                break
            rows.extend(page_rows)
            if page_rows[-1][1] < MIN_PRICE:
                break
            time.sleep(sleep)
    return rows


def build_table(rows, finder):
    """型番キー -> {price(中央値), min, max, n, sample} の辞書を作る。"""
    groups = {}
    for name, price in rows:
        # 品名のカッコ内に型番が書かれていることが多いのでカッコ内を優先
        inner = " ".join(re.findall(r"\(([^)]*)\)", name))
        keys = finder(inner) or finder(name)
        if not keys:
            continue
        groups.setdefault(keys[0], []).append((price, name))
    table = {}
    for key, items in groups.items():
        prices = [p for p, _ in items]
        table[key] = {
            "price": int(statistics.median(prices)),
            "min": min(prices),
            "max": max(prices),
            "n": len(prices),
            "sample": max(items)[1],
        }
    return table


def fetch_prices():
    return {
        "cpu": build_table(fetch_rows("cpu"), find_cpus),
        "gpu": build_table(fetch_rows("gpu"), find_gpus),
    }


def lookup_cpu(table, key):
    """完全一致が無ければ末尾記号を外した型番の最安値で近似する。"""
    if key in table:
        return table[key], False
    base = base_cpu_key(key)
    candidates = [v for k, v in table.items() if base_cpu_key(k) == base]
    if candidates:
        return min(candidates, key=lambda v: v["price"]), True
    return None, False
