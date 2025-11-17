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
        return data.get("availability", "unknown")
    except Exception as e:
        return f"error: {str(e)}"

def map_domain_status(status):
    status = status.upper()
    if status == "TRUE":
        return "Domain is available"
    elif status == "FALSE":
        return "Domain is taken"
    else:
        return "Unable to check status"

# --- Pollinations logo generation ---

def generate_logo(prompt):
    url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(prompt)
    return url

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
    
def run_completion(prompt: str):
    response = completion(
        model="groq/llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        api_key=st.secrets["GROQ_API_KEY"],
    )
    return response["choices"][0]["message"]["content"].strip()

# --- Agents --- (same as your existing ones) ---

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
The names should be creative but easy to understand and remember.  
They must clearly relate to farming, agriculture, or helping farmers.  
Avoid generic words like "AI", "Tech" and avoid complex or hard-to-pronounce names.  
Do NOT include any periods (.) or punctuation after the names.  
Names only.
"""
    return run_completion(prompt)

# ... (rest of your agents: tagline_agent, pitch_agent, audience_agent, brand_agent, website_agent, social_media_agent, competitor_analysis_agent, financials_agent)

# --- Report generator and workflow (unchanged) ---

def report_agent(name, tagline, pitch, audience, brand, idea_summary):
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
        "idea_summary": idea_summary,
    }

def run_name_generation(idea):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    return idea_summary, names

def run_full_generation(idea_summary, selected_name, tone, generate_flags):
    results = {}
    if generate_flags.get("tagline", False):
        results['tagline'] = tagline_agent(selected_name, tone)
    if generate_flags.get("pitch", False):
        results['pitch'] = pitch_agent(idea_summary, tone)
    if generate_flags.get("audience", False):
        results['audience'] = audience_agent(idea_summary)
    if generate_flags.get("brand", False):
        results['brand'] = brand_agent(selected_name, tone)
    if generate_flags.get("website", False):
        results['website'] = website_agent(selected_name, tone)
    if generate_flags.get("social_media", False):
        results['social_media'] = social_media_agent(selected_name, tone)
    if generate_flags.get("competitor", False):
        results['competitor'] = competitor_analysis_agent(idea_summary)
    if generate_flags.get("financials", False):
        results['financials'] = financials_agent(selected_name)
    results.update(report_agent(
        selected_name,
        results.get('tagline', ''),
        results.get('pitch', ''),
        results.get('audience', ''),
        results.get('brand', ''),
        idea_summary,
    ))
    return results

# --- Main Streamlit UI ---

if 'names_generated' not in st.session_state:
    st.session_state['names_generated'] = []
if 'finalized_name' not in st.session_state:
    st.session_state['finalized_name'] = None
if 'idea_summary' not in st.session_state:
    st.session_state['idea_summary'] = None

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")
tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

if idea.strip():
    # Reset if idea changed
    if st.session_state.get('last_idea', '') != idea:
        st.session_state['names_generated'] = []
        st.session_state['finalized_name'] = None
        st.session_state['idea_summary'] = None
        st.session_state['last_idea'] = idea

    if not st.session_state['names_generated']:
        with st.spinner("Generating startup names..."):
            idea_summary, names_text = run_name_generation(idea)
            # Parse names list
            name_options = []
            for line in names_text.split('\n'):
                line = line.strip()
                if line and len(line) > 2 and line[0].isdigit() and line[1] == '.':
                    name = line.split('.', 1)[1].strip()
                    name_options.append(name)

            st.session_state['names_generated'] = name_options
            st.session_state['idea_summary'] = idea_summary
    else:
        name_options = st.session_state['names_generated']
        idea_summary = st.session_state['idea_summary']

    if st.session_state['finalized_name'] is None:
        selected_name = st.selectbox("Select a startup name", name_options)

        custom_name = st.text_input("Or enter your own startup name")

        final_name = custom_name.strip() if custom_name.strip() else selected_name

        domain_to_check = final_name.replace(" ", "") + ".com"
        raw_availability = check_domain_availability(domain_to_check)
        availability = map_domain_status(raw_availability)

        st.markdown(f"**Domain check for `{domain_to_check}`:** **{availability}**")

        if st.button("Finalize Name"):
            st.session_state['finalized_name'] = final_name
            st.experimental_rerun()

    else:
        st.markdown(f"**Finalized Startup Name:** {st.session_state['finalized_name']}")

        # Pollinations logo generation integration
        if st.button("Generate Logo with Pollinations AI"):
            with st.spinner("Generating logo..."):
                prompt = f"Logo for {st.session_state['finalized_name']}"
                logo_url = generate_logo(prompt)
                st.session_state['logo_url'] = logo_url

        if 'logo_url' in st.session_state:
            st.image(st.session_state['logo_url'], caption="Generated Logo", use_column_width=True)
            st.markdown(f"[Download Logo]({st.session_state['logo_url']})")

        generate_tagline = st.checkbox("Generate Tagline", value=True)
        generate_pitch = st.checkbox("Generate Elevator Pitch", value=True)
        generate_audience = st.checkbox("Generate Target Audience & Pain Points", value=True)
        generate_brand = st.checkbox("Generate Brand Direction", value=True)
        generate_website = st.checkbox("Generate Website (HTML/CSS/JS)", value=False)
        generate_social_media = st.checkbox("Generate Social Media Post Ideas", value=False)
        generate_competitor = st.checkbox("Generate Competitor Analysis", value=False)
        generate_financials = st.checkbox("Generate Financial Projections", value=False)

        if st.button("Generate Selected Assets"):
            generate_flags = {
                "tagline": generate_tagline,
                "pitch": generate_pitch,
                "audience": generate_audience,
                "brand": generate_brand,
                "website": generate_website,
                "social_media": generate_social_media,
                "competitor": generate_competitor,
                "financials": generate_financials,
            }
            with st.spinner("Generating your startup assets..."):
                result = run_full_generation(idea_summary, st.session_state['finalized_name'], tone, generate_flags)

            st.success("Generation Complete!")

            if generate_tagline:
                st.markdown(f"### Tagline\n{result.get('tagline','')}")
            if generate_pitch:
                st.markdown(f"### Elevator Pitch\n{result.get('pitch','')}")
            if generate_audience:
                st.markdown(f"### Target Audience & Pain Points\n{result.get('audience','')}")
            if generate_brand:
                st.markdown(f"### Brand Direction\n{result.get('brand','')}")
            if generate_competitor:
                st.markdown(f"### Competitor Analysis\n{result.get('competitor','')}")
            if generate_financials:
                st.markdown(f"### Financial Projections\n{result.get('financials','')}")
            if generate_social_media:
                st.markdown(f"### Social Media Post Ideas\n{result.get('social_media','')}")

            if generate_website:
                st.markdown("### Website Code")
                website_code = result.get('website','')

                # Parse website agent output into HTML, CSS, JS parts
                html_code = css_code = js_code = ""
                html_match = re.search(r"(?:```html|<html>)(.*?)(?:```|</html>)", website_code, re.DOTALL | re.IGNORECASE)
                css_match = re.search(r"(?:```css)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)
                js_match = re.search(r"(?:```js|```javascript)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)

                if html_match:
                    html_code = html_match.group(1).strip()
                if css_match:
                    css_code = css_match.group(1).strip()
                if js_match:
                    js_code = js_match.group(1).strip()

                if not (html_code and css_code and js_code):
                    parts = re.split(r"\d\)\s*[Hh][Tt][Mm][Ll]|CSS|JavaScript|JS", website_code)
                    if len(parts) >= 4:
                        html_code = parts[1].strip()
                        css_code = parts[2].strip()
                        js_code = parts[3].strip()

                with st.expander("HTML"):
                    st.code(html_code, language="html")
                with st.expander("CSS"):
                    st.code(css_code, language="css")
                with st.expander("JavaScript"):
                    st.code(js_code, language="javascript")

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    zip_file.writestr("index.html", html_code)
                    zip_file.writestr("styles.css", css_code)
                    zip_file.writestr("scripts.js", js_code)
                zip_buffer.seek(0)

                st.download_button(
                    label="Download Website Files (ZIP)",
                    data=zip_buffer,
                    file_name=f"{st.session_state['finalized_name'].replace(' ','_')}_website.zip",
                    mime="application/zip"
                )
