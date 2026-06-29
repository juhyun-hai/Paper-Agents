"""
HAI lab_bonus scoring — extracted from the featured_score v4 formula in
``backend/scripts/daily_cron.py`` so the same logic can be re-used and unit
tested independently of cron.

Original inline formula (see daily_cron.py):

    lab_bonus = 0.0
    if is_member:
        lab_bonus += 5.0
    lab_bonus += min(hai_kw, 5) * 1.5  # keyword cap +7.5
    lab_bonus = min(lab_bonus, 12.5)

The function below preserves that exact behavior. ``authors`` is accepted
purely for ergonomics (callers usually have it on hand) but is *not* used to
re-derive ``is_member`` — the caller is responsible for passing the
precomputed flag (typically via ``backend.app.plugins.hai.config.is_hai_author``).
This keeps scoring deterministic and side-effect-free.
"""

from __future__ import annotations

from typing import Iterable, Optional

#: Member floor bonus (added when ``is_member`` is True).
MEMBER_BONUS: float = 5.0

#: Per-keyword weight (cap applies via ``KEYWORD_CAP_COUNT``).
KEYWORD_WEIGHT: float = 1.5

#: Maximum keyword matches that count toward the bonus.
KEYWORD_CAP_COUNT: int = 5

#: Absolute cap on the total lab_bonus contribution to featured_score.
TOTAL_CAP: float = 12.5


def compute_hai_bonus(
    authors: Optional[Iterable[str]],
    hai_kw_count: int,
    is_member: bool,
) -> float:
    """Return the HAI lab_bonus contribution for a paper.

    Parameters
    ----------
    authors:
        Author list — accepted for caller ergonomics but unused. Pass whatever
        the caller has; the value is intentionally ignored so this function
        stays pure / side-effect free. Membership must be precomputed by the
        caller via ``backend.app.plugins.hai.config.is_hai_author(authors)``.
    hai_kw_count:
        Number of HAI keyword hits (typically from
        ``backend.app.plugins.hai.config.hai_keyword_score``).
    is_member:
        Whether any author is a HAI lab member.

    Returns
    -------
    float
        Bonus in the range ``[0.0, 12.5]``.
    """
    del authors  # explicitly unused; documented above

    kw = max(0, int(hai_kw_count or 0))
    bonus = 0.0
    if is_member:
        bonus += MEMBER_BONUS
    bonus += min(kw, KEYWORD_CAP_COUNT) * KEYWORD_WEIGHT
    return min(bonus, TOTAL_CAP)


__all__ = [
    "compute_hai_bonus",
    "MEMBER_BONUS",
    "KEYWORD_WEIGHT",
    "KEYWORD_CAP_COUNT",
    "TOTAL_CAP",
]
