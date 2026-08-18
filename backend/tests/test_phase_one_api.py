import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


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
    response = request(
        "/api/v1/reader/bible/Mark%20%201?version=greek&version=english"
    )

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
    assert body["units"][1]["segments"]["greek"][0]["mapping_type"] == (
        "spans"
    )


def test_reader_rejects_unknown_reference(canonical_fixture: None) -> None:
    response = request("/api/v1/reader/bible/Unknown")

    assert response.status_code == 404
    assert "Reference 'Unknown' was not found" in response.json()["detail"]


def test_reader_rejects_unknown_requested_version(canonical_fixture: None) -> None:
    response = request("/api/v1/reader/bible/Mark%201?version=missing")

    assert response.status_code == 404
    assert "missing" in response.json()["detail"]
