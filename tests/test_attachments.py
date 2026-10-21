import io

import pandas as pd
from PIL import Image

from finance_assistant.core.attachments import format_documents, read_file, select_passages


def text_pdf(text: str) -> bytes:
    """Smallest valid one-page PDF with a text layer."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    out.write(b"".join(b"%010d 00000 n \n" % off for off in offsets))
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref))
    return out.getvalue()


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buf, format="PNG")
    return buf.getvalue()


class FakeVisionLLM:
    is_mock = False

    def describe_image(self, data, mime, instruction):
        return "Balance: $1,234.56\nDescription: a bank statement"


def test_pdf_text_is_extracted():
    d = read_file("statement.pdf", text_pdf("Closing balance 4,250.00 USD with expense ratio 0.03 percent"))
    assert d["kind"] == "pdf" and "4,250.00" in d["text"] and not d["note"]


def test_scanned_pdf_without_llm_gets_a_note():
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(buf, format="PDF")
    d = read_file("scan.pdf", buf.getvalue())
    assert d["text"] == "" and "scanned" in d["note"]


def test_images_need_an_llm_and_use_it_when_present():
    assert "LLM provider" in read_file("receipt.png", png())["note"]
    d = read_file("receipt.png", png(), llm=FakeVisionLLM())
    assert "$1,234.56" in d["text"] and not d["note"]


def test_office_and_text_files():
    import docx
    doc = docx.Document()
    doc.add_paragraph("Employer 401(k) match is 4 percent")
    buf = io.BytesIO()
    doc.save(buf)
    assert "401(k) match" in read_file("benefits.docx", buf.getvalue())["text"]

    xbuf = io.BytesIO()
    pd.DataFrame({"symbol": ["VTI", "BND"], "shares": [10, 5]}).to_excel(xbuf, index=False)
    x = read_file("holdings.xlsx", xbuf.getvalue())["text"]
    assert "VTI,10" in x and "[Sheet" in x

    assert "rent" in read_file("budget.csv", b"item,amount\nrent,1500\n")["text"]
    assert '"rate": 5' in read_file("loan.json", b'{"rate": 5}')["text"]


def test_bad_and_unsupported_files_never_raise():
    assert "Couldn't read" in read_file("broken.pdf", b"not a pdf")["note"]
    assert "isn't supported" in read_file("movie.mp4", b"\x00\x01")["note"]


def test_passage_selection_fits_budget_and_finds_relevant_text():
    filler = "\n".join(f"Line {i} about groceries and coffee." for i in range(400))
    docs = [{"name": "big.txt", "text": filler + "\nThe mortgage interest rate is 6.5 percent.\n" + filler}]
    picked = select_passages(docs, "what is my mortgage interest rate", budget=2000)
    assert sum(len(t) for _, t in picked) <= 2000
    assert any("6.5 percent" in t for _, t in picked)
    assert picked[0][1].startswith("Line 0")  # file opening is always kept
    assert format_documents([{"name": "a.txt", "text": "hi"}], "x") == "--- a.txt ---\nhi"


def test_workflow_answers_from_attached_file(workflow):
    doc = read_file("notes.txt", b"My employer matches 401(k) contributions up to 6 percent of salary.")
    r = workflow.chat("What does my file say about the 401(k) match?", thread_id="t-files", attachments=[doc])
    assert "6 percent" in r["response"] and any(s.get("kind") == "upload" for s in r["sources"])
    # the file stays with the conversation for follow-ups
    r2 = workflow.chat("Remind me what my notes say about my employer match", thread_id="t-files")
    assert "6 percent" in r2["response"]
    assert "(attached: notes.txt)" in workflow.history("t-files")[0]["content"]
    # an unrelated question doesn't drag the file in
    r3 = workflow.chat("What is an ETF?", thread_id="t-files")
    assert not any(s.get("kind") == "upload" for s in r3["sources"]) and "6 percent" not in r3["response"]
