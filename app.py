import json
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="The Marketplace",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# STORAGE
# =========================================================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

PEOPLE_FILE = DATA_DIR / "people.json"
REQUESTS_FILE = DATA_DIR / "requests.json"
ENDORSEMENTS_FILE = DATA_DIR / "endorsements.json"


# =========================================================
# HELPERS
# =========================================================
def now_str() -> str:
    return datetime.now().strftime("%d %b %Y, %H:%M")


def load_json(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text: str) -> str:
    return text.strip().lower()


def split_csv(text: str) -> list[str]:
    if not text:
        return []
    return [x.strip() for x in text.split(",") if x.strip()]


def unique_clean(items: list[str]) -> list[str]:
    seen = set()
    clean = []
    for item in items:
        key = slugify(item)
        if key not in seen:
            clean.append(item.strip())
            seen.add(key)
    return clean


def person_by_id(person_id: str, people: list[dict]) -> dict | None:
    for p in people:
        if p["id"] == person_id:
            return p
    return None


def request_by_id(request_id: str, requests_data: list[dict]) -> dict | None:
    for r in requests_data:
        if r["id"] == request_id:
            return r
    return None


def endorsement_count(person_id: str, endorsements: list[dict]) -> int:
    return sum(1 for e in endorsements if e["to_person_id"] == person_id)


def completed_contributions(person_id: str, requests_data: list[dict]) -> int:
    return sum(
        1
        for r in requests_data
        if r.get("matched_person_id") == person_id and r.get("status") == "Completed"
    )


def badge(label: str, bg: str = "#EEF2FF", fg: str = "#3730A3") -> str:
    return (
        f"<span style='display:inline-block;padding:4px 10px;margin:4px 6px 0 0;"
        f"border-radius:999px;background:{bg};color:{fg};font-size:0.85rem;"
        f"font-weight:600;border:1px solid rgba(0,0,0,0.05);'>{label}</span>"
    )


def render_tag_list(tags: list[str], bg: str, fg: str):
    if not tags:
        st.write("—")
        return
    html = "".join([badge(tag, bg, fg) for tag in tags])
    st.markdown(html, unsafe_allow_html=True)


def all_skills_for_person(person: dict) -> list[str]:
    return (
        person.get("core_skills", [])
        + person.get("hidden_skills", [])
        + person.get("passion_skills", [])
        + person.get("interests", [])
    )


def calculate_match_score(person: dict, request: dict, endorsements: list[dict]) -> tuple[int, dict]:
    person_skills = {slugify(x): x for x in all_skills_for_person(person)}
    request_skills = {slugify(x): x for x in request.get("skills_needed", [])}
    request_tags = {slugify(x): x for x in request.get("tags", [])}

    matched_required = sorted(set(person_skills.keys()) & set(request_skills.keys()))
    matched_tags = sorted(set(person_skills.keys()) & set(request_tags.keys()))

    score = 0
    score += len(matched_required) * 32
    score += len(matched_tags) * 10

    if person.get("available_for_marketplace"):
        score += 8

    if request.get("time_commitment") in person.get("preferred_commitment", []):
        score += 10

    # Hidden/passion boost
    hidden = {slugify(x): x for x in person.get("hidden_skills", [])}
    passion = {slugify(x): x for x in person.get("passion_skills", [])}

    hidden_hits = sorted(set(hidden.keys()) & set(request_skills.keys()))
    passion_hits = sorted(set(passion.keys()) & set(request_skills.keys()))

    score += len(hidden_hits) * 8
    score += len(passion_hits) * 10

    score += min(endorsement_count(person["id"], endorsements), 10) * 2

    explanation = {
        "matched_required": [person_skills[x] for x in matched_required],
        "matched_tags": [person_skills[x] for x in matched_tags],
        "hidden_hits": [hidden[x] for x in hidden_hits],
        "passion_hits": [passion[x] for x in passion_hits],
    }
    return score, explanation


def top_matches_for_request(
    request: dict,
    people: list[dict],
    endorsements: list[dict],
    top_n: int = 5,
) -> list[dict]:
    matches = []
    for person in people:
        score, explanation = calculate_match_score(person, request, endorsements)
        if score > 0:
            matches.append(
                {
                    "person": person,
                    "score": score,
                    "explanation": explanation,
                    "endorsements": endorsement_count(person["id"], endorsements),
                }
            )
    matches.sort(key=lambda x: (x["score"], x["endorsements"]), reverse=True)
    return matches[:top_n]


def init_demo_data():
    if PEOPLE_FILE.exists() and REQUESTS_FILE.exists() and ENDORSEMENTS_FILE.exists():
        return

    people = [
        {
            "id": str(uuid.uuid4()),
            "name": "Sarah Larke",
            "role_title": "People & Culture Manager",
            "directorate": "People & Culture",
            "about": "Focused on workforce transformation, hidden talent and practical innovation.",
            "core_skills": ["Strategic workforce planning", "Leadership development", "Workshop facilitation"],
            "hidden_skills": ["Data storytelling", "Poster design", "Change communications"],
            "passion_skills": ["Streamlit app building", "Prototype design", "People analytics"],
            "interests": ["AI", "Innovation", "Skills-based organisations"],
            "preferred_commitment": ["1-2 hours", "Half day"],
            "available_for_marketplace": True,
            "created_at": now_str(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Imran Hussain",
            "role_title": "Business Support Officer",
            "directorate": "Communities",
            "about": "Strong organiser with hidden digital and design capability.",
            "core_skills": ["Coordination", "Diary management", "Stakeholder support"],
            "hidden_skills": ["Excel dashboards", "Canva design", "Event planning"],
            "passion_skills": ["Graphic design", "Visual storytelling", "Power BI"],
            "interests": ["Community events", "Digital tools"],
            "preferred_commitment": ["1-2 hours", "Half day", "Project sprint"],
            "available_for_marketplace": True,
            "created_at": now_str(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chloe Bennett",
            "role_title": "Housing Support Officer",
            "directorate": "Housing",
            "about": "Passionate about improving resident experience through insight and service design.",
            "core_skills": ["Resident support", "Partnership working", "Case management"],
            "hidden_skills": ["Survey design", "Data analysis", "Presentation design"],
            "passion_skills": ["Service design", "User research", "Facilitation"],
            "interests": ["Resident voice", "Inclusion", "Continuous improvement"],
            "preferred_commitment": ["1-2 hours", "Half day"],
            "available_for_marketplace": True,
            "created_at": now_str(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Tom Davies",
            "role_title": "Finance Analyst",
            "directorate": "Finance",
            "about": "Analytical thinker with a passion for automation and app prototyping.",
            "core_skills": ["Budget analysis", "Forecasting", "Excel modelling"],
            "hidden_skills": ["Python", "Automation", "Data visualisation"],
            "passion_skills": ["App prototyping", "Process improvement", "AI tools"],
            "interests": ["Efficiency", "Digital innovation"],
            "preferred_commitment": ["Half day", "Project sprint"],
            "available_for_marketplace": True,
            "created_at": now_str(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Maya Patel",
            "role_title": "Communications Officer",
            "directorate": "Communications",
            "about": "Creative communicator with strong design and campaign instincts.",
            "core_skills": ["Copywriting", "Campaign planning", "Stakeholder messaging"],
            "hidden_skills": ["Video editing", "Poster design", "Facilitation"],
            "passion_skills": ["Brand design", "Storyboarding", "Workshop design"],
            "interests": ["Resident engagement", "Creative collaboration"],
            "preferred_commitment": ["1-2 hours", "Half day"],
            "available_for_marketplace": True,
            "created_at": now_str(),
        },
    ]

    requests_data = [
        {
            "id": str(uuid.uuid4()),
            "title": "Need support creating a simple engagement dashboard",
            "team": "Transformation",
            "directorate": "Corporate Services",
            "description": "Looking for someone to help build a lightweight dashboard to track engagement activity and responses.",
            "skills_needed": ["Data analysis", "Excel dashboards", "Power BI"],
            "tags": ["Insight", "Dashboard", "Engagement"],
            "time_commitment": "Half day",
            "resident_impact": "Better insight helps us target support and improve resident-facing decisions.",
            "fit_for_future_link": "Supports a more agile, insight-led and connected organisation.",
            "status": "Open",
            "created_by": "Naomi Clarke",
            "matched_person_id": None,
            "created_at": now_str(),
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Need help designing a poster for a staff event",
            "team": "Learning & Development",
            "directorate": "People & Culture",
            "description": "Looking for support to create a clear and engaging poster for an internal careers and development event.",
            "skills_needed": ["Poster design", "Canva design", "Change communications"],
            "tags": ["Design", "Events", "Communications"],
            "time_commitment": "1-2 hours",
            "resident_impact": "Better staff development supports stronger services for residents.",
            "fit_for_future_link": "Encourages collaboration and makes better use of internal talent.",
            "status": "Open",
            "created_by": "L&D Team",
            "matched_person_id": None,
            "created_at": now_str(),
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Looking for someone to help test a simple digital prototype",
            "team": "Digital Improvement",
            "directorate": "Corporate Services",
            "description": "Seeking colleagues who enjoy testing new tools and giving practical feedback.",
            "skills_needed": ["User research", "Prototype design", "App prototyping"],
            "tags": ["Digital", "Prototype", "Innovation"],
            "time_commitment": "1-2 hours",
            "resident_impact": "Faster testing helps improve digital services used by residents.",
            "fit_for_future_link": "Builds digital confidence and practical innovation across the workforce.",
            "status": "Open",
            "created_by": "Digital Team",
            "matched_person_id": None,
            "created_at": now_str(),
        },
    ]

    endorsements = []

    save_json(PEOPLE_FILE, people)
    save_json(REQUESTS_FILE, requests_data)
    save_json(ENDORSEMENTS_FILE, endorsements)


# =========================================================
# STYLING
# =========================================================
def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --bg: #F7F9FC;
            --card: rgba(255,255,255,0.88);
            --text: #10223A;
            --muted: #5F6B7A;
            --line: rgba(16,34,58,0.08);
            --brand: #0F6CBD;
            --brand-dark: #0A4F91;
            --accent: #7C3AED;
            --success: #047857;
            --gold: #B7791F;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15,108,189,0.08), transparent 30%),
                radial-gradient(circle at top right, rgba(124,58,237,0.08), transparent 25%),
                linear-gradient(180deg, #F8FBFF 0%, #F7F9FC 100%);
            color: var(--text);
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1350px;
        }

        .hero {
            padding: 2rem 2rem 1.6rem 2rem;
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(15,108,189,0.95), rgba(124,58,237,0.92));
            color: white;
            box-shadow: 0 20px 40px rgba(31,41,55,0.14);
            margin-bottom: 1.2rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 2.25rem;
            line-height: 1.1;
            letter-spacing: -0.03em;
        }

        .hero .sub {
            font-size: 1.08rem;
            color: rgba(255,255,255,0.92);
            margin-top: 0.55rem;
        }

        .hero .strap {
            display: inline-block;
            margin-top: 1rem;
            padding: 6px 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.16);
            border: 1px solid rgba(255,255,255,0.18);
            font-size: 0.9rem;
            font-weight: 600;
        }

        .section-title {
            font-size: 1.35rem;
            font-weight: 800;
            margin-top: 0.35rem;
            margin-bottom: 0.9rem;
            color: var(--text);
        }

        .glass-card {
            background: var(--card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1.2rem 1.2rem;
            box-shadow: 0 10px 22px rgba(16,34,58,0.06);
        }

        .metric-card {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 22px rgba(16,34,58,0.06);
            min-height: 118px;
        }

        .metric-label {
            font-size: 0.88rem;
            color: var(--muted);
            font-weight: 600;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1;
            margin-bottom: 0.35rem;
        }

        .metric-foot {
            font-size: 0.88rem;
            color: var(--muted);
        }

        .mini-card {
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.8rem;
        }

        .eyebrow {
            font-size: 0.82rem;
            color: var(--brand-dark);
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }

        .big-quote {
            font-size: 1.15rem;
            line-height: 1.6;
            font-weight: 600;
            color: var(--text);
        }

        .muted {
            color: var(--muted);
        }

        .callout {
            border-left: 4px solid var(--brand);
            padding: 0.85rem 1rem;
            background: rgba(15,108,189,0.06);
            border-radius: 10px;
            margin-top: 0.6rem;
        }

        .success-callout {
            border-left: 4px solid var(--success);
            padding: 0.85rem 1rem;
            background: rgba(4,120,87,0.07);
            border-radius: 10px;
            margin-top: 0.6rem;
        }

        .gold-callout {
            border-left: 4px solid var(--gold);
            padding: 0.85rem 1rem;
            background: rgba(183,121,31,0.08);
            border-radius: 10px;
            margin-top: 0.6rem;
        }

        .pill {
            display:inline-block;
            padding:6px 10px;
            background:#EFF6FF;
            color:#0A4F91;
            border-radius:999px;
            border:1px solid rgba(15,108,189,0.12);
            font-size:0.82rem;
            font-weight:700;
            margin-right:6px;
            margin-top:6px;
        }

        .match-score {
            display:inline-block;
            padding:10px 14px;
            background:linear-gradient(135deg, #0F6CBD, #7C3AED);
            color:white;
            border-radius:16px;
            font-weight:800;
            font-size:1rem;
            box-shadow: 0 8px 18px rgba(15,108,189,0.22);
        }

        div[data-testid="stForm"] {
            background: rgba(255,255,255,0.86);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1rem 1rem 0.2rem 1rem;
            box-shadow: 0 10px 22px rgba(16,34,58,0.06);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 20px;
        }

        .footer-note {
            font-size: 0.9rem;
            color: var(--muted);
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, foot: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-foot">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, strap: str = ""):
    strap_html = f"<div class='strap'>{strap}</div>" if strap else ""
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <div class="sub">{subtitle}</div>
            {strap_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


# =========================================================
# INIT
# =========================================================
init_demo_data()
apply_styles()

people = load_json(PEOPLE_FILE, [])
requests_data = load_json(REQUESTS_FILE, [])
endorsements = load_json(ENDORSEMENTS_FILE, [])

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("## ✨ The Marketplace")
    st.caption("Everyone Has Skills")
    page = st.radio(
        "Navigate",
        [
            "Home",
            "Skills Passports",
            "Post a Request",
            "Browse Opportunities",
            "AI Nudges",
            "Endorsements",
            "Insights",
        ],
    )
    st.markdown("---")
    st.markdown(
        """
        **Demo purpose**
        
        This prototype shows how Westminster could:
        - unlock hidden talent
        - surface aspiring and passion skills
        - connect people to value-adding opportunities
        - build trusted recognition through endorsements
        """
    )


# =========================================================
# HOME
# =========================================================
if page == "Home":
    render_hero(
        "The Marketplace",
        "Unlocking the talent we already have — making skills visible, usable and recognised across Westminster.",
        "A live demo of hidden talent, smart matching and workforce insight",
    )

    total_passports = len(people)
    open_requests = sum(1 for r in requests_data if r["status"] == "Open")
    total_endorsements = len(endorsements)
    hidden_skills_count = sum(len(p.get("hidden_skills", [])) for p in people)
    passion_skills_count = sum(len(p.get("passion_skills", [])) for p in people)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_metric_card("Skills Passports", str(total_passports), "Colleagues with visible profiles")
    with c2:
        render_metric_card("Open Opportunities", str(open_requests), "Short-term requests live now")
    with c3:
        render_metric_card("Endorsements", str(total_endorsements), "Trusted recognition of contribution")
    with c4:
        render_metric_card("Hidden Skills", str(hidden_skills_count), "Capability not used in day jobs")
    with c5:
        render_metric_card("Passion Skills", str(passion_skills_count), "Skills people want to practise more")

    st.markdown("")

    col_left, col_right = st.columns([1.15, 0.85], gap="large")

    with col_left:
        st.markdown(
            """
            <div class="glass-card">
                <div class="eyebrow">The Opportunity</div>
                <div class="big-quote">
                    Across Westminster, colleagues have valuable skills, passions and interests that often sit outside their day-to-day role.
                    Those skills can remain hidden simply because there is no easy way to see or access them.
                </div>
                <div class="callout">
                    <strong>Talent should not be limited by job titles.</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        render_section_title("How it works")
        a, b, c = st.columns(3)

        with a:
            st.markdown(
                """
                <div class="mini-card">
                    <div class="eyebrow">1. Skills Passport</div>
                    A simple profile capturing core skills, hidden skills, passion skills and interests — including capabilities not used in someone's current role.
                </div>
                """,
                unsafe_allow_html=True,
            )
        with b:
            st.markdown(
                """
                <div class="mini-card">
                    <div class="eyebrow">2. Smart Matching</div>
                    Opportunities are matched to relevant colleagues, with gentle nudges that surface hidden and aspiring talent.
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c:
            st.markdown(
                """
                <div class="mini-card">
                    <div class="eyebrow">3. Endorsements</div>
                    Contributions are recognised and trusted based on real experience — not just role title.
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_right:
        st.markdown(
            """
            <div class="glass-card">
                <div class="eyebrow">Why this matters</div>
                <ul style="margin-top: 0.5rem; line-height: 1.8;">
                    <li>Makes hidden talent visible</li>
                    <li>Helps people practise passion skills in a real, value-adding environment</li>
                    <li>Supports fairer access to opportunities</li>
                    <li>Reduces duplication and helps teams solve problems faster</li>
                    <li>Builds a live picture of workforce capability over time</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        st.markdown(
            """
            <div class="success-callout">
                <strong>Fit for the Future:</strong> supports a more agile, skilled and connected workforce.
            </div>
            <div class="gold-callout">
                <strong>Resident impact:</strong> better use of internal talent can improve delivery, speed up problem solving and support stronger outcomes for residents.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")
    render_section_title("Demo journey")
    st.write(
        "For the strongest presentation flow, show: **Skills Passport → Opportunity → AI Match → Endorsement → Insights**."
    )


# =========================================================
# SKILLS PASSPORTS
# =========================================================
elif page == "Skills Passports":
    render_hero(
        "Skills Passports",
        "A living picture of what people can do — including hidden capability and the skills they are passionate about practising.",
        "Visible talent beyond job titles",
    )

    search = st.text_input("Search by name, role, skill, passion or interest")

    filtered = []
    for person in people:
        haystack = " ".join(
            [
                person.get("name", ""),
                person.get("role_title", ""),
                person.get("directorate", ""),
                person.get("about", ""),
                " ".join(person.get("core_skills", [])),
                " ".join(person.get("hidden_skills", [])),
                " ".join(person.get("passion_skills", [])),
                " ".join(person.get("interests", [])),
            ]
        ).lower()
        if not search or search.lower() in haystack:
            filtered.append(person)

    top1, top2 = st.columns([1.3, 0.7])
    with top1:
        render_section_title("Browse passports")
    with top2:
        st.caption(f"{len(filtered)} profile(s) shown")

    for person in filtered:
        end_count = endorsement_count(person["id"], endorsements)
        contrib_count = completed_contributions(person["id"], requests_data)

        with st.container(border=False):
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            left, right = st.columns([0.72, 0.28], gap="large")

            with left:
                st.markdown(f"### {person['name']}")
                st.write(f"**{person['role_title']}** · {person['directorate']}")
                st.caption(person.get("about", ""))

                st.markdown("**Core skills**")
                render_tag_list(person.get("core_skills", []), "#EFF6FF", "#0A4F91")

                st.markdown("**Hidden skills not used in their day job**")
                render_tag_list(person.get("hidden_skills", []), "#F5F3FF", "#5B21B6")

                st.markdown("**Passion skills they would like to practise more**")
                render_tag_list(person.get("passion_skills", []), "#ECFDF5", "#065F46")

                st.markdown("**Interests**")
                render_tag_list(person.get("interests", []), "#FFF7ED", "#9A3412")

            with right:
                render_metric_card("Endorsements", str(end_count), "Recognition from colleagues")
                st.markdown("")
                render_metric_card("Completed Contributions", str(contrib_count), "Value added through the Marketplace")
                st.markdown("")
                st.markdown(
                    f"""
                    <div class="mini-card">
                        <div class="eyebrow">Availability</div>
                        {"Available for opportunities" if person.get("available_for_marketplace") else "Not currently available"}
                        <div style="margin-top:10px;" class="muted">
                            <strong>Preferred commitment:</strong><br>
                            {", ".join(person.get("preferred_commitment", [])) if person.get("preferred_commitment") else "Not set"}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("")

    render_section_title("Create a new passport")
    with st.form("create_passport"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            role_title = st.text_input("Role title")
            directorate = st.text_input("Directorate")
            about = st.text_area("About you", height=110)
        with col2:
            core_skills = st.text_area("Core skills (comma-separated)", height=90)
            hidden_skills = st.text_area("Hidden skills not used in your day job", height=90)
            passion_skills = st.text_area("Passion skills you would like to practise more", height=90)
            interests = st.text_input("Interests (comma-separated)")
            commitment = st.multiselect(
                "Preferred time commitment",
                ["1-2 hours", "Half day", "Project sprint"],
            )
            available = st.checkbox("Available for Marketplace opportunities", value=True)

        submitted = st.form_submit_button("Save passport", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Please enter a name.")
            else:
                people.append(
                    {
                        "id": str(uuid.uuid4()),
                        "name": name.strip(),
                        "role_title": role_title.strip(),
                        "directorate": directorate.strip(),
                        "about": about.strip(),
                        "core_skills": unique_clean(split_csv(core_skills)),
                        "hidden_skills": unique_clean(split_csv(hidden_skills)),
                        "passion_skills": unique_clean(split_csv(passion_skills)),
                        "interests": unique_clean(split_csv(interests)),
                        "preferred_commitment": commitment,
                        "available_for_marketplace": available,
                        "created_at": now_str(),
                    }
                )
                save_json(PEOPLE_FILE, people)
                st.success("Passport saved. Refresh or revisit the page to see it in the list.")


# =========================================================
# POST REQUEST
# =========================================================
elif page == "Post a Request":
    render_hero(
        "Post an Opportunity",
        "Create a short-term, value-adding opportunity that helps teams get support and gives colleagues a chance to contribute beyond their job title.",
        "Lightweight · practical · manager-supported",
    )

    with st.form("request_form"):
        c1, c2 = st.columns(2)

        with c1:
            title = st.text_input("Opportunity title")
            team = st.text_input("Team")
            directorate = st.text_input("Directorate")
            description = st.text_area("Describe the support needed", height=150)
            created_by = st.text_input("Posted by")

        with c2:
            skills_needed = st.text_area("Skills needed (comma-separated)", height=100)
            tags = st.text_input("Tags (comma-separated)")
            time_commitment = st.selectbox("Time commitment", ["1-2 hours", "Half day", "Project sprint"])
            resident_impact = st.text_area("How could this positively impact residents?", height=90)
            fit_link = st.text_area("How does this support Fit for the Future?", height=90)

        submitted = st.form_submit_button("Post opportunity", use_container_width=True)

        if submitted:
            if not title.strip():
                st.error("Please enter a title.")
            else:
                requests_data.append(
                    {
                        "id": str(uuid.uuid4()),
                        "title": title.strip(),
                        "team": team.strip(),
                        "directorate": directorate.strip(),
                        "description": description.strip(),
                        "skills_needed": unique_clean(split_csv(skills_needed)),
                        "tags": unique_clean(split_csv(tags)),
                        "time_commitment": time_commitment,
                        "resident_impact": resident_impact.strip(),
                        "fit_for_future_link": fit_link.strip(),
                        "status": "Open",
                        "created_by": created_by.strip(),
                        "matched_person_id": None,
                        "created_at": now_str(),
                    }
                )
                save_json(REQUESTS_FILE, requests_data)
                st.success("Opportunity posted successfully.")


# =========================================================
# BROWSE OPPORTUNITIES
# =========================================================
elif page == "Browse Opportunities":
    render_hero(
        "Browse Opportunities",
        "Explore live opportunities, view suggested matches and see where hidden capability can add value.",
        "Turning opportunities into connections",
    )

    status = st.selectbox("Filter by status", ["All", "Open", "Matched", "Completed"])

    shown = requests_data
    if status != "All":
        shown = [r for r in requests_data if r["status"] == status]

    if not shown:
        st.info("No opportunities found.")
    else:
        for request in shown:
            with st.container():
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                col1, col2 = st.columns([0.68, 0.32], gap="large")

                with col1:
                    st.markdown(f"### {request['title']}")
                    st.write(f"**{request['team']}** · {request['directorate']}")
                    st.caption(f"Posted by {request['created_by']} · {request['created_at']} · Status: {request['status']}")
                    st.write(request["description"])

                    st.markdown("**Skills needed**")
                    render_tag_list(request.get("skills_needed", []), "#EFF6FF", "#0A4F91")

                    st.markdown("**Tags**")
                    render_tag_list(request.get("tags", []), "#F5F3FF", "#5B21B6")

                    st.markdown(
                        f"""
                        <div class="callout"><strong>Resident impact:</strong> {request.get("resident_impact", "—")}</div>
                        <div class="success-callout"><strong>Fit for the Future:</strong> {request.get("fit_for_future_link", "—")}</div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(
                        f"""
                        <div class="mini-card">
                            <div class="eyebrow">Time commitment</div>
                            {request['time_commitment']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    matches = top_matches_for_request(request, people, endorsements, 3)
                    if matches:
                        st.markdown("**Suggested matches**")
                        for m in matches:
                            st.markdown(
                                f"""
                                <div class="mini-card">
                                    <strong>{m['person']['name']}</strong><br>
                                    <span class="muted">{m['person']['role_title']}</span><br><br>
                                    <span class="match-score">Match score: {m['score']}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                st.markdown("---")

                c1, c2 = st.columns(2)
                with c1:
                    selected_name = st.selectbox(
                        f"Assign a match for '{request['title']}'",
                        [""] + [p["name"] for p in people],
                        key=f"assign_{request['id']}",
                    )
                    if st.button("Mark as matched", key=f"match_{request['id']}", use_container_width=True):
                        if selected_name:
                            matched = next((p for p in people if p["name"] == selected_name), None)
                            if matched:
                                request["matched_person_id"] = matched["id"]
                                request["status"] = "Matched"
                                save_json(REQUESTS_FILE, requests_data)
                                st.success(f"{selected_name} matched to the opportunity.")
                        else:
                            st.warning("Please choose someone first.")

                with c2:
                    if st.button("Mark as completed", key=f"complete_{request['id']}", use_container_width=True):
                        request["status"] = "Completed"
                        save_json(REQUESTS_FILE, requests_data)
                        st.success("Opportunity marked as completed.")

                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("")


# =========================================================
# AI NUDGES
# =========================================================
elif page == "AI Nudges":
    render_hero(
        "Smart Matching & AI Nudges",
        "Helping the right opportunities find the right people — including colleagues with hidden and aspiring talent that may otherwise go unnoticed.",
        "A human-centred approach to intelligent matching",
    )

    open_reqs = [r for r in requests_data if r["status"] == "Open"]

    if not open_reqs:
        st.info("There are no open opportunities at the moment.")
    else:
        selected_request = st.selectbox(
            "Choose an opportunity",
            open_reqs,
            format_func=lambda x: x["title"],
        )

        left, right = st.columns([0.48, 0.52], gap="large")
        with left:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(f"### {selected_request['title']}")
            st.write(selected_request["description"])
            st.markdown("**Skills needed**")
            render_tag_list(selected_request.get("skills_needed", []), "#EFF6FF", "#0A4F91")
            st.markdown("**Tags**")
            render_tag_list(selected_request.get("tags", []), "#F5F3FF", "#5B21B6")
            st.markdown(
                f"""
                <div class="mini-card">
                    <div class="eyebrow">Time commitment</div>
                    {selected_request['time_commitment']}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("### Suggested nudges")
            matches = top_matches_for_request(selected_request, people, endorsements, 5)

            if not matches:
                st.warning("No strong matches found.")
            else:
                for idx, match in enumerate(matches, start=1):
                    person = match["person"]
                    exp = match["explanation"]

                    st.markdown(
                        f"""
                        <div class="mini-card">
                            <div class="eyebrow">Match {idx}</div>
                            <strong>{person['name']}</strong><br>
                            <span class="muted">{person['role_title']} · {person['directorate']}</span><br><br>
                            <span class="match-score">Match score: {match['score']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if exp["matched_required"]:
                        st.write(f"**Strong match on:** {', '.join(exp['matched_required'])}")
                    if exp["hidden_hits"]:
                        st.info(f"Hidden skills surfaced: {', '.join(exp['hidden_hits'])}")
                    if exp["passion_hits"]:
                        st.success(
                            f"This opportunity could help them practise a passion skill in a real, value-adding environment: {', '.join(exp['passion_hits'])}"
                        )

                    st.caption(
                        f"Nudge example: “{person['name']}, this opportunity may be a strong fit for your skills and interests.”"
                    )
                    st.markdown("---")
            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ENDORSEMENTS
# =========================================================
elif page == "Endorsements":
    render_hero(
        "Endorsements",
        "Recognition that builds trust. Skills are validated through real contribution, not just job title.",
        "Making talent visible, usable and recognised",
    )

    tab1, tab2 = st.tabs(["Give an endorsement", "View endorsements"])

    with tab1:
        with st.form("endorsement_form"):
            col1, col2 = st.columns(2)
            with col1:
                from_name = st.text_input("Your name")
                to_name = st.selectbox("Who are you endorsing?", [p["name"] for p in people])
                skill_area = st.text_input("Skill or contribution being endorsed")
            with col2:
                linked_request_title = st.selectbox(
                    "Linked opportunity (optional)",
                    [""] + [r["title"] for r in requests_data],
                )
                message = st.text_area("Endorsement message", height=140)

            submitted = st.form_submit_button("Submit endorsement", use_container_width=True)

            if submitted:
                if not from_name.strip() or not skill_area.strip() or not message.strip():
                    st.error("Please complete all required fields.")
                else:
                    person = next((p for p in people if p["name"] == to_name), None)
                    linked = next((r for r in requests_data if r["title"] == linked_request_title), None) if linked_request_title else None
                    if not person:
                        st.error("Selected person not found.")
                    else:
                        endorsements.append(
                            {
                                "id": str(uuid.uuid4()),
                                "from_name": from_name.strip(),
                                "to_person_id": person["id"],
                                "to_person_name": person["name"],
                                "skill_area": skill_area.strip(),
                                "message": message.strip(),
                                "linked_request_id": linked["id"] if linked else None,
                                "linked_request_title": linked["title"] if linked else "",
                                "created_at": now_str(),
                            }
                        )
                        save_json(ENDORSEMENTS_FILE, endorsements)
                        st.success(f"Endorsement added for {person['name']}.")

    with tab2:
        if not endorsements:
            st.info("No endorsements yet.")
        else:
            for e in reversed(endorsements):
                st.markdown(
                    f"""
                    <div class="glass-card">
                        <div class="eyebrow">Endorsement</div>
                        <h4 style="margin-bottom:0.3rem;">{e['to_person_name']}</h4>
                        <div class="muted" style="margin-bottom:0.5rem;">Endorsed by {e['from_name']} · {e['created_at']}</div>
                        <div><strong>Skill / contribution:</strong> {e['skill_area']}</div>
                        <div style="margin-top:0.6rem;">{e['message']}</div>
                        {"<div class='callout'><strong>Linked opportunity:</strong> " + e['linked_request_title'] + "</div>" if e.get('linked_request_title') else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("")


# =========================================================
# INSIGHTS
# =========================================================
elif page == "Insights":
    render_hero(
        "Insights",
        "A live picture of workforce capability, contribution and opportunity — helping the council make better decisions over time.",
        "From hidden talent to strategic insight",
    )

    total_people = len(people)
    total_requests = len(requests_data)
    total_completed = sum(1 for r in requests_data if r["status"] == "Completed")
    total_open = sum(1 for r in requests_data if r["status"] == "Open")
    total_end = len(endorsements)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        render_metric_card("Passports", str(total_people), "People with visible skills")
    with m2:
        render_metric_card("Requests Posted", str(total_requests), "All opportunities")
    with m3:
        render_metric_card("Open Requests", str(total_open), "Live requests right now")
    with m4:
        render_metric_card("Completed", str(total_completed), "Requests turned into action")
    with m5:
        render_metric_card("Endorsements", str(total_end), "Recognition and trust")

    all_core = []
    all_hidden = []
    all_passion = []
    directorates = []
    people_rows = []

    for p in people:
        all_core.extend(p.get("core_skills", []))
        all_hidden.extend(p.get("hidden_skills", []))
        all_passion.extend(p.get("passion_skills", []))
        directorates.append(p.get("directorate", "Unknown"))
        people_rows.append(
            {
                "Name": p["name"],
                "Role": p["role_title"],
                "Directorate": p["directorate"],
                "Endorsements": endorsement_count(p["id"], endorsements),
                "Completed contributions": completed_contributions(p["id"], requests_data),
                "Hidden skills": len(p.get("hidden_skills", [])),
                "Passion skills": len(p.get("passion_skills", [])),
            }
        )

    def freq_df(items: list[str], label: str) -> pd.DataFrame:
        if not items:
            return pd.DataFrame(columns=["Skill", "Count", "Type"])
        s = pd.Series(items).value_counts().reset_index()
        s.columns = ["Skill", "Count"]
        s["Type"] = label
        return s

    skill_df = pd.concat(
        [
            freq_df(all_core, "Core"),
            freq_df(all_hidden, "Hidden"),
            freq_df(all_passion, "Passion"),
        ],
        ignore_index=True,
    )

    left, right = st.columns([0.55, 0.45], gap="large")

    with left:
        render_section_title("Top recorded skills")
        if not skill_df.empty:
            st.dataframe(
                skill_df.sort_values(["Type", "Count"], ascending=[True, False]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No skill data available yet.")

        render_section_title("People, contribution and recognition")
        people_df = pd.DataFrame(people_rows).sort_values(
            ["Endorsements", "Completed contributions"], ascending=False
        )
        st.dataframe(people_df, use_container_width=True, hide_index=True)

    with right:
        render_section_title("Capability profile")
        cap_summary = pd.DataFrame(
            {
                "Category": ["Core skills", "Hidden skills", "Passion skills"],
                "Count": [len(all_core), len(all_hidden), len(all_passion)],
            }
        )
        st.bar_chart(cap_summary.set_index("Category"))

        render_section_title("Directorate spread")
        dir_df = pd.Series(directorates).value_counts().reset_index()
        dir_df.columns = ["Directorate", "People"]
        st.dataframe(dir_df, use_container_width=True, hide_index=True)

    st.markdown("")
    st.markdown(
        """
        <div class="success-callout">
            <strong>Strategic value:</strong> this goes beyond matching people to tasks. It creates insight into hidden capability, underused strengths, passion skills, contribution patterns and where development opportunities are emerging.
        </div>
        <div class="gold-callout">
            <strong>Resident value:</strong> by making better use of internal capability, the council can respond faster, collaborate more effectively, reduce duplication and strengthen outcomes for residents.
        </div>
        <div class="callout">
            <strong>Fit for the Future:</strong> supports a more agile, skilled, connected and insight-led workforce.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="footer-note">
            This demo is intentionally simple — but the insight layer shows how the Marketplace could become a live view of organisational capability over time.
        </div>
        """,
        unsafe_allow_html=True,
    )
    