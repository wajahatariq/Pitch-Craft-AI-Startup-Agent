from langgraph.graph import StateGraph
from litellm import completion
from agents.idea_agent import idea_agent
from agents.name_agent import name_agent
from agents.tagline_agent import tagline_agent
from agents.pitch_agent import pitch_agent
from agents.audience_agent import audience_agent
from agents.brand_agent import brand_agent
from agents.report_agent import report_agent

def run_pitchcraft_workflow(idea: str, tone: str):
    try:
        # Step 1: Extract core idea
        idea_summary = idea_agent(idea)

        # Step 2: Generate names
        names = name_agent(idea_summary)

        # Step 3: Pick best name + tagline
        tagline = tagline_agent(names, tone)

        # Step 4: Generate problem/solution + pitch
        pitch_data = pitch_agent(idea_summary, tone)

        # Step 5: Define audience
        audience = audience_agent(idea_summary)

        # Step 6: Brand suggestions
        brand = brand_agent(names, tone)

        # Step 7: Final report
        result = report_agent(names, tagline, pitch_data, audience, brand)

        return result
    except Exception as e:
        print("Workflow error:", e)
        return None
