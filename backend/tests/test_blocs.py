"""blocs.py: the single canonical bloc -> member mapping everything else is
derived from. These are data-integrity checks -- a typo here silently skews
every aggregate on the site."""
from collections import Counter

from global_monitor import blocs, db


def test_bloc_ids_and_slugs_are_unique():
    ids = [b.bloc_id for b in blocs.BLOCS]
    slugs = [b.slug for b in blocs.BLOCS]
    assert len(ids) == len(set(ids))
    assert len(slugs) == len(set(slugs))


def test_every_membership_references_a_known_bloc_and_country():
    bloc_ids = {b.bloc_id for b in blocs.BLOCS}
    for bloc_id, iso3, _from, _to in blocs.MEMBERSHIP:
        assert bloc_id in bloc_ids, bloc_id
        assert iso3 in blocs.ALL_COUNTRIES, iso3


def test_iso3_codes_are_three_uppercase_letters():
    assert all(len(c) == 3 and c.isupper() and c.isalpha() for c in blocs.ALL_COUNTRIES)


def test_no_duplicate_membership_rows():
    counts = Counter((b, i, f) for b, i, f, _ in blocs.MEMBERSHIP)
    assert [k for k, n in counts.items() if n > 1] == []


def test_expected_bloc_sizes():
    sizes = Counter(b for b, *_ in blocs.MEMBERSHIP)
    assert sizes["eu"] == 27
    assert sizes["brics5"] == 5
    assert sizes["brics"] == 10  # 5 founders + 5 expansion members as modelled
    assert sizes["usmca"] == 3
    assert sizes["us"] == 1


def test_brics5_is_exactly_the_founding_members_of_brics():
    founders = {i for b, i, *_ in blocs.MEMBERSHIP if b == "brics" and i in {"BRA", "RUS", "IND", "CHN", "ZAF"}}
    brics5 = {i for b, i, *_ in blocs.MEMBERSHIP if b == "brics5"}
    assert brics5 == founders


def test_saudi_arabia_deliberately_excluded():
    assert "SAU" not in blocs.ALL_COUNTRIES


def test_seed_populates_current_members(seeded):
    assert len(db.get_current_members("eu")) == 27
    assert set(db.get_current_members("usmca")) == {"USA", "CAN", "MEX"}


def test_seed_is_idempotent(seeded):
    before = {b.bloc_id: sorted(db.get_current_members(b.bloc_id)) for b in db.get_blocs()}
    blocs.seed()
    blocs.seed()
    after = {b.bloc_id: sorted(db.get_current_members(b.bloc_id)) for b in db.get_blocs()}
    assert before == after


def test_membership_respects_effective_dates(seeded):
    # Indonesia joined BRICS+ on 2025-01-01, Egypt on 2024-01-01
    assert "IDN" not in db.get_current_members("brics", as_of="2024-06-01")
    assert "IDN" in db.get_current_members("brics", as_of="2025-06-01")
    assert "EGY" in db.get_current_members("brics", as_of="2024-06-01")
    assert "EGY" not in db.get_current_members("brics", as_of="2023-01-01")


def test_all_tracked_iso3_is_sorted_and_complete():
    codes = blocs.all_tracked_iso3()
    assert codes == sorted(codes)
    assert set(codes) == set(blocs.ALL_COUNTRIES)
