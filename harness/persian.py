import re
from typing import Optional

# Regex pattern for Persian/Arabic Unicode blocks
PERSIAN_ARABIC_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

# Common markdown line prefixes that should not be inverted
MARKDOWN_PREFIX_REGEX = re.compile(r"^(#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    # Configure reshaper with full Persian letter support
    _config = {
        "delete_harakat": False,
        "support_ligatures": True,
        "RIAL SIGN": True,
    }
    _reshaper = arabic_reshaper.ArabicReshaper(configuration=_config)
    HAS_BIDI_SUPPORT = True
except ImportError:
    _reshaper = None
    HAS_BIDI_SUPPORT = False

# Global toggle to enable/disable Persian reshaping (enabled by default)
_PERSIAN_FIX_ENABLED = True


def set_persian_fix(enabled: bool) -> None:
    """Enables or disables automatic Persian terminal BiDi fixing."""
    global _PERSIAN_FIX_ENABLED
    _PERSIAN_FIX_ENABLED = enabled


def is_persian_fix_enabled() -> bool:
    """Returns True if Persian terminal BiDi fixing is active."""
    return _PERSIAN_FIX_ENABLED and HAS_BIDI_SUPPORT


def has_persian(text: str) -> bool:
    """Returns True if the text contains any Persian/Arabic characters."""
    if not text:
        return False
    return bool(PERSIAN_ARABIC_PATTERN.search(text))


def fix_persian_text(text: str) -> str:
    """
    Reshapes and applies BiDi algorithm to Persian text so that
    standard LTR terminals display it in the correct reading order.
    Leaves non-Persian strings completely intact.
    """
    if not is_persian_fix_enabled() or not text or not has_persian(text):
        return text

    try:
        # Pre-clean any backtick markers in single-line strings if needed
        reshaped = _reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def fix_persian_line(line: str) -> str:
    """Fixes a single line of text, preserving markdown prefixes if present."""
    if not is_persian_fix_enabled() or not has_persian(line):
        return line

    match = MARKDOWN_PREFIX_REGEX.match(line)
    if match:
        prefix = match.group(0)
        content = line[len(prefix):]
        return prefix + fix_persian_text(content)

    return fix_persian_text(line)


def fix_persian_markdown(text: str) -> str:
    """
    Fixes Persian text within markdown documents while leaving code blocks
    (```...```) and non-Persian blocks untouched.
    """
    if not is_persian_fix_enabled() or not text or not has_persian(text):
        return text

    lines = text.splitlines()
    processed_lines = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            processed_lines.append(line)
            continue

        if in_code_block:
            # Leave code inside code blocks untouched
            processed_lines.append(line)
        else:
            processed_lines.append(fix_persian_line(line))

    return "\n".join(processed_lines)
