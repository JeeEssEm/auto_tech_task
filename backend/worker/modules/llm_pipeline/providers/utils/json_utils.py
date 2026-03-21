def extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return text.strip()
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False; continue
        if ch == "\\" and in_string:
            escape_next = True; continue
        if ch == '"':
            in_string = not in_string; continue
        if in_string:
            continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:].strip()


# providers/utils/json_utils.py

_CTRL_ESCAPE: dict[str, str] = {
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


def escape_control_chars_in_strings(text: str) -> str:
    """
    Экранирует литеральные управляющие символы внутри JSON-строк.

    Проблема: LLM иногда вставляет в JSON буквальный \n (0x0A) вместо
    экранированного \\n. JSON-парсер это отклоняет (RFC 8259, sec 7).

    Алгоритм тот же что в extract_first_json_object — отслеживаем
    in_string, чтобы не трогать пробелы между ключами.
    """
    result: list[str] = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            escape_next = False
            result.append(ch)
            continue
        if ch == "\\" and in_string:
            escape_next = True
            result.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and "\x00" <= ch <= "\x1f":
            result.append(_CTRL_ESCAPE.get(ch, f"\\u{ord(ch):04x}"))
            continue
        result.append(ch)

    return "".join(result)
