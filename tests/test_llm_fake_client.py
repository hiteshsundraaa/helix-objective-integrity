import json

from helix.llm.fake_client import DeterministicFakeLLMClient


def test_fake_client_returns_json() -> None:
    client = DeterministicFakeLLMClient()
    response = client.complete(system="system", user="Step 1 read file")
    payload = json.loads(response.text)

    assert payload["tool"] == "read_file"
    assert response.provider == "fake"
