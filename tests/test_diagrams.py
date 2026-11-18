"""The data-structure diagram blocks (```array, ```linkedlist, ...) rendered to SVG."""

from __future__ import annotations

import re
import unittest

from swe_prac import diagrams, pages

CELL_X = re.compile(r'<rect class="ds-cell[^"]*" x="([\d.]+)"')


class DiagramTests(unittest.TestCase):
    def test_frames_share_the_label_column(self):
        for kind in ("array", "linkedlist"):
            with self.subTest(kind=kind):
                svg = diagrams.render(kind, "label: seen\nvalues: 1 2\n---\nvalues: 3 4")
                xs = CELL_X.findall(svg)
                self.assertEqual(xs[0], xs[2])  # the unlabelled frame lines up

    def test_dimmed_values_are_dimmed_too(self):
        svg = diagrams.render("array", "values: 1 2 3\ndim: 0 2")
        self.assertEqual(svg.count('class="ds-val dim"'), 2)
        self.assertEqual(svg.count('class="ds-cell dim"'), 2)

    def test_a_negative_pointer_counts_from_the_end(self):
        last = diagrams.render("array", "values: 1 2 3\npointers: p=2")
        self.assertEqual(diagrams.render("array", "values: 1 2 3\npointers: p=-1"), last)
        with self.assertRaisesRegex(diagrams.DiagramError, "outside -3..3"):
            diagrams.render("array", "values: 1 2 3\npointers: p=-4")

    def test_an_unknown_key_is_an_error(self):
        cases = {
            "array": "values: 1 2\nhightlight: 0",
            "grid": "0 1\n1 0\nhightlight: 0,0",  # would otherwise be drawn as a third row
            "tree": "values: 1 2 3\nlabel: root",
        }
        for kind, text in cases.items():
            with self.subTest(kind=kind), self.assertRaisesRegex(diagrams.DiagramError, "no key"):
                diagrams.render(kind, text)

    def test_errors_render_in_place_of_the_figure(self):
        html = pages.render("```array\npointers: i=0\n```\n")
        self.assertIn("Diagram error (array):", html)
        self.assertIn("array needs", html)
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render("hexagon", "values: 1")


if __name__ == "__main__":
    unittest.main()
