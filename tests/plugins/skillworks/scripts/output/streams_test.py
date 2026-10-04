import io

from output.streams import speaking_any_character


def test_the_command_prints_a_character_its_code_page_lacks():
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    speaking_any_character(stream)
    stream.write("✔ every case passed, and \ud800 is escaped\n")
    stream.flush()

    assert stream.buffer.getvalue() == "✔ every case passed, and \\ud800 is escaped\n".encode("utf-8")
