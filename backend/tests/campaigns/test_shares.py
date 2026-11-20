import pytest

from app.campaigns.shares import allocate


@pytest.mark.parametrize("count", range(1, 11))
def test_equal_split_always_adds_up_to_100(count: int) -> None:
    allocation = allocate([None] * count)

    assert sum(allocation.shares) == 100
    assert max(allocation.shares) - min(allocation.shares) <= 1
    assert allocation.errors == []


@pytest.mark.parametrize(
    ("pins", "shares"),
    [
        ([None, None], [50, 50]),
        ([None] * 4, [25, 25, 25, 25]),
        ([None] * 3, [34, 33, 33]),
        ([None] * 6, [17, 17, 17, 17, 16, 16]),
        ([50, None, None], [50, 25, 25]),
        ([None, 40, None, None], [20, 40, 20, 20]),
        ([None, 10, None], [45, 10, 45]),
        ([70, None, None, None], [70, 10, 10, 10]),
        ([60, 40], [60, 40]),
        ([100], [100]),
    ],
)
def test_pinned_keep_their_share_and_the_rest_split(
    pins: list[int | None], shares: list[int]
) -> None:
    allocation = allocate(pins)

    assert allocation.shares == shares
    assert allocation.errors == []


def test_extra_points_go_to_the_top_unpinned_offers() -> None:
    assert allocate([None, 1, None, None]).shares == [33, 1, 33, 33]
    assert allocate([None, 2, None, None]).shares == [33, 2, 33, 32]


@pytest.mark.parametrize(
    ("pins", "error"),
    [
        ([], "No active offers"),
        ([70, 40], "Pinned shares add up to 110%, over 100%"),
        ([70, 40, None], "Pinned shares add up to 110%, over 100%"),
        ([30, 30], "Every offer is pinned and they add up to 60%, not 100%"),
        ([60, 40, None], "Pinned shares leave nothing for the unpinned offers"),
    ],
)
def test_invalid_drafts(pins: list[int | None], error: str) -> None:
    assert allocate(pins).errors == [error]
