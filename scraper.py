"""
scraper.py — Vihil InfoTech Knowledge Base Builder
====================================================
Supports three data sources (tried in order):
  1. Live Backend REST API  (http://143.244.141.111:3000/...)
  2. Next.js __NEXT_DATA__ / JS bundle extraction
  3. Hard-coded static fallback (always up-to-date with last known site state)

NOTE: vihilinfotech.com now runs behind Cloudflare / WAF that blocks server-side
requests with HTTP 403. If direct scraping fails, the script falls back to the
most recent static snapshot so the knowledge base is never left empty.
"""

import urllib.request
import re
import json
import ssl
import sys
import datetime

# ── SSL ───────────────────────────────────────────────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
}


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_url(url, timeout=10, extra_headers=None):
    try:
        h = dict(HEADERS)
        if extra_headers:
            h.update(extra_headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [WARN] fetch_url({url}): {e}", file=sys.stderr)
        return None


def extract_balanced_chunk(text, open_ch, close_ch, start_pos):
    count = 0
    for i in range(start_pos, len(text)):
        if text[i] == open_ch:
            count += 1
        elif text[i] == close_ch:
            count -= 1
            if count == 0:
                return text[start_pos: i + 1]
    return None


def extract_variable_array(var_name, text, start_pos=0):
    escaped = re.escape(var_name)
    pattern = (r'\b' + escaped if not var_name.startswith("$") else escaped) + r'\s*[=:]\s*(?:\[|\()'
    m = re.search(pattern, text[start_pos:])
    if not m:
        return None
    pos = start_pos + m.end() - 1
    if text[pos] == "[":
        return extract_balanced_chunk(text, "[", "]", pos)
    if text[pos] == "(":
        chunk = extract_balanced_chunk(text, "(", ")", pos)
        if chunk:
            bm = list(re.finditer(r"\[", chunk))
            if bm:
                return extract_balanced_chunk(chunk, "[", "]", bm[-1].start())
    return None


def parse_js_array_to_dicts(js_str):
    if not js_str:
        return []
    KEYS = [
        "name", "position", "desc", "desc1", "title", "post", "copy",
        "question", "answer", "area", "description", "content", "dis",
    ]
    items = []
    for m in re.finditer(r"\{", js_str):
        block = extract_balanced_chunk(js_str, "{", "}", m.start())
        if not block:
            continue
        item = {}
        for key in KEYS:
            mv = re.search(r"\b" + key + r'\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', block)
            if mv:
                try:
                    item[key] = mv.group(1).encode().decode("unicode_escape", errors="ignore")
                except Exception:
                    item[key] = mv.group(1)
            else:
                mv2 = re.search(r"\b" + key + r"\s*:\s*'([^'\\]*(?:\\.[^'\\]*)*)'", block)
                if mv2:
                    try:
                        item[key] = mv2.group(1).encode().decode("unicode_escape", errors="ignore")
                    except Exception:
                        item[key] = mv2.group(1)
        mid = re.search(r"\bid\s*:\s*([0-9]+)", block)
        if mid:
            item["id"] = int(mid.group(1))
        if item:
            items.append(item)
    return items


def clean_bracket_placeholders(items):
    for obj in items:
        for k, v in obj.items():
            if isinstance(v, str):
                obj[k] = v.replace("[Vihil infotech]", "Vihil InfoTech")
    return items


# ─────────────────────────────────────────────────────────────────────────────
# Source 1 — Live REST API
# ─────────────────────────────────────────────────────────────────────────────

API_BASE = "http://143.244.141.111:3000/forntadmin/v1/"

def fetch_api(path, timeout=5):
    try:
        raw = fetch_url(API_BASE + path, timeout=timeout)
        if raw:
            data = json.loads(raw)
            if "data" in data and len(data["data"]) > 0:
                return data["data"]
    except Exception as e:
        print(f"  [WARN] API {path}: {e}", file=sys.stderr)
    return None


def scrape_via_api():
    print("  Trying live REST API...")
    result = {}
    api_map = {
        "vision":     "common?page=1&limit=50&placeOfContent=vision",
        "statistics": "common?page=1&limit=50&placeOfContent=statistics",
        "faqs":       "faq",
        "services":   "service",
        "team":       "team",
        "process":    "process",
    }
    for key, path in api_map.items():
        data = fetch_api(path)
        if data:
            result[key] = data
            print(f"  OK  {key}: {len(data)} records")
        else:
            print(f"  ERR {key}: no data")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Source 2 — Next.js / HTML scrape
# ─────────────────────────────────────────────────────────────────────────────

def scrape_via_nextjs():
    print("  Trying Next.js / HTML scrape...")
    html = fetch_url("https://www.vihilinfotech.com/")
    if not html:
        print("  Site blocked (Cloudflare WAF — HTTP 403). Skipping HTML scrape.")
        return {}

    result = {}

    # __NEXT_DATA__ inline JSON
    nd_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if nd_match:
        try:
            nd = json.loads(nd_match.group(1))
            props = nd.get("props", {}).get("pageProps", {})
            if props:
                print(f"  __NEXT_DATA__ found, keys: {list(props.keys())}")
                result["next_data"] = props
        except Exception as e:
            print(f"  [WARN] __NEXT_DATA__ parse error: {e}")

    # JS bundle
    bundle_match = re.search(r'/_next/static/chunks/[^\s"\']+\.js', html) or \
                   re.search(r'/static/js/main\.[a-f0-9]+\.js', html)
    if not bundle_match:
        print("  No JS bundle URL found.")
        return result

    bundle_url = "https://www.vihilinfotech.com" + bundle_match.group(0)
    print(f"  Bundle: {bundle_url}")
    js = fetch_url(bundle_url)
    if not js:
        print("  Failed to download JS bundle.")
        return result

    print("  JS bundle downloaded. Extracting arrays...")
    anchor_idx = js.find("Bharat Desai")
    search_area = js[anchor_idx:] if anchor_idx != -1 else js

    if anchor_idx != -1:
        team_start = js.rfind("[", 0, anchor_idx)
        if team_start != -1:
            result["team"] = parse_js_array_to_dicts(
                extract_balanced_chunk(js, "[", "]", team_start))

    array_map = {
        "services":           ("Qo", js),
        "faqs":               ("GS", js),
        "what_we_do":         ("ls", js),
        "process":            ("os", search_area),
        "carousel":           ("ss", search_area),
        "mobile":             ("$o", search_area),
        "web_frontend":       ("es", search_area),
        "fullstack":          ("ts", search_area),
        "backend":            ("ns", search_area),
        "cross_platform":     ("rs", search_area),
        "frontend_frameworks":("is", search_area),
    }
    for name, (var, area) in array_map.items():
        arr = parse_js_array_to_dicts(extract_variable_array(var, area))
        if arr:
            result[name] = clean_bracket_placeholders(arr)
            print(f"  {name}: {len(arr)} items")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Source 3 — Static fallback snapshot
# ─────────────────────────────────────────────────────────────────────────────

def get_static_fallback():
    """Complete, up-to-date snapshot of the live site as of 2026-06-01."""
    return {
        "company": {
            "name": "Vihil InfoTech",
            "legal_name": "Vihil Infotech Private Limited",
            "tagline": "Build faster with a dependable tech partner.",
            "sub_tagline": "Your trusted IT partner for web, mobile, AI, and cloud solutions — built for clarity, speed, and long-term growth.",
            "vision": {
                "area": "Vision Of Our Company",
                "description": "We envision technology as a growth engine where AI/ML, product engineering, and cloud infrastructure come together to create measurable business outcomes."
            },
            "about": {
                "headline": "We build IT systems that are scalable, secure, and AI-ready — from product discovery to launch and long-term evolution.",
                "who_we_are": "A product-focused team of engineers, designers, and AI specialists. We partner with startups and enterprises to create practical digital products that solve real business problems.",
                "mission": "Our mission is to merge business strategy with IT execution and deliver products that create measurable impact.",
                "pillars": [
                    {"name": "AI-first Thinking",  "desc": "From copilots to workflow automation and smart assistants."},
                    {"name": "Scalable Systems",    "desc": "Modular architecture for performance and future growth."},
                    {"name": "Reliable Delivery",   "desc": "Outcome-oriented sprints with quality and transparency."},
                ]
            },
            "statistics": [
                {"name": "60+", "content": "Happy Clients"},
                {"name": "60+", "content": "Completed Projects"},
                {"name": "20+", "content": "Experienced Staff"},
                {"name": "4.8", "content": "Ratings"},
            ],
            "contact": {
                "address": "207, Vihil Infotech Private Limited, Sky Tatva-1, Opposite Amba Aashram, College Road, Nadiad, Gujarat, India",
                "email": "vihil3010@gmail.com",
                "phone": "+91 7016421339",
                "response_time": "We reply within 24 hours",
                "social_links": {
                    "instagram": "https://www.instagram.com/vihilinfotech/",
                    "linkedin":  "https://www.linkedin.com/company/vihil-infotech-private-limited/",
                    "facebook":  "https://www.facebook.com/vihilinfotech",
                    "website":   "https://www.vihilinfotech.com/",
                }
            }
        },
        "services": [
            {"id": 1, "title": "Web Development",                "desc1": "High-performance web apps using React, Next.js, Node.js — from landing pages to enterprise platforms."},
            {"id": 2, "title": "Mobile App Development",         "desc1": "Cross-platform and native iOS/Android apps built with React Native for seamless user experiences."},
            {"id": 3, "title": "AI / ML Integration",            "desc1": "LLM assistants, RAG knowledge search, workflow automation, and data intelligence layers for measurable outcomes."},
            {"id": 4, "title": "Cloud & Infrastructure",         "desc1": "Cloud modernization, DevOps, CI/CD pipelines, and managed cloud-native architectures."},
            {"id": 5, "title": "Cyber Security",                 "desc1": "Security audits, penetration testing, compliance reviews, and secure architecture design."},
            {"id": 6, "title": "SEO & Digital Marketing",        "desc1": "Data-backed SEO, technical optimization, and digital campaigns to grow visibility and ROI."},
            {"id": 7, "title": "PWA Development",                "desc1": "Progressive Web Apps with React/Next.js for fast, reliable, installable cross-device experiences."},
            {"id": 8, "title": "Desktop Application Development","desc1": "Cross-platform desktop apps using Electron and React for Windows, macOS, and Linux."},
        ],
        "what_we_do": [
            {"id": 1,  "name": "Web Application",            "desc": "Platform-independent business solutions for maximum availability"},
            {"id": 2,  "name": "Cross Platform Development", "desc": "Interactive apps with perfect integration of frontend and backend"},
            {"id": 3,  "name": "SEO",                        "desc": "Let the world find you on top of others"},
            {"id": 4,  "name": "Desktop Application",        "desc": "Advanced autonomous software to make life simple"},
            {"id": 5,  "name": "BIG Data",                   "desc": "Decision making backed by intelligent insight"},
            {"id": 6,  "name": "Cyber Security",             "desc": "Make your digital assets secure and protected"},
            {"id": 7,  "name": "Mobile Applications",        "desc": "Robust technology to accompany with you"},
            {"id": 8,  "name": "Digital Marketing",          "desc": "Business made easy in a digital world"},
            {"id": 9,  "name": "AI / ML Enablement",         "desc": "Smarter products powered by generative AI and machine learning"},
            {"id": 10, "name": "Cloud Modernization",        "desc": "Scalable, cost-efficient cloud-native infrastructure and DevOps"},
        ],
        "ai_ml": {
            "headline": "AI/ML can be integrated here for smarter products and automation.",
            "capabilities": [
                {"name": "Generative AI Workflows", "desc": "Automate content, support, and internal operations with secure AI assistants.", "features": ["LLM-based assistants", "Knowledge search + RAG", "Workflow automation agents"]},
                {"name": "Data Intelligence Layer", "desc": "ML predictions for forecasting, retention, and decision-making."},
                {"name": "Automation & AI Ops",     "desc": "Connect AI with existing systems and automate repetitive processes.", "tech_stack": ["FastAPI", "LangChain", "Node.js", "Cloud"]},
            ]
        },
        "team": [
            {"id": 1,  "name": "Bharat Desai",    "position": "CEO",                                     "desc": "Founder driving company vision and growth strategy."},
            {"id": 2,  "name": "Manish Shah",      "position": "CTO",                                     "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 3,  "name": "Jay Shah",         "position": "Project Manager & Fullstack Developer",   "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 4,  "name": "Heer Patel",       "position": "Sr. Frontend Developer",                  "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 5,  "name": "Dhaval Prajapati", "position": "HR & Sr. QA",                             "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 6,  "name": "Mihir Prajapati",  "position": "Sr. Backend Developer & Server Handling", "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 7,  "name": "Dip Pathak",       "position": "Sr. Frontend Developer",                  "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 8,  "name": "Kinjal Patel",     "position": "Jr. Frontend Developer",                  "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 9,  "name": "Jaydeep Panchal",  "position": "Jr. Frontend Developer",                  "desc": "From automation to advanced analytics and seamless experiences."},
            {"id": 10, "name": "Shaami Rana",      "position": "BDE (Business Development Executive)",    "desc": "From automation to advanced analytics and seamless experiences."},
        ],
        "technologies": sorted([
            "React", "Next.js", "Node.js", "Express.js", "React Native",
            "Android", "iOS", "PHP", "Shopify", "Python", "FastAPI",
            "LangChain", "AI / ML", "Cyber Security", "SEO", "Electron",
            "TypeScript", "JavaScript", "Cloud (AWS/GCP/Azure)",
        ]),
        "tech_categories": {
            "web_frontend": [{"desc": "React"}, {"desc": "Next.js"}, {"desc": "TypeScript"}, {"desc": "JavaScript"}],
            "backend":      [{"desc": "Node.js"}, {"desc": "Express.js"}, {"desc": "PHP"}, {"desc": "Python"}, {"desc": "FastAPI"}],
            "mobile":       [{"desc": "React Native"}, {"desc": "Android"}, {"desc": "iOS"}],
            "ai_ml":        [{"desc": "LangChain"}, {"desc": "AI / ML"}, {"desc": "RAG / Knowledge Search"}],
            "ecommerce":    [{"desc": "Shopify"}],
            "cloud":        [{"desc": "Cloud (AWS/GCP/Azure)"}],
        },
        "process": [
            {"id": 1, "title": "01.", "content": "Research",         "dis": "Gathering information from all around"},
            {"id": 2, "title": "02.", "content": "Plan",             "dis": "Effective strategies for favorable outcomes"},
            {"id": 3, "title": "03.", "content": "Implement",        "dis": "Timely executions as per the plan"},
            {"id": 4, "title": "04.", "content": "Test and Deliver", "dis": "Making a successful launch"},
            {"id": 5, "title": "05.", "content": "Optimize",         "dis": "Steadily climbing up the hill"},
        ],
        "faqs": [
            {"id": 1,  "question": "What services does Vihil InfoTech offer?",                                "answer": "Web development (React/Next.js), mobile apps (React Native/iOS/Android), AI/ML integration (LLMs, RAG, automation), cloud infrastructure, cybersecurity, SEO, PWA, and desktop app development."},
            {"id": 2,  "question": "What technologies does your team specialize in?",                         "answer": "React, Next.js, Node.js, Express.js, React Native, Python, FastAPI, LangChain, PHP, Shopify, Android, iOS, TypeScript, and Cloud platforms (AWS/GCP/Azure)."},
            {"id": 3,  "question": "How experienced is your team?",                                           "answer": "20+ experienced professionals with 60+ completed projects, 60+ happy clients, and a 4.8 rating."},
            {"id": 4,  "question": "Can you handle both small projects and large-scale enterprise solutions?", "answer": "Yes. We work with startups and enterprises, from MVPs to complex enterprise platforms."},
            {"id": 5,  "question": "What is your development process?",                                       "answer": "Research → Plan → Implement → Test & Deliver → Optimize. Using agile Scrum and Kanban."},
            {"id": 6,  "question": "Do you integrate AI and ML into products?",                               "answer": "Yes. LLM assistants, RAG, generative AI workflows, data intelligence, and AI Ops using FastAPI, LangChain, Node.js, and cloud."},
            {"id": 7,  "question": "How do you ensure security?",                                             "answer": "Security audits, secure coding, penetration testing, compliance reviews, and dedicated cybersecurity services."},
            {"id": 8,  "question": "Do you provide ongoing support?",                                         "answer": "Yes. Post-launch support, maintenance, and continuous optimization."},
            {"id": 9,  "question": "How can I get a quote?",                                                  "answer": "Email vihil3010@gmail.com, call +91 7016421339, or book a call at https://www.vihilinfotech.com/. We reply within 24 hours."},
            {"id": 10, "question": "Where is Vihil InfoTech located?",                                        "answer": "207, Vihil Infotech Private Limited, Sky Tatva-1, Opposite Amba Aashram, College Road, Nadiad, Gujarat, India."},
            {"id": 11, "question": "What sets Vihil InfoTech apart?",                                         "answer": "AI-first thinking, scalable modular systems, and reliable agile delivery. We merge business strategy with IT execution."},
            {"id": 12, "question": "Can you provide references or case studies?",                             "answer": "Yes. Contact vihil3010@gmail.com for case studies and references relevant to your industry."},
        ],
        "carousel": [
            {"id": 1, "name": "Cutting Edge Technology",    "desc": "Take advantage of our solutions to increase your Return on Investment in IT."},
            {"id": 2, "name": "Cross Device Compatibility", "desc": "Multi-device compatibility ensures seamless access across all platforms."},
            {"id": 3, "name": "Tailored Mode Development",  "desc": "Scalable and dynamic systems built to meet your ever-changing business needs."},
            {"id": 4, "name": "AI-first Products",          "desc": "From copilots to workflow automation — build smarter products powered by AI/ML."},
            {"id": 5, "name": "Reliable Delivery",          "desc": "Outcome-oriented sprints with quality, transparency, and speed you can count on."},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def scrape_vihil(output_path="knowledge_base.json"):
    print("\n" + "=" * 60)
    print("  Vihil InfoTech — Knowledge Base Builder")
    print("=" * 60)

    kb = get_static_fallback()
    kb["metadata"] = {
        "source": "https://www.vihilinfotech.com/",
        "crawled_at": datetime.datetime.now().isoformat(),
        "sources_tried": [],
    }

    # Source 1: REST API
    print("\n[1/2] REST API")
    api_data = scrape_via_api()
    if api_data:
        kb["metadata"]["sources_tried"].append("rest_api")
        for key in ("vision", "statistics", "faqs", "services", "team", "process"):
            if key in api_data:
                if key == "vision":
                    kb["company"]["vision"] = api_data[key][0] if api_data[key] else kb["company"]["vision"]
                elif key == "statistics":
                    kb["company"]["statistics"] = api_data[key]
                else:
                    kb[key] = api_data[key]
        print("  REST API data merged.")

    # Source 2: Next.js scrape
    print("\n[2/2] Next.js / HTML scrape")
    next_data = scrape_via_nextjs()
    if next_data:
        kb["metadata"]["sources_tried"].append("nextjs_scrape")
        for key in ("team", "services", "faqs", "what_we_do", "process", "carousel"):
            if key in next_data and next_data[key]:
                kb[key] = next_data[key]
        for cat in ("mobile", "web_frontend", "fullstack", "backend", "cross_platform", "frontend_frameworks"):
            if cat in next_data and next_data[cat]:
                kb.setdefault("tech_categories", {})[cat] = next_data[cat]
        all_techs = {item["desc"] for items in kb.get("tech_categories", {}).values() for item in items if "desc" in item}
        if all_techs:
            kb["technologies"] = sorted(all_techs)
        print("  Next.js data merged.")

    if not kb["metadata"]["sources_tried"]:
        kb["metadata"]["sources_tried"].append("static_fallback")
        print("  Using complete static fallback snapshot.")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"  Knowledge base saved to: {output_path}")
    print(f"    Services : {len(kb.get('services', []))}")
    print(f"    Team     : {len(kb.get('team', []))}")
    print(f"    FAQs     : {len(kb.get('faqs', []))}")
    print(f"    Process  : {len(kb.get('process', []))}")
    print(f"    Techs    : {len(kb.get('technologies', []))}")
    print(f"    Sources  : {', '.join(kb['metadata']['sources_tried'])}")
    print("=" * 60 + "\n")
    return kb


if __name__ == "__main__":
    scrape_vihil()