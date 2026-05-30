import os
import json
import re
import sys
import datetime
import time
import math

# Force UTF-8 encoding on standard streams to prevent UnicodeEncodeError on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ANSI Colors for Terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def init_terminal():
    """Enable virtual terminal processing on Windows for ANSI colors."""
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

def load_dotenv_custom(filepath=".env"):
    """Loads a .env file if it exists, putting variables into os.environ."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key:
                            os.environ[key] = val
        except Exception as e:
            print(f"Error loading custom .env: {e}", file=sys.stderr)

# Load env variables at startup
load_dotenv_custom()

def load_knowledge_base(filepath="knowledge_base.json"):
    """Load the crawled structured knowledge base."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading knowledge base: {e}", file=sys.stderr)
        return {}

def clean_and_tokenize(text):
    """Clean, lowercase, and tokenize text into a set of words, removing common stop words."""
    if not text:
        return set()
    text_lower = text.lower()
    # Remove punctuation and special symbols
    cleaned = re.sub(r'[^\w\s]', ' ', text_lower)
    words = cleaned.split()
    
    stop_words = {
        "what", "is", "are", "do", "you", "how", "can", "i", "get", "a", "the", "to", 
        "for", "of", "in", "on", "about", "with", "does", "vihil", "infotech", "company",
        "please", "tell", "me", "show", "give", "who", "where", "when", "why", "which"
    }
    return set(w for w in words if w not in stop_words and len(w) > 1)

def build_search_index(kb):
    """Compiles all fields of knowledge_base.json into structured documents for keyword search."""
    if not kb:
        return []
    
    index = []
    
    # 1. Company General / Tagline
    tagline = kb.get("company", {}).get("tagline", "")
    if tagline:
        index.append({
            "type": "general",
            "title": "Company Tagline & Description",
            "search_text": f"tagline description about company general vihil infotech {tagline}",
            "content": tagline,
            "answer": f"**Vihil InfoTech Tagline & Overview**:\n> *\"{tagline}\"*\n\nVihil InfoTech is a leading software engineering firm specializing in modern high-performance web applications, cross-platform mobile apps, and robust desktop solutions."
        })
        
    # 2. Company Vision
    vision = kb.get("company", {}).get("vision", {})
    if vision:
        area = vision.get("area", "Vision of our Company")
        desc = vision.get("description", "")
        index.append({
            "type": "vision",
            "title": f"Company {area} Mission Philosophy",
            "search_text": f"vision mission goal target philosophy values {area} {desc}",
            "content": desc,
            "answer": f"### 🎯 {area}\n{desc}"
        })
        
    # 3. Company Statistics
    stats = kb.get("company", {}).get("statistics", [])
    if stats:
        stats_str = "\n".join([f"- **{s.get('content')}**: {s.get('name')}" for s in stats])
        index.append({
            "type": "statistics",
            "title": "Company Statistics & Achievements Ratings Projects",
            "search_text": "statistics stats numbers count completed projects happy clients ratings rating staff experience size",
            "content": stats_str,
            "answer": f"### 📊 Vihil InfoTech Statistics\n{stats_str}"
        })
        
    # 4. Contact Details
    contact = kb.get("company", {}).get("contact", {})
    if contact:
        addr = contact.get("address", "")
        email = contact.get("email", "")
        phone = contact.get("phone", "")
        socials = contact.get("social_links", {})
        socials_str = "\n".join([f"- **{k.capitalize()}**: [{v}]({v})" for k, v in socials.items()])
        
        index.append({
            "type": "contact",
            "title": "Contact Information Email Phone Location Address Office",
            "search_text": "contact email phone mobile number telephone support vihil3010@gmail.com +91 7016421339 facebook instagram twitter linkedin address office location where headquarter head quarters nadiad gujarat india",
            "content": f"{addr} {email} {phone} {socials_str}",
            "answer": f"### 📞 Contact Vihil InfoTech\n- 📍 **Address**: {addr}\n- ✉ **Email**: {email}\n- 📞 **Phone**: {phone}\n\n**Social Profiles**:\n{socials_str}"
        })
        
    # 5. Core Services
    for s in kb.get("services", []):
        title = s.get("title", "").strip()
        clean_title = re.sub(r'^[0-9\.\s]+', '', title)
        desc1 = s.get("desc1", "")
        desc = s.get("desc", "")
        ans_text = desc1 or desc
        index.append({
            "type": "service",
            "title": f"Service: {clean_title}",
            "search_text": f"service develop coding development build web mobile app native cross-platform pwa desktop chatbot {clean_title} {ans_text}",
            "content": ans_text,
            "answer": f"### 🛠️ Service: {clean_title}\n{ans_text}"
        })
        
    # 6. What We Do / Capabilities
    for w in kb.get("what_we_do", []):
        name = w.get("name", "").strip()
        desc = w.get("desc", "").strip()
        index.append({
            "type": "capability",
            "title": f"Capability: {name}",
            "search_text": f"capability solution standard process what we do offering seo cybersecurity big data digital marketing {name} {desc}",
            "content": desc,
            "answer": f"### ⚡ {name}\n*{desc}*"
        })
        
    # 7. FAQs
    for f in kb.get("faqs", []):
        q = f.get("question", "").strip()
        ans = f.get("answer", "").strip()
        index.append({
            "type": "faq",
            "title": f"FAQ: {q}",
            "search_text": f"faq question answer query support common FAQ {q} {ans}",
            "content": ans,
            "answer": f"### ❓ FAQ: {q}\n{ans}"
        })
        
    # 8. Team Members
    for m in kb.get("team", []):
        name = m.get("name", "").strip()
        pos = m.get("position", "").replace("(", "").replace(")", "").strip()
        desc = m.get("desc", "").strip()
        index.append({
            "type": "team",
            "title": f"Team Member: {name} ({pos})",
            "search_text": f"team member employee founder ceo cto staff who works developer developer engineer designer director management {name} {pos} {desc}",
            "content": f"{name} {pos} {desc}",
            "answer": f"👤 **{name}** — *{pos}*\n{desc if (desc and 'from automation to advanced' not in desc.lower()) else 'Dedicated team member shaping high-quality solutions.'}"
        })
        
    # 9. Development Process
    for p in kb.get("process", []):
        title = p.get("title", "").strip()
        content = p.get("content", "").strip()
        dis = p.get("dis", "").strip()
        index.append({
            "type": "process",
            "title": f"Process Step {title}: {content}",
            "search_text": f"process step development workflow methodology cycle project stages method standard how we build research planning implement testing launch deliver optimize {title} {content} {dis}",
            "content": f"{title} {content} {dis}",
            "answer": f"### 🔄 Development Process: Step {title} ({content})\n{dis}"
        })
        
    # 10. Carousel / Portfolio highlights
    for c in kb.get("carousel", []):
        title = c.get("title", "")
        if not title:
            title = c.get("name", "")
        desc = c.get("desc", "")
        index.append({
            "type": "portfolio",
            "title": f"Highlight: {title}",
            "search_text": f"portfolio highlight case study showcase work carousel slide theme value proposition {title} {desc}",
            "content": desc,
            "answer": f"### 🌟 Portfolio Highlight: {title}\n{desc}"
        })
        
    # 11. Technologies
    techs = kb.get("technologies", [])
    if techs:
        techs_str = ", ".join(techs)
        index.append({
            "type": "technology",
            "title": "Specialized Technologies Stack Languages Frameworks",
            "search_text": f"technology tech stack languages database frontend backend mobile framework tools libraries react nextjs flutter android ios php python node {techs_str}",
            "content": techs_str,
            "answer": f"### 💻 Specialized Technology Stack\nVihil InfoTech specializes in a wide range of cutting-edge frameworks, databases, and programming languages:\n" + "\n".join([f"- {t}" for t in techs])
        })
        
    return index

def compute_tfidf_score(query, docs):
    """
    Computes a highly accurate TF-IDF relevance score for each document against the query.
    Supports title boosts, exact phrase matching, bigrams, and length normalization.
    """
    query_tokens = [w for w in clean_and_tokenize(query)]
    if not query_tokens:
        return []
        
    # Count document frequency (DF) for each term in the corpus
    df = {}
    total_docs = len(docs)
    for doc in docs:
        tokens = set(clean_and_tokenize(doc["search_text"]) | clean_and_tokenize(doc["title"]))
        for token in tokens:
            df[token] = df.get(token, 0) + 1
            
    # Compute inverse document frequency (IDF) for each query term
    idf = {}
    for token in query_tokens:
        d_f = df.get(token, 0)
        # Smoothed IDF
        idf[token] = math.log(1.0 + (total_docs - d_f + 0.5) / (d_f + 0.5))
        
    scored_docs = []
    query_lower = query.lower().strip()
    
    for doc in docs:
        search_text = doc["search_text"].lower()
        title = doc["title"].lower()
        content = doc["content"].lower()
        
        doc_tokens = clean_and_tokenize(doc["search_text"])
        doc_title_tokens = clean_and_tokenize(doc["title"])
        
        # Term frequencies (TF) inside the document search_text
        tf = {}
        for token in doc_tokens:
            tf[token] = tf.get(token, 0) + 1
            
        score = 0.0
        for token in query_tokens:
            if token in doc_tokens:
                # Sublinear term frequency scaling
                tf_val = 1.0 + math.log(tf[token])
                score += tf_val * idf.get(token, 0.0)
                
            # Major boost if query term matches document title directly
            if token in doc_title_tokens:
                score += 3.5 * idf.get(token, 0.0)
                
        # Phrase exact matching bonuses
        if query_lower in title:
            score += 15.0
        elif query_lower in search_text or query_lower in content:
            score += 7.0
        else:
            # Partial N-gram match checks
            words = query_lower.split()
            if len(words) > 1:
                for i in range(len(words) - 1):
                    bigram = f"{words[i]} {words[i+1]}"
                    if bigram in title:
                        score += 5.0
                    elif bigram in search_text or bigram in content:
                        score += 2.0
                        
        # Length normalization (math.sqrt of document length)
        doc_len = len(doc_tokens) + len(doc_title_tokens) + 1.0
        normalized_score = score / math.sqrt(doc_len)
        
        scored_docs.append((normalized_score, doc))
        
    # Sort by score descending
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    return scored_docs

def preprocess_multilingual_query(query):
    """
    Translates or maps non-English, Hindi, and Gujarati keywords/queries into standard English concepts
    to allow the TF-IDF index to match correctly.
    """
    q_lower = query.lower().strip()
    
    # 1. Multi-lingual mappings (Hindi/Gujarati phonetics, Devanagari, and Gujarati script)
    translation_maps = {
        # Contact / Location concepts
        "contact": ["संपर्क", "सम्पर्क", "સંપર્ક", "contact", "number", "phone", "email", "address", "location", "office", "headquarter", "nadiad", "gujarat", "india", "ફોન", "મોબાઈલ", "સરનામું", "ઈમેલ", "કહા", "कहा", "कहाँ", "પતા", "पता", "નંબર", "नंबर", "फ़ोन"],
        # Services / Work concepts
        "service": ["सेवा", "સેવા", "काम", "કામ", "services", "offer", "do", "build", "develop", "make", "create", "બનાવો", "બનાવે", "बनाता", "બનાવતી"],
        # Mobile app development
        "mobile": ["मोबाइल", "મોબાઈલ", "app", "application", "android", "ios", "એપ", "ऐप", "phone app"],
        # Web development
        "web": ["वेबसाइट", "વેબસાઈટ", "वेब", "વેબ", "website", "site", "page", "nextjs", "react"],
        # Team / Owner / CEO concepts
        "team": ["टीम", "ટીમ", "ceo", "cto", "owner", "founder", "boss", "member", "staff", "employee", "માલિક", "ભરત", "भरत", "મનીષ", "मनीष", "જેય", "जय"],
        # QA / Security
        "security": ["सुरक्षा", "સુરક્ષા", "cyber", "protect", "safe", "secure"],
        # Development Process
        "process": ["काम करने का तरीका", "પદ્ધતિ", "चरण", "पद्धति", "process", "step", "method", "workflow"]
    }
    
    expanded_terms = []
    for concept, keywords in translation_maps.items():
        for keyword in keywords:
            if keyword in q_lower:
                expanded_terms.append(concept)
                break
                
    # 2. English synonyms expansion for common questions
    synonyms = {
        "location": ["where", "location", "address", "office", "city", "nadiad", "gujarat", "india", "place", "map", "situated", "located"],
        "ceo": ["ceo", "cto", "owner", "founder", "head", "boss", "runs", "manage", "bharat", "manish", "desai", "shah"],
        "team": ["who works", "member", "staff", "employees", "team", "people", "developers", "engineers"],
        "contact": ["email", "phone", "call", "mobile", "number", "reach", "support", "talk to", "contact"],
        "service": ["services", "capabilities", "what we do", "build", "develop", "create", "offering", "solutions"],
        "quote": ["price", "cost", "charge", "quote", "payment", "budget", "how much"],
        "process": ["process", "methodology", "workflow", "steps", "stages", "how do you build", "how you work"],
        "faqs": ["faqs", "questions", "common", "support", "help", "security", "maintenance"]
    }
    
    for concept, keywords in synonyms.items():
        if any(w in q_lower for w in keywords):
            expanded_terms.append(concept)
            
    if expanded_terms:
        return query + " " + " ".join(set(expanded_terms))
    return query

def fallback_qa(query, kb):
    """
    Advanced offline QA search engine.
    Uses TF-IDF similarity vector matching across indexed facts for extreme precision.
    Includes exact intent routing for conversational safety.
    """
    if not kb:
        return "I am sorry, but the knowledge base is currently empty. Please trigger a crawl first using /sync."
        
    query_clean = query.lower().strip()
    
    # Precise high-fidelity conversational routing to prevent unrelated vector matches
    # 1. Greetings
    greeting_patterns = [r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgreetings\b', r'\bgood\s+morning\b', r'\bgood\s+afternoon\b', r'\bgood\s+evening\b']
    if any(re.search(pat, query_clean) for pat in greeting_patterns):
        return "Hello! I am Vihil InfoTech's AI assistant. I have been trained on our official company context. How can I help you today?"
        
    # 2. Identity & Name
    identity_patterns = [
        r'\bwho\s+are\s+you\b', r'\bwhat\s+is\s+your\s+name\b', r'\byour\s+name\b',
        r'\bwho\s+made\s+you\b', r'\bwho\s+created\s+you\b', r'\bwho\s+developed\s+you\b',
        r'\bintroduce\s+yourself\b'
    ]
    if any(re.search(pat, query_clean) for pat in identity_patterns):
        return "I am Vihil InfoTech's official AI assistant. I am programmed to help you explore our services, technical stacks, development process, team profiles, and office locations!"

    # 3. How are you
    how_are_you_patterns = [
        r'\bhow\s+are\s+you\b', r'\bhow\s+do\s+you\s+do\b', r'\bhope\s+you\s+are\s+well\b',
        r'\bhow\'s\s+it\s+going\b', r'\bdoing\s+well\b'
    ]
    if any(re.search(pat, query_clean) for pat in how_are_you_patterns):
        return "I'm doing fantastic, thank you for asking! I'm completely ready to help you explore Vihil InfoTech's engineering offerings. What can I assist you with today?"

    # 4. Capabilities / What can you do
    capabilities_patterns = [
        r'\bwhat\s+do\s+you\s+do\b', r'\bwhat\s+can\s+you\s+do\b', r'\byour\s+capabilities\b',
        r'\bhow\s+can\s+you\s+help\b', r'\bhelp\s+me\b', r'\bwhat\s+are\s+you\s+capable\s+of\b'
    ]
    if any(re.search(pat, query_clean) for pat in capabilities_patterns):
        return (
            "I am specialized in helping you discover Vihil InfoTech! Specifically, I can:\n"
            "- Explain our **Core Services** (Web, Mobile, Desktop engineering, Custom CMS).\n"
            "- Describe our **5-Step Development Process** (Research, Planning, Implementation, Testing, Optimization).\n"
            "- Introduce our **Expert Team** (like Bharat Desai, our CEOs, and designers).\n"
            "- Give **Contact Information** (Email, phone number, physical office location in Nadiad, Gujarat).\n"
            "- Share our **Technologies Stack** (React, Next.js, Python, FastAPI, Flutter, etc.).\n\n"
            "Ask me about any of these, or set up a live Gemini API key for an unrestricted chat!"
        )

    # 5. Thanks / Gratitude
    thanks_patterns = [
        r'\bthank\s+you\b', r'\bthanks\b', r'\bappreciate\s+it\b', r'\bthankful\b',
        r'\bgreat\s+help\b', r'\bawesome\b', r'\bgood\s+job\b'
    ]
    if any(re.search(pat, query_clean) for pat in thanks_patterns):
        return "You're very welcome! Helping you is what I do best. Let me know if there's anything else about Vihil InfoTech you want to explore!"

    # 6. Goodbye / Farewell
    goodbye_patterns = [
        r'\bbye\b', r'\bgoodbye\b', r'\bsee\s+you\b', r'\btalk\s+to\s+you\s+later\b',
        r'\bexit\b', r'\bquit\b'
    ]
    if any(re.search(pat, query_clean) for pat in goodbye_patterns):
        return "Goodbye! Thank you for chatting. We hope to collaborate on your next big digital idea soon! Have an amazing day!"

    # Precise high-importance triggers to override vector searches if needed with word boundaries
    ceo_patterns = [r'\bceo\b', r'\bfounder\b', r'\bhead\b', r'\bwho\s+runs\b', r'\bleader\b']
    if any(re.search(pat, query_clean) for pat in ceo_patterns):
        ceo = next((m for m in kb.get("team", []) if "ceo" in m.get("position", "").lower()), None)
        if ceo:
            return f"The CEO of Vihil InfoTech is **{ceo['name']}**. Under his profile: '{ceo.get('desc', '')}'."
            
    cto_patterns = [r'\bcto\b', r'\btech\s+lead\b']
    if any(re.search(pat, query_clean) for pat in cto_patterns):
        cto = next((m for m in kb.get("team", []) if "cto" in m.get("position", "").lower()), None)
        if cto:
            return f"The CTO of Vihil InfoTech is **{cto['name']}**. Under his profile: '{cto.get('desc', '')}'."

    # ENFORCE STRICT CORE BUSINESS KEYWORD FILTERING TO AVOID UNRELATED HALLUCINATING MATCHES
    core_business_keywords = {
        "contact", "phone", "email", "address", "location", "office", "nadiad", "gujarat", "india",
        "service", "services", "web", "mobile", "app", "application", "desktop", "pwa", "chatbot",
        "development", "seo", "marketing", "security", "big data", "data", "cyber", "work",
        "team", "member", "ceo", "cto", "pm", "developer", "engineer", "designer", "bharat", "manish", "jay",
        "process", "methodology", "workflow", "step", "planning", "research", "test", "testing", "optimize",
        "faq", "faqs", "question", "questions", "answer", "quote", "cost", "price", "portfolio", "carousel",
        "android", "ios", "react", "nextjs", "python", "fastapi", "node"
    }
    
    # Preprocess and expand the query to support multiple languages and synonyms
    expanded_query = preprocess_multilingual_query(query)
    
    # Tokenize the original query to check for core keywords
    original_tokens = clean_and_tokenize(query)
    
    # Check if the query has at least some relevance to Vihil/Infotech or contains core business keywords
    is_relevant_topic = any(w in core_business_keywords for w in original_tokens) or "vihil" in query_clean or "infotech" in query_clean
    
    if not is_relevant_topic and original_tokens:
        # If the question contains no company name and no business keywords, fail early to prevent wrong answers
        return (
            "I am Vihil InfoTech's AI Assistant. Since the Gemini API is currently offline/inactive, I am operating on local cached knowledge base facts. "
            "I couldn't find a confident, highly-relevant match for your query in our local site cache.\n\n"
            "**To resolve this and unlock smart general conversation**:\n"
            "1. **Upgrade to Live AI Mode**: If you have a Gemini API key, configure it using `/setkey <your_key>` in the terminal, or save it as `GEMINI_API_KEY` in a `.env` file. This unlocks the powerful `gemini-1.5-flash` model, allowing me to answer any general, conversational, or advanced questions beautifully!\n"
            "2. **Ask about Vihil InfoTech**: You can ask me about our core services, development process, specialized technologies, and team members, and I'll fetch the answers instantly from our local cache.\n"
            "3. **Contact us directly**: Feel free to reach out to our team at vihil3010@gmail.com or call +91 7016421339. We'd love to help you build your digital vision!"
        )

    index = build_search_index(kb)
    results = compute_tfidf_score(expanded_query, index)
    
    # Increase threshold to 0.35 to prevent random single word mismatches from returning illogical results
    if results and results[0][0] > 0.35:
        best_score, best_doc = results[0]
        return best_doc["answer"]
        
    return (
        "I am Vihil InfoTech's AI Assistant. Since the Gemini API is currently offline/inactive, I am operating on local cached knowledge base facts. "
        "I couldn't find a confident, highly-relevant match for your query in our local site cache.\n\n"
        "**To resolve this and unlock smart general conversation**:\n"
        "1. **Upgrade to Live AI Mode**: If you have a Gemini API key, configure it using `/setkey <your_key>` in the terminal, or save it as `GEMINI_API_KEY` in a `.env` file. This unlocks the powerful `gemini-1.5-flash` model, allowing me to answer any general, conversational, or advanced questions beautifully!\n"
        "2. **Ask about Vihil InfoTech**: You can ask me about our core services, development process, specialized technologies, and team members, and I'll fetch the answers instantly from our local cache.\n"
        "3. **Contact us directly**: Feel free to reach out to our team at vihil3010@gmail.com or call +91 7016421339. We'd love to help you build your digital vision!"
    )

def detect_language_simple(text):
    """Simple heuristic to detect Gujarati, Hindi/Devanagari, or default to English."""
    if re.search(r'[\u0A80-\u0AFF]', text):
        return "gu"
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
    if re.search(r'[\u0400-\u04FF]', text):
        return "ru"
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar"
    if re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', text):
        return "ja"
    if re.search(r'[\u4E00-\u9FFF]', text):
        return "zh"
    if re.search(r'[\uAC00-\uD7AF]', text):
        return "ko"
    return "en"

def query_groq_api(query, kb, api_key, stream=False):
    """
    Direct REST API client for Groq to support Llama 3 models.
    Uses standard urllib to bypass extra library requirements.
    """
    import urllib.request
    import json
    import ssl
    import datetime
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    system_instruction = (
        "You are Vihil InfoTech's highly wise, helpful, and friendly AI assistant. "
        "Your goal is to answer questions about Vihil InfoTech accurately, comprehensively, and beautifully using the provided website context.\n"
        "Guidelines:\n"
        "- Be exceptionally professional, insightful, and warm in your responses.\n"
        "- Communicate naturally in the language of the user's prompt (supporting all world languages, matching scripts and tone exactly).\n"
        "- Use the provided website context to answer company-related questions. If a question is about Vihil InfoTech but the context does not contain the exact details, answer politely using general helpful company framing, or guide them to contact the team, rather than giving a dry, robotic refusal. If the query is completely unrelated to the company (e.g., general chat, greetings, math, science, programming), act as a wise and knowledgeable general AI companion, answering their query beautifully while gracefully tying it back to how Vihil InfoTech can help build digital solutions!\n"
        "- If they greet you, give a highly localized, warm time-of-day greeting (matching their language and script) based on the Current Local Time.\n"
    )
    
    if not stream:
        system_instruction += (
            "\nResponse format MUST be a JSON object with two fields:\n"
            "1. 'answer': The actual text response.\n"
            "2. 'lang_code': The standard 2-letter language code (e.g. 'en', 'hi', 'gu', 'es', 'fr', 'ja', 'ru', etc.) of the generated answer."
        )
    else:
        system_instruction += "\nGenerate your response in standard Markdown format. Stream the response directly."
        
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    hour = datetime.datetime.now().hour
    greeting_context = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    
    context_str = json.dumps(kb, indent=2, ensure_ascii=False)
    prompt = (
        f"Current Local Time: {current_time}.\n"
        f"When the user greets you or asks for the time, naturally respond with the appropriate real-time greeting (e.g., '{greeting_context}').\n\n"
        f"Website Context:\n{context_str}\n\n"
        f"User Question: {query}"
    )
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    if not stream:
        body["response_format"] = {"type": "json_object"}
    else:
        body["stream"] = True
        
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return req, ctx

def answer_query(query, filepath="knowledge_base.json", lang_pref=None):
    """Query answering coordinator. Uses Groq or Gemini API if key is present, else fall back to local rule engine."""
    import urllib.request
    import json
    load_dotenv_custom()
    kb = load_knowledge_base(filepath)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    
    # 1. Try Groq API first if available
    if groq_api_key:
        try:
            req, ctx = query_groq_api(query, kb, groq_api_key, stream=False)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content_str = res_data["choices"][0]["message"]["content"].strip()
                try:
                    res_json = json.loads(content_str)
                    ans = res_json.get("answer", "")
                    lang_code = res_json.get("lang_code", "en")
                    return ans, lang_code
                except Exception:
                    return content_str, detect_language_simple(content_str)
        except Exception as e:
            print(f"Groq API Error: {e}", file=sys.stderr)
            
    # 2. Try Gemini API next if available
    if gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            
            system_instruction = (
                "You are Vihil InfoTech's highly wise, helpful, and friendly AI assistant. "
                "Your goal is to answer questions about Vihil InfoTech accurately, comprehensively, and beautifully using the provided website context.\n"
                "Guidelines:\n"
                "- Be exceptionally professional, insightful, and warm in your responses.\n"
                "- Communicate naturally in the language of the user's prompt (supporting all world languages, matching scripts and tone exactly).\n"
                "- Use the provided website context to answer company-related questions. If a question is about Vihil InfoTech but the context does not contain the exact details, answer politely using general helpful company framing, or guide them to contact the team, rather than giving a dry, robotic refusal. If the query is completely unrelated to the company (e.g., general chat, greetings, math, science, programming), act as a wise and knowledgeable general AI companion, answering their query beautifully while gracefully tying it back to how Vihil InfoTech can help build digital solutions!\n"
                "- If they greet you, give a highly localized, warm time-of-day greeting (matching their language and script) based on the Current Local Time.\n"
                "Response format MUST be a JSON object with two fields:\n"
                "1. 'answer': The actual text response.\n"
                "2. 'lang_code': The standard 2-letter language code (e.g. 'en', 'hi', 'gu', 'es', 'fr', 'ja', 'ru', etc.) of the generated answer."
            )
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            hour = datetime.datetime.now().hour
            greeting_context = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"

            context_str = json.dumps(kb, indent=2, ensure_ascii=False)
            prompt = (
                f"Current Local Time: {current_time}.\n"
                f"When the user greets you or asks for the time, naturally respond with the appropriate real-time greeting (e.g., '{greeting_context}').\n\n"
                f"Website Context:\n{context_str}\n\n"
                f"User Question: {query}"
            )
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                }
            )
            
            try:
                res_json = json.loads(response.text.strip())
                ans = res_json.get("answer", "")
                lang_code = res_json.get("lang_code", "en")
                return ans, lang_code
            except Exception as json_err:
                text = response.text.strip()
                return text, detect_language_simple(text)
                
        except Exception as e:
            print(f"Gemini API Error: {e}", file=sys.stderr)
            
    ans = fallback_qa(query, kb)
    return ans, detect_language_simple(ans)

def stream_answer_query(query, filepath="knowledge_base.json"):
    """
    Generator that yields chunks of the answer.
    Enables highly responsive real-time streaming in the terminal and browser.
    Supports Groq, Gemini, or local search fallback.
    """
    import urllib.request
    import json
    load_dotenv_custom()
    kb = load_knowledge_base(filepath)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    
    # 1. Try Groq API first if available
    if groq_api_key:
        try:
            req, ctx = query_groq_api(query, kb, groq_api_key, stream=True)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                buffer = ""
                for chunk in response:
                    buffer += chunk.decode("utf-8", errors="ignore")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data_content = line[5:].strip()
                            if data_content == "[DONE]":
                                break
                            try:
                                json_data = json.loads(data_content)
                                delta = json_data["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except Exception:
                                pass
            return
        except Exception as e:
            print(f"Groq Stream Error: {e}", file=sys.stderr)

    # 2. Try Gemini API next if available
    if gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            
            system_instruction = (
                "You are Vihil InfoTech's highly wise, helpful, and friendly AI assistant.\n"
                "Your goal is to answer questions about Vihil InfoTech accurately, comprehensively, and beautifully using the provided website context.\n"
                "Guidelines:\n"
                "- Be exceptionally professional, insightful, and warm in your responses.\n"
                "- Communicate naturally in the language of the user's prompt (supporting all world languages, matching scripts and tone exactly).\n"
                "- Use the provided website context to answer company-related questions. If a question is about Vihil InfoTech but the context does not contain the exact details, answer politely using general helpful company framing, or guide them to contact the team, rather than giving a dry, robotic refusal.\n"
                "- If the query is completely unrelated to the company (e.g., general chat, greetings, math, science, programming), act as a wise and knowledgeable general AI companion, answering their query beautifully while gracefully tying it back to how Vihil InfoTech can help build digital solutions!\n"
                "- If they greet you, give a highly localized, warm time-of-day greeting (matching their language and script) based on the Current Local Time.\n"
                "- Stream the answer directly as markdown text."
            )
            
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            hour = datetime.datetime.now().hour
            greeting_context = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
                
            context_str = json.dumps(kb, indent=2, ensure_ascii=False)
            prompt = (
                f"Current Local Time: {current_time}.\n"
                f"When the user greets you or asks for the time, naturally respond with the appropriate real-time greeting (e.g., '{greeting_context}').\n\n"
                f"Website Context:\n{context_str}\n\n"
                f"User Question: {query}\n\n"
                "Generate your response in standard Markdown format. Stream the response directly."
            )
            
            response = model.generate_content(
                prompt,
                stream=True,
                generation_config={
                    "temperature": 0.1
                }
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            print(f"Gemini Stream Error: {e}", file=sys.stderr)
            
    ans = fallback_qa(query, kb)
    words = ans.split(" ")
    for i, word in enumerate(words):
        yield (word + " " if i < len(words) - 1 else word)
        time.sleep(0.015)

def show_spinner_animation(duration=2.0, message="Thinking"):
    """Shows a beautiful micro-animation spinner in the terminal."""
    spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    start_time = time.time()
    idx = 0
    while time.time() - start_time < duration:
        char = spinner_chars[idx % len(spinner_chars)]
        sys.stdout.write(f"\r{Colors.CYAN}{char}{Colors.ENDC} {message}...")
        sys.stdout.flush()
        time.sleep(0.08)
        idx += 1
    sys.stdout.write("\r" + " " * (len(message) + 15) + "\r")
    sys.stdout.flush()

def run_live_crawl(filepath="knowledge_base.json"):
    """Runs scraper in background and prints live console updates."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== SYNCING KNOWLEDGE BASE FROM LIVE WEBSITE ==={Colors.ENDC}")
    show_spinner_animation(1.0, "Connecting to www.vihilinfotech.com")
    try:
        import scraper
        kb = scraper.scrape_vihil()
        if kb:
            print(f"{Colors.GREEN}✔ Knowledge base successfully updated and saved to {filepath}.{Colors.ENDC}\n")
        else:
            print(f"{Colors.RED}✘ Crawl returned empty database. Check connection.{Colors.ENDC}\n")
    except Exception as e:
        print(f"{Colors.RED}✘ Sync failed: {e}{Colors.ENDC}\n")

def set_api_key(key):
    """Saves API key to .env file and reloads it."""
    key = key.strip()
    if not key:
        print(f"{Colors.RED}Error: API key cannot be empty.{Colors.ENDC}")
        return
        
    lines = []
    found_gemini = False
    found_groq = False
    env_path = ".env"
    
    is_groq = key.startswith("gsk_")
    key_var = "GROQ_API_KEY" if is_groq else "GEMINI_API_KEY"
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(f"{key_var}="):
                    lines.append(f"{key_var}={key}\n")
                    if is_groq:
                        found_groq = True
                    else:
                        found_gemini = True
                else:
                    lines.append(line)
                    
    if is_groq and not found_groq:
        lines.append(f"GROQ_API_KEY={key}\n")
    elif not is_groq and not found_gemini:
        lines.append(f"GEMINI_API_KEY={key}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    os.environ[key_var] = key
    print(f"\n{Colors.GREEN}✔ API key successfully configured and saved to .env!{Colors.ENDC}")
    print(f"{Colors.GREEN}AI assistant is now upgraded to Live {'Groq' if is_groq else 'Gemini'} Mode.{Colors.ENDC}\n")

def print_status(filepath="knowledge_base.json"):
    kb = load_knowledge_base(filepath)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    
    if groq_api_key:
        api_status = f"{Colors.GREEN}CONNECTED (Groq Llama-3.3-70b-versatile){Colors.ENDC}"
    elif gemini_api_key:
        api_status = f"{Colors.GREEN}CONNECTED (Gemini-1.5-flash){Colors.ENDC}"
    else:
        api_status = f"{Colors.YELLOW}OFFLINE MODE (Local TF-IDF Vector Search Engine){Colors.ENDC}"
    
    services_count = len(kb.get("services", []))
    team_count = len(kb.get("team", []))
    faqs_count = len(kb.get("faqs", []))
    process_count = len(kb.get("process", []))
    techs_count = len(kb.get("technologies", []))
    
    cur_time = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== SYSTEM STATUS ==={Colors.ENDC}")
    print(f"- **AI Power Status**: {api_status}")
    print(f"- **Loaded Knowledge Base**: {Colors.CYAN}{filepath}{Colors.ENDC}")
    print(f"  - Core Services: {services_count}")
    print(f"  - Team Members: {team_count}")
    print(f"  - Frequently Asked Qs: {faqs_count}")
    print(f"  - Process Steps: {process_count}")
    print(f"  - Tech Stack Items: {techs_count}")
    print(f"- **Current Local Time**: {cur_time}")
    print(f"=====================\n")

def view_category(category, filepath="knowledge_base.json"):
    kb = load_knowledge_base(filepath)
    category = category.lower().strip()
    
    if category == "services":
        services = kb.get("services", [])
        if not services:
            print("No services found.")
            return
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== CORE SERVICES ==={Colors.ENDC}")
        for i, s in enumerate(services, 1):
            title = s.get('title', '').strip()
            clean_title = re.sub(r'^[0-9\.\s]+', '', title)
            print(f"{Colors.BOLD}{i}. {clean_title}{Colors.ENDC}")
            print(f"   {s.get('desc1') or s.get('desc')}\n")
            
    elif category == "team":
        team = kb.get("team", [])
        if not team:
            print("No team members found.")
            return
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== VIHIL INFOTECH TEAM ==={Colors.ENDC}")
        for i, m in enumerate(team, 1):
            pos = m.get('position', '').replace('(', '').replace(')', '').strip()
            print(f"{Colors.BOLD}{i}. {m.get('name')} - {Colors.YELLOW}{pos}{Colors.ENDC}")
            if m.get('desc'):
                print(f"   Role: {m.get('desc')}")
            print()
            
    elif category == "faqs":
        faqs = kb.get("faqs", [])
        if not faqs:
            print("No FAQs found.")
            return
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== FREQUENTLY ASKED QUESTIONS ==={Colors.ENDC}")
        for i, f in enumerate(faqs, 1):
            print(f"{Colors.BOLD}Q{i}: {f.get('question')}{Colors.ENDC}")
            print(f"A:  {f.get('answer')}\n")
            
    elif category == "tech" or category == "technologies":
        techs = kb.get("technologies", [])
        if not techs:
            print("No technologies indexed.")
            return
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== SPECIALIZED TECHNOLOGIES ==={Colors.ENDC}")
        print(", ".join([f"{Colors.BOLD}{t}{Colors.ENDC}" for t in techs]) + "\n")
    else:
        print(f"{Colors.RED}Unknown category: {category}. Choose 'services', 'team', 'faqs', or 'tech'.{Colors.ENDC}")

def print_help():
    print(f"\n{Colors.BOLD}{Colors.CYAN}=== AVAILABLE COMMANDS ==={Colors.ENDC}")
    print(f"  {Colors.BOLD}/help{Colors.ENDC}             - Show this help menu.")
    print(f"  {Colors.BOLD}/status{Colors.ENDC}           - Display AI configurations & database stats.")
    print(f"  {Colors.BOLD}/sync{Colors.ENDC}             - Crawl & refresh local database from live website.")
    print(f"  {Colors.BOLD}/setkey <key>{Colors.ENDC}     - Save Gemini API key to .env file for Live Mode.")
    print(f"  {Colors.BOLD}/view <cat>{Colors.ENDC}       - View lists ('services', 'team', 'faqs', 'tech').")
    print(f"  {Colors.BOLD}/clear{Colors.ENDC}            - Clear the terminal screen.")
    print(f"  {Colors.BOLD}/exit{Colors.ENDC} or {Colors.BOLD}/quit{Colors.ENDC}    - Exit the interactive assistant.")
    print(f"==========================\n")

def run_terminal_client(filepath="knowledge_base.json"):
    init_terminal()
    load_dotenv_custom()
    
    banner = f"""{Colors.BOLD}{Colors.CYAN}
===================================================
     __   ___ _    _ _    _          ___  _    
     \\ \\ / (_) |__(_) |  / \\  _   _ |  _|| |   
      \\ V /| | '_ \\ | | / _ \\| | | || |_ | |   
       \\ / | | | | | | |/ ___ \\ |_| ||  _|| |__ 
        V  |_|_| |_|_|_/_/   \\_\\__,_||_|  |____|
                                               
           ★  AI ASSISTANT TERMINAL  ★
===================================================
{Colors.ENDC}"""
    print(banner)
    
    kb = load_knowledge_base(filepath)
    if not kb:
        print(f"{Colors.YELLOW}Warning: 'knowledge_base.json' not found or empty!{Colors.ENDC}")
        print(f"Please run {Colors.BOLD}/sync{Colors.ENDC} inside this terminal to crawl the website and build it.\n")
    
    print_status(filepath)
    print(f"Type a question to ask the AI, or {Colors.BOLD}/help{Colors.ENDC} to see commands.")
    print("-" * 50)
    
    while True:
        try:
            prompt_str = f"{Colors.BOLD}{Colors.GREEN}vihil-ai > {Colors.ENDC}"
            user_input = input(prompt_str).strip()
            
            if not user_input:
                continue
                
            if user_input.startswith("/"):
                parts = user_input.split(" ", 1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if cmd in ["/exit", "/quit"]:
                    print(f"\n{Colors.BOLD}{Colors.BLUE}Thank you for chatting with Vihil InfoTech AI! Goodbye.{Colors.ENDC}\n")
                    break
                elif cmd == "/help":
                    print_help()
                elif cmd == "/status":
                    print_status(filepath)
                elif cmd == "/clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                elif cmd == "/sync":
                    run_live_crawl(filepath)
                elif cmd == "/setkey":
                    set_api_key(arg)
                elif cmd == "/view":
                    if not arg:
                        print(f"{Colors.RED}Please specify a category: /view services, /view team, /view faqs, or /view tech{Colors.ENDC}")
                    else:
                        view_category(arg, filepath)
                else:
                    print(f"{Colors.RED}Unknown command: {cmd}. Type /help for assistance.{Colors.ENDC}")
                continue
                
            # Regular question answering with streaming
            groq_api_key = os.environ.get("GROQ_API_KEY")
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if groq_api_key:
                engine_label = "Groq Llama-3"
            elif gemini_api_key:
                engine_label = "Gemini Flash"
            else:
                engine_label = "Local TF-IDF Search"
            
            sys.stdout.write(f"\n{Colors.BOLD}{Colors.BLUE}[AI ({engine_label}) is thinking...]{Colors.ENDC}\n")
            sys.stdout.flush()
            
            show_spinner_animation(0.4, "Searching database")
            
            sys.stdout.write(f"{Colors.CYAN}")
            sys.stdout.flush()
            
            # Call streaming generator
            for chunk in stream_answer_query(user_input, filepath):
                sys.stdout.write(chunk)
                sys.stdout.flush()
                
            sys.stdout.write(f"{Colors.ENDC}\n")
            print("-" * 50 + "\n")
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Session interrupted. Type /exit to quit.{Colors.ENDC}\n")
        except EOFError:
            print(f"\n\n{Colors.BOLD}{Colors.BLUE}Goodbye!{Colors.ENDC}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}An error occurred: {e}{Colors.ENDC}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        ans, lang = answer_query(q)
        print(ans)
    else:
        run_terminal_client()
