#!/usr/bin/env python3
"""Print the text of a .docx file, one paragraph per line.

Standard library only, for machines without python-docx or pandoc.
Usage: python docx_to_text.py FILE.docx [FILE2.docx ...]
"""

import html
import re
import sys
import zipfile


def docx_text(path: str) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    text = html.unescape(re.sub(r"<[^>]+>", "", xml))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for i, p in enumerate(sys.argv[1:]):
        if len(sys.argv) > 2:
            print(f"{'' if i == 0 else chr(10)}===== {p} =====")
        print(docx_text(p))
