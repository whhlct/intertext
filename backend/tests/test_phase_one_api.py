import asyncio

from app.main import app
from httpx import ASGITransport, AsyncClient, Response


def request(path: str) -> Response:
    async def send_request() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(send_request())


def test_lists_texts_and_current_versions(
    canonical_fixture: None,
) -> None:
    texts_response = request("/api/v1/texts")
    versions_response = request("/api/v1/texts/bible/versions")

    assert texts_response.status_code == 200
    assert texts_response.json()[0]["slug"] == "bible"
    assert versions_response.status_code == 200
    assert {version["slug"] for version in versions_response.json()} == {
        "english",
        "greek",
    }


def test_reader_resolves_and_aligns_selected_versions(
    canonical_fixture: None,
) -> None:
    response = request("/api/v1/reader/bible/Mark%20%201?versions=greek,english")

    assert response.status_code == 200
    body = response.json()
    assert body["reference"] == {
        "label": "Mark 1",
        "start": "bible.mark.1.1",
        "end": "bible.mark.1.2",
    }
    assert [version["slug"] for version in body["versions"]] == [
        "greek",
        "english",
    ]
    assert body["versions"][0]["roles"] == ["default_source"]
    assert [unit["label"] for unit in body["units"]] == ["1", "2"]
    assert body["units"][0]["segments"]["english"][0]["text"] == (
        "The beginning of the gospel"
    )
    assert body["units"][1]["segments"]["greek"][0]["mapping_type"] == ("spans")


def test_reader_rejects_unknown_reference(canonical_fixture: None) -> None:
    response = request("/api/v1/reader/bible/Unknown")

    assert response.status_code == 404
    assert "Reference 'Unknown' was not found" in response.json()["detail"]


def test_reader_rejects_unknown_requested_version(canonical_fixture: None) -> None:
    response = request("/api/v1/reader/bible/Mark%201?versions=missing")

    assert response.status_code == 404
    assert "missing" in response.json()["detail"]


def test_lists_top_level_structure_and_children(canonical_fixture: None) -> None:
    top_level_response = request("/api/v1/texts/bible/structure")

    assert top_level_response.status_code == 200
    top_level = top_level_response.json()
    assert len(top_level) == 1
    assert top_level[0]["node_type"] == "book"
    assert top_level[0]["title"] == "Mark"
    assert top_level[0]["path"] == "bible.mark"

    children_response = request(
        f"/api/v1/texts/bible/structure/{top_level[0]['id']}/children"
    )
    assert children_response.status_code == 200
    children = children_response.json()
    assert len(children) == 1
    assert children[0]["node_type"] == "chapter"
    assert children[0]["title"] == "Mark 1"
    assert children[0]["path"] == "bible.mark.1"

    leaf_response = request(
        f"/api/v1/texts/bible/structure/{children[0]['id']}/children"
    )
    assert leaf_response.status_code == 200
    assert leaf_response.json() == []


def test_rejects_unknown_structure_node(canonical_fixture: None) -> None:
    response = request(
        "/api/v1/texts/bible/structure/00000000-0000-0000-0000-000000000000/children"
    )

    assert response.status_code == 404


def test_resolves_reference_to_canonical_range(canonical_fixture: None) -> None:
    response = request("/api/v1/texts/bible/references/resolve?reference=Mark%20%201")

    assert response.status_code == 200
    body = response.json()
    assert body["input"] == "Mark  1"
    assert body["normalized_reference"] == "mark 1"
    assert body["label"] == "Mark 1"
    assert body["reference_scheme"] == "Default"
    assert body["start"]["key"] == "bible.mark.1.1"
    assert body["end"]["key"] == "bible.mark.1.2"
    assert body["start"]["ordinal"] == 1
    assert body["end"]["ordinal"] == 2


def test_reference_resolver_rejects_unknown_reference(
    canonical_fixture: None,
) -> None:
    response = request("/api/v1/texts/bible/references/resolve?reference=Unknown")

    assert response.status_code == 404


def test_reader_rejects_malformed_versions_parameter(
    canonical_fixture: None,
) -> None:
    response = request("/api/v1/reader/bible/Mark%201?versions=greek,,english")

    assert response.status_code == 422
    assert "comma-separated" in response.json()["detail"]
