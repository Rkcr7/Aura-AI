"""Helpers for resolving usable API keys from ai_providers.json entries.

ai_providers.example.json ships BOTH an ``apiKey`` field and a populated
``apiKeys`` array, every entry a placeholder ("YOUR_GROQ_API_KEY_1", ...).
Without filtering, a user who fills in only ``apiKey`` still gets the untouched
placeholder array as the rotation pool, so every request fails with a 401.
"""

from typing import Any, Dict, List, Optional, Sequence

# Placeholder shapes used by ai_providers.example.json and the README samples.
_PLACEHOLDER_PREFIXES = ("YOUR_", "YOUR-")
_PLACEHOLDER_EXACT = frozenset({"CHANGEME", "CHANGE_ME", "PLACEHOLDER"})


def is_placeholder_key(key: Any) -> bool:
    """Return True when *key* is missing, blank or an obvious template value."""
    if not isinstance(key, str):
        return True
    cleaned = key.strip()
    if not cleaned:
        return True
    upper = cleaned.upper()
    return upper in _PLACEHOLDER_EXACT or upper.startswith(_PLACEHOLDER_PREFIXES)


def usable_keys(keys: Optional[Sequence[Any]]) -> List[str]:
    """Return a new list with the stripped entries of *keys* that look real."""
    if not keys or not isinstance(keys, (list, tuple)):
        return []
    return [key.strip() for key in keys if not is_placeholder_key(key)]


def resolve_provider_keys(provider_config: Dict[str, Any]) -> List[str]:
    """Resolve the key rotation pool for one ai_providers.json provider entry.

    Prefers the ``apiKeys`` array and falls back to the single ``apiKey`` field
    when the array holds nothing usable. Returns ``[]`` when neither is set.
    """
    if not isinstance(provider_config, dict):
        return []
    return (usable_keys(provider_config.get("apiKeys"))
            or usable_keys([provider_config.get("apiKey")]))
