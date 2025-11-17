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
from PIL import Image

domainsduck_key = st.secrets["DOMAINDUCK_API_KEY"]

# Load CSS from external file
css_path = Path(__file__).parent / "style.css"
def local_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass  # ignore if no CSS file

local_css(css_path)

st.set_page_config(page_title="PitchCraft - AI Startup Partner", layout="centered")

st.title("PitchCraft – Your AI Startup Partner")
st.markdown(
    """
Generate **startup content dynamically**.  
Enter your startup idea, select tone, and toggle which assets to generate.
"""
)

def create_pitch_pdf(pitch_text, startup_name):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=4, fontSize=12, leading=16))  # 4 = TA_JUSTIFY

    flowables = []
    flowables.append(Paragraph(f"{startup_name} - Elevator Pitch", styles['Title']))
    flowables.append(Spacer(1, 12))

    for para in pitch_text.split('\n\n'):
        flowables.append(Paragraph(para.strip(), styles['Justify']))
        flowables.append(Spacer(1, 12))

    doc.build(flowables)
    buffer.seek(0)
    return buffer

# --- Pollinations image generation for logo preview ---
def generate_stability_image(prompt: str) -> Image.Image | None:
    api_url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    api_key = st.secrets["STABILITY_API_KEY"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/png",  # receive raw image bytes
        "stability-client-id": "pitchcraft-app",
        "stability-client-user-id": "user-unique-id",  # you can make this dynamic if you want
        "stability-client-version": "1.0",
    }

    data = {
        "prompt": prompt,
        "output_format": "png",
        "cfg_scale": 7,
        "aspect_ratio": "1:1",
        "model": "sd3"
    }

    # dummy field for multipart/form-data
    files = {"none": ""}

    try:
        response = requests.post(api_url, headers=headers, data=data, files=files)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        return image
    except Exception as e:
        st.error(f"Failed to generate logo: {e}")
        return None

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

# --- Helpers ---
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

def run_completion(prompt: str):
    response = completion(
        model="groq/llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        api_key=st.secrets["GROQ_API_KEY"],
    )
    return response["choices"][0]["message"]["content"].strip()

# --- Agents ---
def idea_agent(idea):
    prompt = f"""
You are a seasoned startup strategist.

Analyze this startup idea carefully.

Provide a concise summary (2-3 sentences) that clearly identifies:
- The main problem the startup addresses
- The core solution it offers

Make the summary compelling and insightful.

Startup Idea:
{idea}

Output only the summary text without any additional explanation.
"""
    return run_completion(prompt)

def name_agent(idea):
    prompt = f"""
Generate exactly 3 unique startup names as a numbered list ONLY.

Do NOT include any explanations, descriptions, or pronunciation guides.

Avoid generic words like "AI" and "Tech". The names should be easy to pronounce and SEO Friendly.

Startup idea:
{idea}

Output only the names as a numbered list.
"""
    return run_completion(prompt)

def tagline_agent(name, idea, tone):
    prompt = f"""
You are an expert copywriter.

Create a catchy and memorable tagline for the startup named "{name}".

The startup idea is:
{idea}

Use the tone: {tone} (e.g., Formal, Casual, Fun, Investor).

Keep it short (under 10 words).

Output only the tagline text without any explanations or extra text.
"""
    return run_completion(prompt)

def pitch_agent(name, idea, tone):
    prompt = f"""
You are a skilled marketer.

Write a compelling two-paragraph elevator pitch for the startup named "{name}".

Include:
- A clear statement of the problem and its impact
- A description of the solution and unique value proposition

The startup idea is:
{idea}

Use the tone: {tone}.

Output only the pitch text without any explanations or extra text.
"""
    return run_completion(prompt)

def audience_agent(name, idea):
    prompt = f"""
You are a market analyst.

Define the target audience and their pain points for the startup named "{name}".

The startup idea is:
{idea}

Format your answer as bullet points grouped under:
- Primary Target Audience
- Secondary Target Audience
- Pain Points

Use clear and concise language.

Output only the bullet points without explanations or additional text.
"""
    return run_completion(prompt)

def brand_agent(name, idea, tone):
    prompt = f"""
You are a branding expert.

Suggest a professional color palette (with hex codes) and a simple but effective logo concept idea for the startup named "{name}".

The startup idea is:
{idea}

Consider the tone: {tone}.

Describe:
- Primary and secondary colors
- Logo style and symbolism

Output only the paragraphs describing the color palette and logo concept without explanations or extra text.
"""
    return run_completion(prompt)

def website_agent(name, idea, tone):
    prompt = f"""
You are a professional front-end web developer and UI/UX designer.

Generate a modern, fully responsive, visually appealing single-page website for the startup named "{name}".

The startup idea is:
{idea}

Requirements:
- Provide three separate code blocks for HTML, CSS, and JavaScript.
- Use clean, semantic HTML5 markup with proper ARIA attributes and alt text for accessibility.
- Use Google Fonts: 'Poppins' for headings and 'Roboto' for body text, loaded in the HTML head.
- The CSS should include detailed styling for:
  - Responsive layout with CSS Grid and Flexbox
  - Sticky header with smooth background color transition on scroll
  - Smooth fade-in animations on scroll for sections
  - Buttons with rounded corners, subtle shadows, hover and focus states
  - Consistent spacing, readable font sizes, and a clear visual hierarchy
  - Should have centralized justified layout                                              
- JavaScript should handle:
  - Smooth scrolling navigation for internal links
  - Simple client-side form validation with inline error messages for the contact form (validate required fields and email format)
  - Add subtle animations or transitions triggered on scroll
- The page structure must include these sections:

  1. Hero section:
     - Large heading with the startup name
     - Tagline in a smaller font
     - Centered call-to-action button

  2. About section:
     - Clear description of the problem the startup solves

  3. Features section:
     - At least 3 feature cards, each with an icon (emoji or inline SVG), title, and short description

  4. Services section:
     - At least 4 Services each with an icon (emoji or inline SVG), title, and short description

  5. Testimonials section:
     - 3 testimonials with user names, photos (use placeholder images), and quotes

  6. Contact section:
     - Contact form with Name, Email, Message fields
     - All inputs required with proper validation
     - Submit button with hover effect

- Include SEO-friendly meta tags (title, description) reflecting the startup name and tone.
- Ensure the website is accessible, mobile-friendly, and visually balanced.
- Use only vanilla CSS and JavaScript (no external CSS frameworks or libraries).

Output your response in three separate labeled code blocks:

1) HTML code  
2) CSS code  
3) JavaScript code  

Do NOT include explanations or any text outside the code blocks.
"""
    return run_completion(prompt)

def social_media_agent(name, idea, tone):
    prompt = f"""
You are a social media strategist.

Create a list of 5 creative social media post ideas for the startup named "{name}".

The startup idea is:
{idea}

Use a {tone} tone.

Each idea should be short, engaging, and suitable for platforms like Twitter or Instagram.

Output only a numbered list without explanations or additional text.
"""
    return run_completion(prompt)

def competitor_analysis_agent(name, idea):
    prompt = f"""
You are a business analyst.

Provide a brief competitor analysis for the startup named "{name}".

The startup idea is:
{idea}

Include:
- Key competitors
- What differentiates this startup from competitors
- Potential market challenges

Write in clear, concise paragraphs.

Output only the analysis text without explanations or extra text.
"""
    return run_completion(prompt)

def financials_agent(name, idea):
    prompt = f"""
You are a financial advisor.

Create a simple 3-year financial projection outline for the startup named "{name}".

The startup idea is:
{idea}

Include expected:
- Revenue streams
- Key costs
- Profit estimates

Write in bullet points, clear and concise.

Output only the financial outline without explanations or extra text.
"""
    return run_completion(prompt)

# --- Report generator ---
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

# --- Workflow split into parts ---
def run_name_generation(idea):
    idea_summary = idea_agent(idea)
    names = name_agent(idea_summary)
    return idea_summary, names

def run_full_generation(idea_summary, selected_name, tone, generate_flags):
    results = {}
    if generate_flags.get("tagline", False):
        results['tagline'] = tagline_agent(selected_name, idea_summary, tone)
    if generate_flags.get("pitch", False):
        results['pitch'] = pitch_agent(selected_name, idea_summary, tone)
    if generate_flags.get("audience", False):
        results['audience'] = audience_agent(selected_name, idea_summary)
    if generate_flags.get("brand", False):
        results['brand'] = brand_agent(selected_name, idea_summary, tone)
    if generate_flags.get("website", False):
        results['website'] = website_agent(selected_name, idea_summary, tone)
    if generate_flags.get("social_media", False):
        results['social_media'] = social_media_agent(selected_name, idea_summary, tone)
    if generate_flags.get("competitor", False):
        results['competitor'] = competitor_analysis_agent(selected_name, idea_summary)
    if generate_flags.get("financials", False):
        results['financials'] = financials_agent(selected_name, idea_summary)
    results.update(report_agent(
        selected_name,
        results.get('tagline', ''),
        results.get('pitch', ''),
        results.get('audience', ''),
        results.get('brand', ''),
        idea_summary,
    ))
    return results

# --- Streamlit UI ---

if 'names_generated' not in st.session_state:
    st.session_state['names_generated'] = []
if 'finalized_name' not in st.session_state:
    st.session_state['finalized_name'] = None
if 'idea_summary' not in st.session_state:
    st.session_state['idea_summary'] = None
if 'last_idea' not in st.session_state:
    st.session_state['last_idea'] = ""
if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False

idea = st.text_area("Enter your startup idea", placeholder="e.g. An app that connects students with mentors.")
tone = st.selectbox("Select tone", ["Formal", "Casual", "Fun", "Investor"])

# Reset session states if idea changed
if st.session_state['last_idea'] != idea:
    st.session_state['last_idea'] = idea
    st.session_state['submitted'] = False
    st.session_state['names_generated'] = []
    st.session_state['finalized_name'] = None
    st.session_state['idea_summary'] = None

submitted = st.button("Submit")

if submitted:
    if not idea.strip():
        st.warning("Please enter your startup idea before submitting.")
    else:
        st.session_state['submitted'] = True
        with st.spinner("Generating startup names..."):
            idea_summary, names_text = run_name_generation(idea)
            name_options = []
            for line in names_text.split('\n'):
                line = line.strip()
                if line and len(line) > 2 and line[0].isdigit() and line[1] == '.':
                    name = line.split('.', 1)[1].strip()
                    name_options.append(name)

            st.session_state['names_generated'] = name_options
            st.session_state['idea_summary'] = idea_summary
        st.rerun()

if st.session_state['submitted']:
    idea_summary = st.session_state['idea_summary']
    name_options = st.session_state['names_generated']

    if st.session_state['finalized_name'] is None:
        if name_options:
            selected_name = st.radio("Select a startup name", name_options)
        else:
            st.warning("No AI-generated names available. Please enter your own startup name below.")
            selected_name = None
        
        custom_name = st.text_input("Or enter your own startup name (optional)")

        final_name = custom_name.strip() if custom_name.strip() else selected_name
        
        if final_name and len(final_name) > 0:
            domain_to_check = final_name.replace(" ", "") + ".com"
            raw_availability = check_domain_availability(domain_to_check)
            availability = map_domain_status(raw_availability)
            st.markdown(f"**Domain check for `{domain_to_check}`:** **{availability}**")
        else:
            st.warning("Please select or enter a valid startup name.")
            domain_to_check = None
            availability = None

        if st.button("Finalize Name"):
            st.session_state['finalized_name'] = final_name
            st.rerun()
    else:
        st.markdown(f"**Finalized Startup Name:** {st.session_state['finalized_name']}")

        logo_prompt = (
            f"Create a creative, iconic logo concept for the startup named '{st.session_state['finalized_name']}'. "
            f"The logo should be bold, memorable, and visually represent the core values of the startup. "
            f"Use the brand's suggested color palette with primary and secondary colors. "
            f"Include symbolic elements related to the startup's mission, avoiding minimal or sleek styles. "
            f"The design should stand out and be suitable for various media, including digital and print."
        )
    
        logo_image = generate_stability_image(logo_prompt)
        if logo_image:
            st.image(logo_image, caption="Logo Preview (AI-generated)", use_column_width=True)


        # Asset toggles
        generate_tagline = st.checkbox("Generate Tagline", value=True)
        generate_pitch = st.checkbox("Generate Elevator Pitch", value=True)
        generate_audience = st.checkbox("Generate Target Audience & Pain Points", value=True)
        generate_brand = st.checkbox("Generate Brand Direction", value=True)
        generate_website = st.checkbox("Generate Website (HTML/CSS/JS)", value=True)
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
                # Use existing idea summary (don't re-run idea_agent with name only)
                result = run_full_generation(
                    idea_summary,
                    st.session_state['finalized_name'],
                    tone,
                    generate_flags
                )

            st.success("Generation Complete!")

            tabs = st.tabs(["Tagline", "Pitch", "Audience", "Brand", "Competitor", "Financials", "Social Media", "Website Preview", "Website Code"])

            if generate_tagline:
                with tabs[0]:
                    st.markdown(f"### Tagline\n{result.get('tagline','')}")

            if generate_pitch:
                with tabs[1]:
                    pitch_text = result.get('pitch', '')
                    st.markdown(f"### Elevator Pitch\n{pitch_text}")
            
                    if pitch_text:
                        pdf_buffer = create_pitch_pdf(pitch_text, st.session_state['finalized_name'])
                        st.download_button(
                            label="Download Pitch as PDF",
                            data=pdf_buffer,
                            file_name=f"{st.session_state['finalized_name'].replace(' ', '_')}_pitch.pdf",
                            mime="application/pdf"
                        )


            if generate_audience:
                with tabs[2]:
                    st.markdown(f"### Target Audience & Pain Points\n{result.get('audience','')}")

            if generate_brand:
                with tabs[3]:
                    st.markdown(f"### Brand Direction\n{result.get('brand','')}")

            if generate_competitor:
                with tabs[4]:
                    st.markdown(f"### Competitor Analysis\n{result.get('competitor','')}")

            if generate_financials:
                with tabs[5]:
                    st.markdown(f"### Financial Projections\n{result.get('financials','')}")

            if generate_social_media:
                with tabs[6]:
                    st.markdown(f"### Social Media Post Ideas\n{result.get('social_media','')}")

            # Website preview tab with iframe
            if generate_website:
                html_code = css_code = js_code = ""
                website_code = result.get('website','')

                html_match = re.search(r"(?:```html|<html>)(.*?)(?:```|</html>)", website_code, re.DOTALL | re.IGNORECASE)
                css_match = re.search(r"(?:```css)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)
                js_match = re.search(r"(?:```js|```javascript)(.*?)(?:```)", website_code, re.DOTALL | re.IGNORECASE)

                if html_match:
                    html_code = html_match.group(1).strip()
                if css_match:
                    css_code = css_match.group(1).strip()
                if js_match:
                    js_code = js_match.group(1).strip()
                    smooth_scroll_js = """
                    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                      anchor.addEventListener('click', function(e) {
                        e.preventDefault();
                        const targetID = this.getAttribute('href').substring(1);
                        const targetElement = document.getElementById(targetID);
                        if (targetElement) {
                          targetElement.scrollIntoView({ behavior: 'smooth' });
                        }
                      });
                    });
                    """
                    
                    js_code += smooth_scroll_js

                if not (html_code and css_code and js_code):
                    parts = re.split(r"\d\)\s*[Hh][Tt][Mm][Ll]|CSS|JavaScript|JS", website_code)
                    if len(parts) >= 4:
                        html_code = parts[1].strip()
                        css_code = parts[2].strip()
                        js_code = parts[3].strip()

                full_html = f"""
                <html>
                <head>
                <style>{css_code}</style>
                </head>
                <body>
                {html_code}
                <script>{js_code}</script>
                </body>
                </html>
                """

                with tabs[7]:
                    st.markdown("### Live Website Preview")
                    st.components.v1.html(full_html, height=600, scrolling=True)

                with tabs[8]:
                    st.markdown("### Website Code")
                    st.subheader("HTML")
                    st.code(html_code, language="html")
                    st.subheader("CSS")
                    st.code(css_code, language="css")
                    st.subheader("JavaScript")
                    st.code(js_code, language="javascript")

                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        zip_file.writestr("index.html", html_code)
                        zip_file.writestr("styles.css", css_code)
                        zip_file.writestr("script.js", js_code)
                    zip_buffer.seek(0)

                    st.download_button(
                        label="Download Website Files (ZIP)",
                        data=zip_buffer,
                        file_name=f"{st.session_state['finalized_name'].replace(' ','_')}_website.zip",
                        mime="application/zip"
                    )

else:
    st.info("Enter your startup idea and tone, then press Submit to generate startup names.")









