#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Benchmark the mapper resolver fast path (Nexus #46).

Compares the pre-#46 linear regex scan against ``MapperExpressionIndex`` at the
Diagnose-mapper scale (~6k exact keys + a few genuine regex keys). Pure
in-memory: it isolates the resolver algorithm this change fixes. Separately, the
live resolver now reads a mapper's expressions once per mapper (cached) instead
of once per value — a further large saving not modelled here.

Run:  uv run python benchmarks/bench_mapper_resolver.py
"""

from __future__ import annotations

import random
import time

from slidetap.services.mapper_service import MapperExpressionIndex, MapperService

N_EXACT = 6173
REGEX_KEYS = [".*resectie.*", "^HE[0-9]*", ".*biopt.*"]
N_LOOKUPS = 2000
WORKBOOK_ROWS = 30_000


def build_expressions() -> list[str]:
    exact = [f"^{100000 + i}$" for i in range(N_EXACT)]
    return exact + REGEX_KEYS


def old_linear_scan(expressions: list[str], value: str) -> str | None:
    return next(
        (e for e in expressions if MapperService.create_pattern(e).match(value)),
        None,
    )


def main() -> None:
    expressions = build_expressions()
    rng = random.Random(42)  # noqa: S311 - reproducible sampling, not cryptographic
    # Representative lookups: existing exact concept-ids (the common case).
    values = [str(100000 + rng.randrange(N_EXACT)) for _ in range(N_LOOKUPS)]

    MapperService.create_pattern.cache_clear()
    start = time.perf_counter()
    for value in values:
        old_linear_scan(expressions, value)
    old_per = (time.perf_counter() - start) / len(values)

    MapperService.create_pattern.cache_clear()
    start = time.perf_counter()
    index = MapperExpressionIndex.build(expressions)
    build_time = time.perf_counter() - start
    start = time.perf_counter()
    for value in values:
        index.resolve(value, MapperService.create_pattern)
    new_per = (time.perf_counter() - start) / len(values)

    print(
        f"expressions: {len(expressions)} "
        f"({N_EXACT} exact + {len(REGEX_KEYS)} regex), lookups: {len(values)}"
    )
    print(f"index build: {build_time * 1e3:.1f} ms (once per mapper)\n")
    print(f"{'':<6}{'per value':>14}{'30k workbook':>16}")
    print(f"{'OLD':<6}{old_per * 1e3:>11.3f} ms{old_per * WORKBOOK_ROWS:>13.1f} s")
    print(f"{'NEW':<6}{new_per * 1e6:>11.1f} us{new_per * WORKBOOK_ROWS:>13.3f} s")
    print(f"\nspeedup: {old_per / new_per:.0f}x")


if __name__ == "__main__":
    main()
