from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def export_to_pdf(result):
    c = canvas.Canvas("pitch_output.pdf", pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "PitchCraft - AI Startup Pitch")
    c.setFont("Helvetica", 12)

    y = 770
    for key, value in result.items():
        c.drawString(50, y, f"{key.capitalize()}: {value}")
        y -= 40
        if y < 100:
            c.showPage()
            y = 770

    c.save()
