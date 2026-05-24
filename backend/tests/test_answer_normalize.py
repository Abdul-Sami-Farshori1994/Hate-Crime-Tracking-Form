from answer_normalize import _parse_checkbox_raw


def test_parse_checkbox_semicolon_separated():
    assert _parse_checkbox_raw("A; B; C") == ["A", "B", "C"]
