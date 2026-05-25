import io
from datetime import datetime

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image,
)
from reportlab.lib import colors


def prescription_pdf(*, clinic_name: str, doctor_name: str, license_no: str,
                     patient_name: str, patient_dni: str | None,
                     prescriptions: list[dict], verify_url: str) -> bytes:
    buf = io.BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, h - 2 * cm, clinic_name)
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, h - 2.6 * cm, f"Receta digital — {datetime.utcnow().strftime('%d/%m/%Y')}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, h - 4 * cm, f"Profesional: {doctor_name}")
    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, h - 4.6 * cm, f"Matrícula: {license_no}")
    c.drawString(2 * cm, h - 5.4 * cm, f"Paciente: {patient_name}")
    if patient_dni:
        c.drawString(2 * cm, h - 6.0 * cm, f"DNI: {patient_dni}")

    y = h - 7.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Indicaciones:")
    y -= 0.7 * cm
    c.setFont("Helvetica", 11)
    for p in prescriptions:
        line = f"• {p.get('drug', '')} — {p.get('dosage', '')} {p.get('frequency', '')}"
        c.drawString(2.2 * cm, y, line[:90])
        y -= 0.55 * cm
        if p.get("instructions"):
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(2.6 * cm, y, p["instructions"][:100])
            y -= 0.5 * cm
            c.setFont("Helvetica", 11)
        if y < 4 * cm:
            c.showPage(); y = h - 2 * cm

    qimg = qrcode.make(verify_url)
    qbuf = io.BytesIO(); qimg.save(qbuf, format="PNG"); qbuf.seek(0)
    c.drawImage(__import__("reportlab.lib.utils", fromlist=["ImageReader"])
                .ImageReader(qbuf), w - 5.5 * cm, 2 * cm, 3.5 * cm, 3.5 * cm)
    c.setFont("Helvetica", 8)
    c.drawString(w - 5.5 * cm, 1.7 * cm, "Validá la receta escaneando el QR")

    c.setLineWidth(0.5)
    c.line(2 * cm, 4 * cm, w / 2, 4 * cm)
    c.drawString(2 * cm, 3.5 * cm, "Firma y sello del profesional")

    c.showPage(); c.save()
    return buf.getvalue()


def report_pdf(*, title: str, rows: list[list[str]], headers: list[str]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    data = [headers] + rows
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()
