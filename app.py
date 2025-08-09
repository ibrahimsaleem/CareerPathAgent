from flask import Flask, request, render_template, render_template_string, Response, session  # <-- add session
import logging
import time
import os
from pathlib import Path
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Google Gemini AI client via environment variable
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
if not GENAI_API_KEY:
    raise RuntimeError("Environment variable GENAI_API_KEY is required")
client = genai.Client(api_key=GENAI_API_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "development-insecure-key")  # set via env in production

# Paths
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/recommend", methods=["GET"])
def recommend():
    # Collect user inputs
    name  = request.args.get("name", "").strip()
    age   = request.args.get("age", "").strip()
    exp   = request.args.get("experience", "").strip()
    certs = request.args.get("current_certs", "").strip()
    intr  = request.args.get("interest", "").strip()
    tf    = request.args.get("timeframe", "").strip()
    topic = request.args.get("topic", "cybersecurity").strip()  # New: topic field
    
    # Build profile details dynamically
    profile_lines = []
    if name:
        profile_lines.append(f"- Name: {name}")
    if age:
        profile_lines.append(f"- Age: {age}")
    if exp:
        profile_lines.append(f"- Experience Level: {exp}")
    if certs:
        profile_lines.append(f"- Current Certifications: {certs}")
    if intr:
        profile_lines.append(f"- Areas of Interest: {intr}")
    profile_lines.append(f"- Topic: {topic.capitalize()}")
    profile_text = "\n".join(profile_lines)
    
    # Save the user profile including topic into session for later use
    session["user_profile"] = {
        "name": name,
        "age": age,
        "experience": exp,
        "current_certs": certs,
        "interest": intr,
        "topic": topic
    }
    
    # Optionally enrich the roadmap generation with static reference context
    reference_context = ""
    try:
        if topic == "cybersecurity":
            with open((DATA_DIR / "CybersecurityRoadmap.txt"), "r", encoding="utf-8") as f:
                reference_context = f.read().strip()
        elif topic == "data-analysis":
            with open((DATA_DIR / "DataAnalystroadmap.txt"), "r", encoding="utf-8") as f:
                reference_context = f.read().strip()
    except Exception as e:
        logging.error(f"Could not load reference context for roadmap generation: {e}")

    # Build prompt, now tailoring the roadmap to the selected topic and including reference context
    prompt = f"""
You are a {topic} career advisor with a fun and personal touch. Based on the user's profile, generate a personalized {topic} certification roadmap and guidance for that person, mentioning their name.

**IMPORTANT**: Return a self‑contained HTML fragment only.
- Wrap each phase in <div class="roadmap-phase">…</div>.
- Use <h2>, <h3>, <ul>, <li> for structure.
- No external CSS or JS—just the fragment.

User Profile:
{profile_text}
Desired Roadmap Timeframe: {tf}

REFERENCE CONTEXT (use to keep recommendations up-to-date and structured):
{reference_context}
"""
    logging.info("Requesting HTML roadmap from Gemini AI…")
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html_fragment = resp.text.strip() or "<p>No roadmap generated.</p>"
        return Response(html_fragment, status=200, mimetype="text/html")
    except Exception as e:
        logging.exception("Error generating roadmap")
        return Response(f"<p style='color:red;'>Error: {e}</p>", status=500, mimetype="text/html")
        
@app.route("/explain-node", methods=["GET"])
def explain_node():
    title = request.args.get("title", "").strip()
    if not title:
        return "Missing node title", 400, {"Content-Type": "text/plain; charset=utf-8"}
    
    # Retrieve the topic from request or session
    topic = request.args.get("topic", "").strip() or session.get("user_profile", {}).get("topic", "cybersecurity")
    
    # Collect optional personal parameters
    name          = request.args.get("name", "").strip() or session.get("user_profile", {}).get("name", "")
    age           = request.args.get("age", "").strip() or session.get("user_profile", {}).get("age", "")
    experience    = request.args.get("experience", "").strip() or session.get("user_profile", {}).get("experience", "")
    current_certs = request.args.get("current_certs", "").strip() or session.get("user_profile", {}).get("current_certs", "")
    interest      = request.args.get("interest", "").strip() or session.get("user_profile", {}).get("interest", "")
    
    # Build profile with non-empty fields
    profile_lines = []
    if name:
        profile_lines.append(f"- Name: {name}")
    if age:
        profile_lines.append(f"- Age: {age}")
    if experience:
        profile_lines.append(f"- Experience Level: {experience}")
    if current_certs:
        profile_lines.append(f"- Current Certifications: {current_certs}")
    if interest:
        profile_lines.append(f"- Areas of Interest: {interest}")
    profile_lines.append(f"- Topic: {topic.capitalize()}")
    profile_text = "\n".join(profile_lines)
    
    # Load roadmap context from local data folder
    # Add additional elif blocks here to support more roadmap files for other topics
    learningpath_context = ""
    try:
        if topic == "data-analysis":
            with open((DATA_DIR / "DataAnalystroadmap.txt"), "r", encoding="utf-8") as f:
                learningpath_context = f.read().strip()
        elif topic == "cybersecurity":
            with open((DATA_DIR / "cyberlearningpath.txt"), "r", encoding="utf-8") as f:
                learningpath_context = f.read().strip()
        # Example of how to add more topics:
        # elif topic == "ai-engineering":
        #     with open((DATA_DIR / "ailearningpath.txt"), "r", encoding="utf-8") as f:
        #         learningpath_context = f.read().strip()
    except Exception as e:
        logging.error(f"Could not load roadmap context for topic '{topic}': {e}")
    # prompt = f"""Teach the topic '{title}' in a concise, personal, and fun tutorial style tailored for {topic.replace('-', ' ')} which a topic from roadmap context if user is on this topci assume he now know pervious topic as he will be going one by one.
    prompt = f""" Teach the topic '{title}' in a concise, personal, and fun tutorial style tailored to the '{topic.replace('-', ' ')}' section of the roadmap. Assume the learner has already know little bit about all previous topics and is following the learning path step by step.

User Profile:
{profile_text}

Learning Path Context:
{learningpath_context}

**IMPORTANT**: Return a self-contained HTML fragment only.  
- Wrap the explanation in appropriate HTML elements (e.g. <div>, <h2>, <p>).
- Do not include any extra text.

Provide a short, clear explanation on this topic in the context of {topic.replace('-', ' ')} certifications and training."""
    
    logging.info(f"Requesting explanation for node: {title} with profile:\n{profile_text or 'No extra profile provided.'}")
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html_response = resp.text.strip() or "<div>No explanation found.</div>"
        return Response(html_response, status=200, mimetype="text/html")
    except Exception as e:
        logging.exception("Error during node explanation")
        return f"<p style='color:red;'>❌ Error: {e}</p>", 500, {"Content-Type": "text/html"}
    
if __name__ == "__main__":
    # In production, disable debug and use a proper WSGI server
    app.run(host="0.0.0.0", port=5000, debug=False)
