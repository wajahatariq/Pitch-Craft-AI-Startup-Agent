import streamlit as st
from litellm import completion
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO
from pathlib import Path
import re

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
Generate **startup pitches, names, taglines, target audiences, and branding concepts**
Enter your startup idea and select a tone to get started.
"""
)

# --- LLM interaction helper ---

def run_completion(prompt: str):
    response = completion(
        model="groq/llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        api_key=st.secrets["GROQ_API_KEY"],
    )
    return response["choices"][0]["message"]["content"].strip()

# --- Detailed prompts for each agent ---

def idea_agent(idea):
    prompt = f"""
You are a seasoned startup strategist. Analyze this startup idea carefully.

Provide a concise summary (2-3 sentences) that clearly identifies:
- The main problem the startup addresses
- The core solution it offers

Make the summary compelling and insightful.

Startup Idea:
{idea}
"""
    return run_completion(prompt)

def name_agent(summary):
    prompt = f"""
Generate exactly 3 unique startup names as a numbered list ONLY.  
Do NOT include any explanations, descriptions, or pronunciation guides.
Avoid generic words like "AI", "Tech".
Names only.
"""
    return run_completion(prompt)

def extract_first_name(names_text):
    # Extracts first startup name from a numbered list format
    lines = names_text.strip().split('\n')
    for line in lines:
        if line.strip().startswith("1."):
            return line.split('.', 1)[1].strip()
    # fallback: first non-empty line
    for line in lines:
        if line.strip():
            return line.strip()
    return "StartupName"

def tagline_agent(name, tone):
    prompt = f"""
You are an expert copywriter.

Create a catchy and memorable tagline for this startup name.

Requirements:
- Reflect the startup's core value and vision
- Use the tone: {tone} (e.g., Formal, Casual, Fun, Investor)
- Keep it short (under 10 words)
- Output only the tagline text (no explanations)

Startup Name:
{name}
"""
    return run_completion(prompt)

def pitch_agent(summary, tone):
    prompt = f"""
You are a skilled marketer.

Write a compelling **two-paragraph elevator pitch** for this startup.

Include:
- A clear statement of the problem and its impact
- A description of the solution and unique value proposition
- Use the tone: {tone}

Startup Summary:
{summary}
"""
    return run_completion(prompt)

def audience_agent(summary):
    prompt = f"""
You are a market analyst.

Define the target audience and their pain points for this startup.

Format your answer as bullet points grouped under:
- Primary Target Audience
- Secondary Target Audience
- Pain Points

Use clear and concise language.

Startup Summary:
{summary}
"""
    return run_completion(prompt)

def brand_agent(name, tone):
    prompt = f"""
You are a branding expert.

Suggest a professional color palette (with hex codes) and a simple but effective logo concept idea for this startup.

Consider the startup name: {name} and the tone: {tone}.

Describe:
- Primary and secondary colors
- Logo style and symbolism

Output your response in clear paragraphs.
"""
    return run_completion(prompt)

def report_agent(name, tagline, pitch, audience, brand):
    # Split pitch into problem and solution if possible
    if "." in pitch:
        problem = pitch.split(".", 1)[0] + "."
        solution = pitch.split(".", 1)[1].strip()
    else:
        problem = pitch
        solution = ""
    return {
        "name": name,
        "tagline": tagline,
        "pitch": pitch,
        "audience": audience,
        "problem": problem,
        "solution": solution,
        "brand": brand,
    }

# --- PDF generation ---

def clean_markdown(text):
    # Basic cleanup to remove markdown characters for PDF clarity
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

    # Title and Tagline
    story.append(Paragraph(data['name'], styles['TitleCenter']))
    story.append(Paragraph(data['tagline'], styles['Heading']))
    story.append(Spacer(1, 12))

    # Problem and Solution
    story.append(Paragraph("Problem", styles['Heading']))
    story.append(Paragraph(data['problem'], styles['Body']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Solution", styles['Heading']))
    story.append(Paragraph(data['solution'], styles['Body']))
    story.append(Spacer(1, 12))

    # Audience - bullet points
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

    # Elevator Pitch
    story.append(Paragraph("Elevator Pitch", styles['Heading']))
    story.append(Paragraph(data['pitch'], styles['Body']))
    story.append(Spacer(1, 12))

    # Brand Direction with options parsing
    story.append(Paragraph("Brand Direction", styles['Heading']))
    brand_text = data['brand']

    options = re.split(r"\*\*Option \d+: Startup Name - [^\*]+\*\*", brand_text)
    titles = re.findall(r"\*\*Option \d+: Startup Name - ([^\*]+)\*\*", brand_text)

    # Clean empty leading split
    if options and options[0].strip() == "":
        options = options[1:]

    for i, option_text in enumerate(options):
        title = titles[i] if i < len(titles) else f"Option {i+1}"
        story.append(Paragraph(f"Option {i+1}: {title}", styles['Heading']))

        option_text_clean = clean_markdown(option_text)
        for line in option_text_clean.strip().split('\n'):
            line = line.strip()
            if line:
                story.append(Paragraph(line, styles['Body']))
        story.append(Spacer(1, 12))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# --- Main workflow ---

def run_pitchcraft_workflow(idea, tone):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    first_name = extract_first_name(names)
    tagline = tagline_agent(first_name, tone)
    pitch_text = pitch_agent(idea_summary, tone)
    audience = audience_agent(idea_summary)
    brand = brand_agent(first_name, tone)
    return report_agent(first_name, tagline, pitch_text, audience, brand)

# --- Streamlit UI ---

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")

tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

result = None

if st.button("Generate Pitch"):
    if not idea.strip():
        st.warning("Please enter your idea first.")
    else:
        with st.spinner("Generating your startup pitch..."):
            result = run_pitchcraft_workflow(idea, tone)
            if result:
                st.success("Pitch Generated!")
                st.markdown(f"### 🏷 **Name:** {result['name']}")
                st.markdown(f"**Tagline:** {result['tagline']}")
                st.markdown(f"**Problem:** {result['problem']}")
                st.markdown(f"**Solution:** {result['solution']}")
                st.markdown(f"**Audience:** {result['audience']}")
                st.markdown(f"**Pitch:** {result['pitch']}")
                st.markdown(f"**Brand Direction:** {result['brand']}")

                pdf_bytes = create_pitch_pdf(result)

                st.download_button(
                    label="Download Pitch as PDF",
                    data=pdf_bytes,
                    file_name=f"{result['name'].replace(' ', '_')}_pitch.pdf",
                    mime="application/pdf",
                )

