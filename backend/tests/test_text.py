from app.utils.text import clean_text, split_sentences


def test_clean_text_normalizes_whitespace():
    raw = "Hello   world\r\n\r\n\r\nnext\tparagraph  "
    cleaned = clean_text(raw)
    assert "  " not in cleaned.replace("\n", "")
    assert "\n\n\n" not in cleaned
    assert cleaned.startswith("Hello world")


def test_clean_text_strips_control_chars():
    assert "\x00" not in clean_text("a\x00b")


def test_split_sentences():
    sentences = split_sentences("First sentence. Second one! Third? Yes.")
    assert len(sentences) == 4
    assert sentences[0] == "First sentence."
