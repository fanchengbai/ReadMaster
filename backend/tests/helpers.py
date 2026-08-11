from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def create_minimal_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
            compress_type=ZIP_DEFLATED,
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">readmaster-test</dc:identifier>
    <dc:title>Learning Through Reading</dc:title>
    <dc:creator>Jane Reader</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter-one" href="text/chapter-1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter-two" href="text/chapter-2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter-one"/>
    <itemref idref="chapter-two"/>
  </spine>
</package>""",
        )
        archive.writestr(
            "OEBPS/nav.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <body><nav epub:type="toc"><ol>
    <li><a href="text/chapter-1.xhtml">A New Beginning</a></li>
    <li><a href="text/chapter-2.xhtml">Reading Practice</a></li>
  </ol></nav></body>
</html>""",
        )
        archive.writestr(
            "OEBPS/text/chapter-1.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>A New Beginning</h1>
<p>Reading connects us with another mind.</p>
<p>Context gives unfamiliar words a place to live.</p>
</body></html>""",
        )
        archive.writestr(
            "OEBPS/text/chapter-2.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>Reading Practice</h1>
<p>Practice turns recognition into understanding.</p>
<script>this text must be ignored</script>
</body></html>""",
        )
    return output.getvalue()
