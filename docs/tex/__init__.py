import re


def _escape_bare_underscores(s: str) -> str:
    """
    Escape underscores in plain text, but not inside {...} LaTeX command
    arguments.

    :param s: The input string to process.
    :return: The processed string with underscores escaped where appropriate.
    """
    result = []
    depth = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            # Keep the backslash and next character together (e.g. \_, \{, \ref)
            result.append(c)
            result.append(s[i + 1])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "_" and depth == 0:
            result.append(r"\_")
            i += 1
            continue
        result.append(c)
        i += 1
    return "".join(result)


def normalize_text(text: str) -> str:
    # Escape special LaTeX characters
    text = text.replace("#", r"\#")
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    # replace `code` with \texttt{code} (escape underscores inside)
    text = re.sub(
        r"`([^`]+)`",
        lambda m: r"\texttt{" + m.group(1).replace("_", r"\_") + "}",
        text,
    )
    # Escape bare underscores outside of {...} constructs
    text = _escape_bare_underscores(text)
    # replace **word** with \textbf{word} (must be before italic)
    text = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: r"\textbf{" + m.group(1) + "}",
        text,
    )
    # replace *word* with \textit{word}
    return re.sub(
        r"\*(.+?)\*",
        lambda m: r"\textit{" + m.group(1) + "}",
        text,
    )
