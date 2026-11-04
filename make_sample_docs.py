"""Create sample-data variants (word-processing file via raw OOXML zip, txt copy)."""
import html
import zipfile
from pathlib import Path

base = Path(__file__).resolve().parent / "sample-data"

lines = (base / "meeting-notes.md").read_text().splitlines()
paras = []
for line in lines:
    text = line.strip()
    if not text:
        continue
    t = html.escape(text, quote=False)
    paras.append(f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>')

document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>' + ''.join(paras) + '</w:body></w:document>')

content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                 '</Types>')

rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')

out = base / "meeting-notes.docx"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("_rels/.rels", rels)
    z.writestr("word/document.xml", document)

(base / "development-tasks.txt").write_text(
    (base / "development-tasks.md").read_text())
print("created", out, "and development-tasks.txt")