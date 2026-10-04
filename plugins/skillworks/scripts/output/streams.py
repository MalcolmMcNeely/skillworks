# A Windows pipe takes the locale's code page and adds a carriage return, and an odd character must not stop a command.
def speaking_any_character(stream):
    stream.reconfigure(newline="\n", encoding="utf-8", errors="backslashreplace")
