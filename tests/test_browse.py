from api.routes.search import browse_releases, get_filter_options
from db.models import Release, Track


def _seed_releases(session):
    session.add(
        Release(
            id=1,
            title="Strobe",
            artists="deadmau5",
            year=2009,
            genres="Electronic, Progressive House",
        )
    )
    session.add(
        Release(
            id=2,
            title="One More Time",
            artists="Daft Punk",
            year=2000,
            genres="Electronic, House",
        )
    )
    session.add(
        Release(
            id=3,
            title="Born Slippy",
            artists="Underworld",
            year=1995,
            genres="Electronic",
        )
    )
    session.commit()


def test_browse_releases_returns_all_when_unfiltered(session):
    _seed_releases(session)
    releases = browse_releases(session)
    assert {r.id for r in releases} == {1, 2, 3}


def test_browse_releases_filters_by_year(session):
    _seed_releases(session)
    releases = browse_releases(session, year=2009)
    assert [r.id for r in releases] == [1]


def test_browse_releases_filters_by_artist(session):
    _seed_releases(session)
    releases = browse_releases(session, artist="Daft Punk")
    assert [r.id for r in releases] == [2]


def test_browse_releases_filters_by_genre_substring(session):
    _seed_releases(session)
    releases = browse_releases(session, genre="House")
    assert {r.id for r in releases} == {1, 2}


def test_browse_releases_combines_filters(session):
    _seed_releases(session)
    releases = browse_releases(session, genre="Electronic", year=1995)
    assert [r.id for r in releases] == [3]


def test_browse_releases_no_match_returns_empty(session):
    _seed_releases(session)
    assert browse_releases(session, year=1900) == []


def test_filter_options_returns_distinct_sorted_values(session):
    _seed_releases(session)
    options = get_filter_options(session)

    assert options["years"] == [2009, 2000, 1995]  # newest first
    assert options["artists"] == ["Daft Punk", "Underworld", "deadmau5"]
    assert options["genres"] == ["Electronic", "House", "Progressive House"]


def test_filter_options_ignores_releases_with_no_year_or_genre(session):
    session.add(Release(id=99, title="No Metadata", artists="Mystery Artist"))
    session.commit()

    options = get_filter_options(session)

    assert None not in options["years"]
    assert "" not in options["genres"]
    assert "Mystery Artist" in options["artists"]


def test_index_page_shows_browsable_list_by_default(session, client):
    _seed_releases(session)
    resp = client.get("/")
    assert "Strobe" in resp.text
    assert "Born Slippy" in resp.text
    assert 'href="/release/1"' in resp.text


def test_index_page_filter_dropdowns_populated(session, client):
    _seed_releases(session)
    resp = client.get("/")
    assert "Electronic" in resp.text
    assert "2009" in resp.text
    assert "deadmau5" in resp.text


def test_search_endpoint_handles_empty_filter_params_from_unselected_dropdowns(
    session, client
):
    # Regression test: an unselected <select> submits an empty string, not
    # an absent param. The route used to declare year as Optional[int],
    # which FastAPI/Pydantic rejects with a 422 for "" instead of treating
    # it as "no filter" -- only caught by hitting the real endpoint with the
    # same query string a browser actually sends, not by calling
    # browse_releases() directly.
    _seed_releases(session)
    resp = client.get("/search", params={"q": "", "year": "", "genre": "", "artist": ""})
    assert resp.status_code == 200
    assert "Strobe" in resp.text


def test_search_endpoint_genre_filter_via_query_params(session, client):
    _seed_releases(session)
    resp = client.get("/search", params={"q": "", "year": "", "genre": "House", "artist": ""})
    assert resp.status_code == 200
    assert "Strobe" in resp.text  # Progressive House
    assert "One More Time" in resp.text  # House
    assert "Born Slippy" not in resp.text  # plain Electronic only


def test_search_endpoint_year_filter_via_query_params(session, client):
    _seed_releases(session)
    resp = client.get("/search", params={"q": "", "year": "2009", "genre": "", "artist": ""})
    assert resp.status_code == 200
    assert "Strobe" in resp.text
    assert "Born Slippy" not in resp.text


def test_index_page_with_empty_collection_shows_no_releases_message(session, client):
    resp = client.get("/")
    assert "No releases match these filters." in resp.text
