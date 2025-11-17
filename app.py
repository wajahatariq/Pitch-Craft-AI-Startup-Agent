import streamlit as st
from litellm import completion
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO
from pathlib import Path
import re
import zipfile
import requests

domainsduck_key = st.secrets["DOMAINDUCK_API_KEY"]

# Load CSS from external file in the same directory as app.py
css_path = Path(__file__).parent / "style.css"

def local_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css(css_path)

st.set_page_config(page_title="PitchCraft - AI Startup Partner", layout="centered")

st.title("PitchCraft – Your AI Startup Partner")

st.markdown(
    """
Generate **startup content dynamically**.  
Enter your startup idea, select tone, and toggle which assets to generate.
"""
)

# --- Domain availability check ---

def check_domain_availability(domain: str) -> str:
    url = "https://us.domainsduck.com/api/get/"
    params = {
        "domain": domain,
        "apikey": domainsduck_key,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("availability", "unknown").upper()
    except Exception as e:
        return f"ERROR: {str(e)}"

def map_domain_status(status):
    if status == "TRUE":
        return "Domain is available"
    elif status == "FALSE":
        return "Domain is taken"
    elif status.startswith("ERROR"):
        return status  # Return the error message as is
    else:
        return "Unable to check status"

# --- LLM interaction helper ---

def clean_markdown(text):
    replacements = [
        ("**", ""),
        ("*", ""),
        ("+", ""),
        ("\u2022", ""),
        ("\n\n", "\n"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text.strip()

def create_pitch_pdf(data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', fontSize=24, leading=28, alignment=TA_CENTER, spaceAfter=20, spaceBefore=10))
    styles.add(ParagraphStyle(name='Heading', fontSize=16, leading=20, spaceAfter=10, spaceBefore=15))
    styles.add(ParagraphStyle(name='Body', fontSize=12, leading=16))
    styles.add(ParagraphStyle(name='CustomBullet', fontSize=12, leading=16, leftIndent=15, bulletIndent=5))
    styles.add(ParagraphStyle(name='CustomIndentedBullet', fontSize=12, leading=16, leftIndent=30, bulletIndent=10))

    story = []

    story.append(Paragraph(data['name'], styles['TitleCenter']))
    story.append(Paragraph(data['tagline'], styles['Heading']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Problem", styles['Heading']))
    story.append(Paragraph(data['problem'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Solution", styles['Heading']))
    story.append(Paragraph(data['solution'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Target Audience & Pain Points", styles['Heading']))
    audience_lines = data['audience'].strip().split('\n')
    for line in audience_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("•") or line.startswith("-"):
            text = clean_markdown(line[1:].strip())
            story.append(Paragraph(text, styles['CustomBullet'], bulletText="•"))
        elif line.startswith("+"):
            text = clean_markdown(line[1:].strip())
            story.append(Paragraph(text, styles['CustomIndentedBullet'], bulletText="–"))
        else:
            story.append(Paragraph(clean_markdown(line), styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Elevator Pitch", styles['Heading']))
    story.append(Paragraph(data['pitch'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Brand Direction", styles['Heading']))
    brand_text = data['brand']

    options = re.split(r"\*\*Option \d+: Startup Name - [^\*]+\*\*", brand_text)
    titles = re.findall(r"\*\*Option \d+: Startup Name - ([^\*]+)\*\*", brand_text)

    if options and options[0].strip() == "":
        options = options[1:]

    for i, option_text in enumerate(options):
