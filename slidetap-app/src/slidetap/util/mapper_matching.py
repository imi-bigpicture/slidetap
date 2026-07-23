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

"""Shared classifier for mapping expressions.

Used by both the database model (to populate ``DatabaseMappingItem.literal`` at
write time) and the mapper service (historically; now the classification lives
entirely at write time, see ``DatabaseMappingItem``). Lives outside both layers
since the model must not import from ``services``.
"""

import re


def literal_key(expression: str) -> str | None:
    """Return the one string ``expression`` matches exactly under ``re.match``.

    Mapper resolution matches values with ``re.match(expression, value)``
    (anchored at the start only). An expression therefore matches exactly one
    string when it is a start/end-anchored plain literal — e.g. the
    ``^<concept-id>$`` keys that dominate the Diagnose mapper — which lets it
    be resolved by an indexed lookup instead of a regex scan.

    Returns the literal for such expressions, or ``None`` when the expression
    carries any regex machinery (``.*resectie.*``, ``^HE[0-9]*``, …) and must go
    through a regex scan. The check is deliberately conservative: anything it
    is not certain is a plain literal falls back to the regex path, so it can
    never turn a genuine regex into a wrong exact match.
    """
    body = expression[1:] if expression.startswith("^") else expression
    if not body.endswith("$"):
        # Without an end anchor, re.match is a prefix match, not an exact one.
        return None
    body = body[:-1]
    # re.escape is a no-op only for strings with no regex metacharacters; if it
    # changed anything (including a trailing backslash escaping our ``$``), the
    # expression is a genuine regex.
    if body == "" or re.escape(body) != body:
        return None
    return body
