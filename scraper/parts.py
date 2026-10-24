"""商品名・説明文から GPU / CPU の型番を抜き出して正規化する。"""
import re
import unicodedata

_B = r"(?<![0-9A-Z])"  # 左側の境界
_E = r"(?![0-9A-Z])"  # 右側の境界

GPU_PATTERNS = [
    # RTX4070 SUPER / RTX 4070Ti / 4070S など。RTX4060 Laptop のようなノート向けは右境界で弾く
    (re.compile(_B + r"(RTX|GTX)\s*-?\s*(\d{3,4})\s*(TI\s*SUPER|TI|SUPER|S)?" + _E), "nvidia"),
    (re.compile(_B + r"(?:RX|RADEON\s*RX|RADEON)\s*-?\s*(\d{3,4})\s*(XTX|XT|GRE)?" + _E), "amd"),
    (re.compile(_B + r"ARC\s*([AB]\d{3})" + _E), "intel"),
]

CPU_PATTERNS = [
    (re.compile(_B + r"RYZEN\s*[3579]?\s*-?\s*(\d{4})\s*(X3D|XT|X|GT|GE|G|F)?" + _E), "ryzen"),
    (re.compile(_B + r"R[3579]\s*-?\s*(\d{4})\s*(X3D|XT|X|GT|GE|G|F)?" + _E), "ryzen"),
    (re.compile(_B + r"ULTRA\s*([3579])\s*-?\s*(\d{3})\s*(KF|K|F|T)?" + _E), "ultra"),
    (re.compile(_B + r"I([3579])\s*-?\s*(\d{4,5})\s*(KS|KF|K|F|T)?" + _E), "core"),
]


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").upper()


def _gpu_key(m, kind):
    if kind == "nvidia":
        suffix = re.sub(r"\s+", "", m.group(3) or "")
        if suffix == "S":
            suffix = "SUPER"
        return f"{m.group(1)}{m.group(2)}{suffix}"
    if kind == "amd":
        return f"RX{m.group(1)}{m.group(2) or ''}"
    return f"ARC{m.group(1)}"


def _cpu_key(m, kind):
    if kind == "ryzen":
        return f"RYZEN {m.group(1)}{m.group(2) or ''}"
    if kind == "ultra":
        return f"ULTRA {m.group(1)} {m.group(2)}{m.group(3) or ''}"
    return f"I{m.group(1)}-{m.group(2)}{m.group(3) or ''}"


def _find_all(text, patterns, keyfn):
    text = normalize_text(text)
    found = []
    for pattern, kind in patterns:
        for m in pattern.finditer(text):
            found.append((m.start(), keyfn(m, kind)))
    keys = []
    for _, key in sorted(found):
        if key not in keys:
            keys.append(key)
    return keys


def find_gpus(text):
    return _find_all(text, GPU_PATTERNS, _gpu_key)


def find_cpus(text):
    return _find_all(text, CPU_PATTERNS, _cpu_key)


def base_cpu_key(key):
    """末尾の K/F/X などを外したキー（完全一致が無いときの近似用）。"""
    return re.sub(r"(X3D|XT|X|GT|GE|G|F|KS|KF|K|T)$", "", key)
