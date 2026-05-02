from __future__ import annotations

import pytest
from app.pii import mask


def test_mask_returns_tuple():
    text = "Hello world"
    result, entities = mask(text)
    assert isinstance(result, str)
    assert isinstance(entities, list)


def test_mask_detects_email():
    text = "Contact john.doe@example.com for help."
    masked, entities = mask(text)
    assert "john.doe@example.com" not in masked
    assert any(e["entity_type"] == "EMAIL_ADDRESS" for e in entities)


def test_mask_empty_string():
    result, entities = mask("")
    assert result == ""
    assert entities == []


def test_mask_no_pii():
    text = "The capital gains tax rate is 15 percent."
    result, entities = mask(text)
    assert result == text
    assert entities == []
