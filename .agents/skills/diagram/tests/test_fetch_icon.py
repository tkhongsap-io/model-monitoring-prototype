"""fetch_icon.py: add_fill, the one change made to a downloaded Simple Icons file."""

import unittest

import support  # noqa: F401  (puts the scripts on sys.path)

import fetch_icon
import icon_safety

ROOT = b'<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'


class AddFill(unittest.TestCase):
    def test_the_fill_goes_on_the_root(self) -> None:
        data = ROOT + b'<path d="M0"/></svg>\n'
        filled = fetch_icon.add_fill(data, "#009639")
        self.assertTrue(filled.startswith(b'<svg fill="#009639" role="img"'))
        self.assertEqual(filled.replace(b' fill="#009639"', b"", 1), data)
        self.assertEqual(icon_safety.svg_problems(filled), [])

    def test_a_child_fill_is_left_alone(self) -> None:
        data = ROOT + b'<path fill="#000000" d="M0"/></svg>\n'
        filled = fetch_icon.add_fill(data, "#2496ED")
        self.assertIn(b'<path fill="#000000" d="M0"/>', filled)
        self.assertEqual(filled.count(b"#2496ED"), 1)

    def test_an_xml_declaration_before_the_root_is_kept(self) -> None:
        data = b'<?xml version="1.0"?>\n' + ROOT + b"</svg>\n"
        filled = fetch_icon.add_fill(data, "#336791")
        self.assertTrue(filled.startswith(b'<?xml version="1.0"?>\n<svg fill="#336791" '))

    def test_a_root_that_has_a_fill_is_refused(self) -> None:
        data = b'<svg fill="red" xmlns="http://www.w3.org/2000/svg"></svg>\n'
        with self.assertRaises(SystemExit):
            fetch_icon.add_fill(data, "#009639")

    def test_a_fill_rule_on_the_root_is_not_a_fill(self) -> None:
        data = b'<svg fill-rule="evenodd" xmlns="http://www.w3.org/2000/svg"></svg>\n'
        self.assertIn(b'<svg fill="#009639" fill-rule=', fetch_icon.add_fill(data, "#009639"))

    def test_a_file_without_an_svg_root_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            fetch_icon.add_fill(b"<html></html>\n", "#009639")


if __name__ == "__main__":
    unittest.main()
