import unittest
from harness.persian import (
    has_persian,
    fix_persian_text,
    fix_persian_line,
    fix_persian_markdown,
    set_persian_fix,
    is_persian_fix_enabled,
)


class TestPersianSupport(unittest.TestCase):

    def setUp(self):
        set_persian_fix(True)

    def test_has_persian(self):
        self.assertTrue(has_persian("سلام دنیا"))
        self.assertTrue(has_persian("پروژه پایتون"))
        self.assertFalse(has_persian("Hello World"))
        self.assertFalse(has_persian("def add(a, b): return a + b"))

    def test_fix_persian_text(self):
        text = "پروژه پایتون"
        fixed = fix_persian_text(text)
        # Should be reshaped and not equal to the raw disconnected sequence
        self.assertNotEqual(fixed, text)
        self.assertTrue(len(fixed) > 0)

        # English should remain completely unchanged
        eng = "Hello Python 123"
        self.assertEqual(fix_persian_text(eng), eng)

    def test_fix_persian_markdown_preserves_prefixes(self):
        line = "# پروژه تست"
        fixed = fix_persian_line(line)
        self.assertTrue(fixed.startswith("# "))

        list_item = "- مورد اول: تست موفق"
        fixed_item = fix_persian_line(list_item)
        self.assertTrue(fixed_item.startswith("- "))

    def test_fix_persian_markdown_preserves_code_blocks(self):
        md = (
            "### عنوان\n"
            "```python\n"
            "def test_func():\n"
            "    # comment\n"
            "    return True\n"
            "```\n"
            "پایان متن"
        )
        fixed_md = fix_persian_markdown(md)
        self.assertIn("```python\ndef test_func():\n    # comment\n    return True\n```", fixed_md)

    def test_toggle_persian_fix(self):
        set_persian_fix(False)
        self.assertFalse(is_persian_fix_enabled())
        text = "سلام دنیا"
        self.assertEqual(fix_persian_text(text), text)

        set_persian_fix(True)
        self.assertTrue(is_persian_fix_enabled())
        self.assertNotEqual(fix_persian_text(text), text)


if __name__ == "__main__":
    unittest.main()
