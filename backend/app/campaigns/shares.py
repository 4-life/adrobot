"""Offer shares: pinned offers keep their %, the unpinned ones split what's left equally.

Shares are whole percentages (trackers take integers), so the split uses the largest-remainder
method: with equal fractions the extra points go to the top unpinned offers in list order,
e.g. 3 offers -> 34 / 33 / 33.
"""

from dataclasses import dataclass

TOTAL = 100
MIN_PIN = 1
MAX_PIN = 100


@dataclass(frozen=True)
class Allocation:
    shares: list[int]  # one per active offer, in list order
    errors: list[str]  # why this draft can't be pushed; empty when it can


def allocate(pins: list[int | None]) -> Allocation:
    """`pins`: each active offer's pinned share, or None when unpinned, in list order."""
    if not pins:
        return Allocation([], ["No active offers"])

    pinned_total = sum(p for p in pins if p is not None)
    unpinned = [i for i, p in enumerate(pins) if p is None]
    errors: list[str] = []
    if pinned_total > TOTAL:
        errors.append(f"Pinned shares add up to {pinned_total}%, over {TOTAL}%")
    elif not unpinned and pinned_total != TOTAL:
        errors.append(f"Every offer is pinned and they add up to {pinned_total}%, not {TOTAL}%")
    elif unpinned and pinned_total == TOTAL:
        errors.append("Pinned shares leave nothing for the unpinned offers")

    shares = [p or 0 for p in pins]
    if unpinned:
        base, extra = divmod(max(TOTAL - pinned_total, 0), len(unpinned))
        for rank, index in enumerate(unpinned):
            shares[index] = base + (1 if rank < extra else 0)
    return Allocation(shares, errors)
