"""
darkelf_pq.py

Centralized Post-Quantum state manager for Darkelf Shadow.
Designed to replace scattered PQ logic from interceptor.py/utils.py.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time


def darkelf_pq_fingerprint(url: str, headers: dict | None = None, seed: bytes | None = None) -> str:
    h = hashlib.sha3_512()
    h.update(url.encode("utf-8", errors="ignore"))

    if headers:
        for k, v in sorted(headers.items()):
            h.update(str(k).encode())
            h.update(str(v).encode())

    h.update(str(int(time.time() // 10)).encode())

    if seed:
        h.update(seed)

    return h.hexdigest()


def darkelf_pq_chain(seed: bytes, url: str, counter: int) -> bytes:
    h = hashlib.sha3_512()
    h.update(seed)
    h.update(url.encode("utf-8", errors="ignore"))
    h.update(counter.to_bytes(8, "big"))
    return h.digest()


def darkelf_pq_mix(url: str) -> str:
    nonce = secrets.token_hex(8)
    return hashlib.sha3_512(
        (url + nonce + str(time.time())).encode()
    ).hexdigest()


def darkelf_hkdf_sha3(key: bytes, salt=b"darkelf", info=b"pq-layer") -> bytes:
    prk = hmac.new(salt, key, hashlib.sha3_512).digest()
    return hmac.new(prk, info, hashlib.sha3_512).digest()


class DarkelfPQ:
    """Central PQ state container."""

    def __init__(self):
        self.tab_seeds: dict[str, bytes] = {}
        self.counters: dict[str, int] = {}
        self.canvas_seeds: dict[str, int] = {}
        self.seen: set[str] = set()
        self.chain: str | None = None
        
        self.initialize()
        
    def initialize(self):
        seed = secrets.token_bytes(32)
        self.chain = hashlib.sha3_512(seed).hexdigest()
        self.counters["boot"] = 1
        self.tab_seeds["boot"] = seed

    def get_tab_seed(self, tab_id: str) -> bytes:
        if tab_id not in self.tab_seeds:
            self.tab_seeds[tab_id] = secrets.token_bytes(32)
        return self.tab_seeds[tab_id]

    def update_chain(self, tab_id: str, url: str):
        seed = self.get_tab_seed(tab_id)
        counter = self.counters.get(tab_id, 0)

        self.chain = hashlib.sha3_512(
            seed +
            url.encode("utf-8", errors="ignore") +
            counter.to_bytes(8, "big")
        ).hexdigest()

        self.counters[tab_id] = counter + 1
        self.canvas_seeds[tab_id] = int.from_bytes(seed[:4], "big")

    def canvas_seed(self, tab_id: str) -> int:
        return self.canvas_seeds.get(tab_id, 0)

    def observe(self, url: str, request_type: str | None, seed: bytes):
        if not self.chain:
            return

        if request_type not in ("xmlhttprequest", "subdocument", "media"):
            return

        fp = darkelf_pq_fingerprint(url, seed=seed)
        self.seen.add(fp)

        if len(self.seen) > 5000:
            self.seen = set(list(self.seen)[-2500:])

    def status(self):
        if sum(self.counters.values()) <= 1:
            return "standby"
        return "active"
        
    def destroy(self):
        """
        Destroy all session-only Quantum state.

        This removes references to transient cryptographic state so it
        becomes eligible for garbage collection. No state is persisted.
        """

        self.tab_seeds.clear()
        self.canvas_seeds.clear()
        self.counters.clear()
        self.seen.clear()

        self.chain = None
        
    def reset(self):
        """
        Destroy existing state and begin a new Quantum session.
        """

        self.destroy()
        self.initialize()
