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

def prune_json(data):
    """Recursively removes large or useless metadata keys from JSON to shrink payload size."""
    if isinstance(data, dict):
        return {k: prune_json(v) for k, v in data.items() if k not in ["_id", "__v", "createdAt", "updatedAt", "image", "resume", "extensions", "icon"]}
    elif isinstance(data, list):
        return [prune_json(item) for item in data]
    else:
        return data

def clean_and_tokenize(text):
    """Clean, lowercase, and tokenize text into a set of words, removing common stop words. Supports Indic script diacritics."""
    if not text:
        return set()
    import unicodedata
    text_lower = text.lower()
    # Replace non-letter, non-mark, non-number, non-space characters with space (preserves Indic diacritics)
    cleaned_chars = []
    for c in text_lower:
        cat = unicodedata.category(c)
        if cat.startswith('L') or cat.startswith('M') or cat.startswith('N') or c.isspace():
            cleaned_chars.append(c)
        else:
            cleaned_chars.append(' ')
    cleaned = "".join(cleaned_chars)
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
    if isinstance(stats, dict):
        # New DB structure
        stats = stats.get("vihildetails", {})
        if stats:
            stats_str = f"Happy Clients: {stats.get('happyClients')}, Completed Projects: {stats.get('completedProjects')}, Rating: {stats.get('rating')}"
            index.append({
                "type": "statistics",
                "title": "Company Statistics & Achievements Ratings Projects",
                "search_text": f"statistics stats numbers count completed projects happy clients ratings rating staff experience size {stats_str}",
                "content": stats_str,
                "answer": f"### 📊 Vihil InfoTech Statistics\n- **Happy Clients**: {stats.get('happyClients', '50+')}\n- **Completed Projects**: {stats.get('completedProjects', '66+')}\n- **Experienced Staff**: {stats.get('experiencedStaff', '10+')}\n- **Rating**: {stats.get('rating', '5')}"
            })
    elif stats:
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
    contact_details = contact.get("contactdetails", contact)
    
    if contact_details:
        addr = contact_details.get("address", "")
        email = contact_details.get("email", "")
        phone = contact_details.get("phone", "")
        response_time = contact_details.get("response_time", contact_details.get("responseTime", "We reply within 24 hours"))
        socials = contact_details.get("social_links", {})
        socials_str = "\n".join([f"- **{k.capitalize()}**: [{v}]({v})" for k, v in socials.items()])

        index.append({
            "type": "contact",
            "title": "Contact Information Email Phone Location Address Office Social",
            "search_text": (
                "contact email phone mobile number telephone support vihil3010@gmail.com +91 7016421339 "
                "instagram linkedin facebook address office location where headquarter nadiad gujarat india "
                f"book call reach out inquiry quote {addr} {email} {phone}"
            ),
            "content": f"{addr} {email} {phone} {socials_str}",
            "answer": (
                f"### 📞 Contact Vihil InfoTech\n"
                f"- 📍 **Address**: {addr}\n"
                f"- ✉ **Email**: {email}\n"
                f"- 📞 **Phone**: {phone}\n"
                f"- ⏱ **Response Time**: {response_time}\n\n"
                f"**Social & Web**:\n{socials_str}"
            )
        })
        
    # 5. Core Services
    services_list = kb.get("services", [])
    if isinstance(services_list, dict):
        services_list = services_list.get("vihilservices", []) + services_list.get("vihilcapabilities", [])
        
    for s in services_list:
        title = s.get("title", "").strip()
        clean_title = re.sub(r'^[0-9\.\s]+', '', title)
        desc1 = s.get("desc1", "")
        desc = s.get("description", s.get("desc", ""))
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
        
    # 6b. AI / ML Capabilities (new section)
    ai_ml = kb.get("ai_ml", {})
    if ai_ml:
        caps = ai_ml.get("capabilities", [])
        caps_str = "\n".join([
            f"- **{c.get('name')}**: {c.get('desc','')}" +
            (f"\n  Features: {', '.join(c.get('features', []))}" if c.get('features') else "") +
            (f"\n  Stack: {', '.join(c.get('tech_stack', []))}" if c.get('tech_stack') else "")
            for c in caps
        ])
        index.append({
            "type": "ai_ml",
            "title": "AI ML Capabilities Artificial Intelligence Machine Learning LLM RAG Automation",
            "search_text": (
                "ai ml artificial intelligence machine learning llm large language model rag retrieval augmented generation "
                "generative ai workflow automation langchain fastapi data intelligence forecasting chatbot copilot smart "
                f"{ai_ml.get('headline', '')} {caps_str}"
            ),
            "content": caps_str,
            "answer": f"### 🤖 AI/ML Capabilities at Vihil InfoTech\n{ai_ml.get('headline','')}\n\n{caps_str}"
        })
        
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
    team_list = kb.get("team", [])
    if isinstance(team_list, dict):
        team_list = team_list.get("teammembers", [])
        
    for m in team_list:
        name = m.get("name", "").strip()
        pos = m.get("position", "").replace("(", "").replace(")", "").strip()
        desc = m.get("desc", m.get("description", "")).strip()
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
    if isinstance(techs, list) and techs and isinstance(techs[0], dict):
        techs_str = ", ".join([t.get("content", "") for t in techs if t.get("type") == "tech"])
        techs = [t.get("content", "") for t in techs if t.get("type") == "tech"]
    elif techs:
        techs_str = ", ".join(techs)
        
    if techs:
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
        "contact contacts phone email address location office number mobile": [
            "संपर्क", "सम्पर्क", "સંપર્ક", "contact", "number", "phone", "email", "address", "location", 
            "office", "headquarter", "nadiad", "gujarat", "india", "ફોન", "મોબાઈલ", "સરનામું", "ઈમેલ", 
            "કહા", "कहा", "कहाँ", "પતા", "पता", "નંબર", "नंबर", "फ़ोन"
        ],
        # Services / Work concepts
        "service services work capability capabilities": [
            "सेवा", "સેવા", "काम", "કામ", "services", "offer", "do", "build", "develop", "make", "create", 
            "બનાવો", "બનાવે", "बनाता", "બનાવતી"
        ],
        # Mobile app development
        "mobile app application android ios phone": [
            "मोबाइल", "મોબાઈલ", "app", "application", "android", "ios", "એપ", "ऐप", "phone app"
        ],
        # Web development
        "web website site page": [
            "वेबसाइट", "વેબસાઈટ", "वेब", "વેબ", "website", "site", "page", "nextjs", "react"
        ],
        # Team / Owner / CEO concepts
        "team member staff employee ceo cto owner founder boss bharat manish": [
            "टीम", "ટીમ", "ceo", "cto", "owner", "founder", "boss", "member", "staff", "employee", 
            "માલિક", "ભરત", "भरत", "મનીષ", "मनीष", "જેય", "जय"
        ],
        # QA / Security
        "security cyber safe protect defense compliance audit": [
            "सुरक्षा", "સુરક્ષા", "cyber", "protect", "safe", "secure"
        ],
        # Development Process
        "process step methodology workflow stage cycle": [
            "काम करने का तरीका", "પદ્ધતિ", "चरण", "पद्धति", "process", "step", "method", "workflow"
        ],
        # AI / ML
        "ai ml artificial intelligence machine learning llm rag langchain copilot bot automation chatbot": [
            "ai", "ml", "artificial intelligence", "machine learning", "llm", "rag", "langchain", 
            "copilot", "bot", "automation", "generative", "chatbot", "smart", "intelligent", "bots"
        ],
        # Cloud & Infrastructure
        "cloud devops aws gcp azure infrastructure server deployment hosting": [
            "cloud", "devops", "aws", "gcp", "azure", "infrastructure", "server", "deployment", "hosting"
        ],
        # LinkedIn / Social
        "linkedin social instagram facebook profile follow": [
            "linkedin", "social", "instagram", "facebook", "profile", "follow"
        ],
        # FAQ / Questions
        "faq faqs question questions answer query support common": [
            "faq", "faqs", "question", "questions", "answer", "support", "પ્રશ્ન", "સવાલ", "જવાબ", 
            "प्रश्न", "सवाल", "जवाब"
        ],
        # Technology / Stack
        "technology tech stack languages database frontend backend framework tools": [
            "tech", "technology", "technologies", "stack", "ટેકનોલોજી", "ટેક", "तकनीक", "टेक्नोलॉजी", "टेक"
        ],
        # Careers / Job
        "career careers job jobs vacancy vacancies hiring apply resume CV": [
            "career", "careers", "job", "jobs", "vacancy", "vacancies", "hiring", "apply", "resume", 
            "નોકરી", "ભરતી", "કારકિર્દી", "नौकरी", "भर्ती", "करियर"
        ],
        # Portfolio / Testimonial
        "portfolio testimonial testimonials highlight highlights client clients rating review reviews": [
            "portfolio", "testimonial", "testimonials", "highlight", "highlights", "client", "clients", 
            "rating", "ratings", "review", "reviews", "પોર્ટફોલિયો", "ગ્રાહક", "રીવ્યુ", "पोर्टफोलियो", "ग्राहक", "रिव्यू"
        ],
        # About / Company
        "about company vision mission history background": [
            "about", "company", "vision", "mission", "history", "background", "વિશે", "કંપની", "ધ્યેય", 
            "વિઝન", "बारे", "कंपनी", "लक्ष्य", "विजन"
        ]
    }
    
    expanded_terms = []
    for concept, keywords in translation_maps.items():
        for keyword in keywords:
            if keyword in q_lower:
                expanded_terms.append(concept)
                break
                
    # 2. English synonyms expansion for common questions
    synonyms = {
        "location address office nadiad gujarat india": ["where", "location", "address", "office", "city", "nadiad", "gujarat", "india", "place", "map", "situated", "located"],
        "ceo cto owner founder bharat manish": ["ceo", "cto", "owner", "founder", "head", "boss", "runs", "manage", "bharat", "manish", "desai", "shah"],
        "team member staff developers engineers": ["who works", "member", "staff", "employees", "team", "people", "developers", "engineers"],
        "contact email phone call mobile number support social": ["email", "phone", "call", "mobile", "number", "reach", "support", "talk to", "contact", "linkedin", "instagram", "facebook", "social", "book"],
        "service services capabilities workflow solutions": ["services", "capabilities", "what we do", "build", "develop", "create", "offering", "solutions"],
        "quote price cost estimate": ["price", "cost", "charge", "quote", "payment", "budget", "how much"],
        "process methodology workflow steps stages": ["process", "methodology", "workflow", "steps", "stages", "how do you build", "how you work"],
        "faq faqs question questions answer support": ["faqs", "questions", "common", "support", "help", "security", "maintenance"],
        "ai ml machine learning artificial intelligence llm rag langchain automation": ["ai", "ml", "machine learning", "artificial intelligence", "llm", "rag", "langchain", "automation", "generative", "copilot", "smart"],
        "cloud devops aws azure gcp infrastructure": ["cloud", "devops", "aws", "azure", "gcp", "infrastructure", "server", "hosting", "deployment"],
    }
    
    for concept, keywords in synonyms.items():
        if any(w in q_lower for w in keywords):
            expanded_terms.append(concept)
            
    # 3. Spelling correction and expansion for team members' names to handle typos/variations (supports English, Gujarati, and Hindi)
    team_names_map = [
        (["hetvi", "shama", "sarma", "sharma", "હેત્વી", "હેતવી", "હતવી", "हेतवी", "हत्वी", "શર્મા", "શરમા", "शर्मा", "शमा"], "hetvi sharma"),
        (["manish", "manis", "મનીષ", "મનીસ", "मनीष", "मनिष", "શાહ", "शाह"], "manish shah"),
        (["janvi", "janavi", "જાનવી", "જાનવિ", "जानवी", "जानवि", "શાહ", "शाह"], "janvi shah"),
        (["dhaval", "dhavel", "ધવલ", "ધવેલ", "धवल", "प्रजापति", "પ્રાજપતિ", "પ્રજાપતિ"], "dhaval prajapati"),
        (["kinjal", "kinjel", "કિંજલ", "કિંજેલ", "किंजल", "પટેલ", "पटेल"], "kinjal patel"),
        (["krupal", "krupel", "કૃપાલ", "કૃપેલ", "कृपाल", "વલાંદ", "વાલાંદ", "वलांद", "वोलंद"], "krupal valand"),
        (["dhruvil", "dhruval", "ધ્રુવિલ", "ધ્રુવલ", "ध्रुविल", "मिस्त्री", "મિશ્ત્રી", "મિસ્તરી"], "dhruvil mistry"),
        (["bharat", "ભરત", "भरત", "દેસાઈ", "દેસાઇ", "देसाई"], "bharat desai")
    ]
    for aliases, full_name in team_names_map:
        # Avoid \b word boundary bug for Indic/Unicode scripts
        if any(re.search(rf'(?:^|[^a-zA-Z0-9\u0A80-\u0AFF\u0900-\u097F]){re.escape(alias)}(?:$|[^a-zA-Z0-9\u0A80-\u0AFF\u0900-\u097F])', q_lower) for alias in aliases):
            expanded_terms.append(full_name)
            
    if expanded_terms:
        unique_terms = set()
        for term in expanded_terms:
            unique_terms.update(term.split())
        return query + " " + " ".join(unique_terms)
    return query

def contains_indic_scripts(text):
    """
    Checks if the text contains Gujarati or Hindi (Devanagari) characters.
    """
    if not text:
        return False
    return bool(re.search(r'[\u0A80-\u0AFF\u0900-\u097F]', text))

def translate_to_target_lang(text, target_lang):
    """
    Translates English text to the target language (e.g. 'gu' or 'hi')
    using Google Translate's free API endpoint.
    If it fails, returns the original text.
    """
    if not target_lang or target_lang.lower() in ["en", "auto"]:
        return text
        
    import urllib.request
    import urllib.parse
    import json
    import ssl
    
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
        )
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            translated = "".join([sentence[0] for sentence in data[0] if sentence[0]])
            return translated
    except Exception as e:
        print(f"Translation failed: {e}", file=sys.stderr)
        return text

def fallback_qa(query, kb, lang_pref=None):
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
    # 2. Identity & Name
    identity_patterns = [
        r'\bwho\s+are\s+you\b', r'\bwhat\s+is\s+your\s+name\b', r'\byour\s+name\b',
        r'\bwho\s+made\s+you\b', r'\bwho\s+created\s+you\b', r'\bwho\s+developed\s+you\b',
        r'\bintroduce\s+yourself\b'
    ]
    # 3. How are you
    how_are_you_patterns = [
        r'\bhow\s+are\s+you\b', r'\bhow\s+do\s+you\s+do\b', r'\bhope\s+you\s+are\s+well\b',
        r'\bhow\'s\s+it\s+going\b', r'\bdoing\s+well\b'
    ]
    # 4. Capabilities / What can you do
    capabilities_patterns = [
        r'\bwhat\s+do\s+you\s+do\b', r'\bwhat\s+can\s+you\s+do\b', r'\byour\s+capabilities\b',
        r'\bhow\s+can\s+you\s+help\b', r'\bhelp\s+me\b', r'\bwhat\s+are\s+you\s+capable\s+of\b'
    ]
    # 5. Thanks / Gratitude
    thanks_patterns = [
        r'\bthank\s+you\b', r'\bthanks\b', r'\bappreciate\s+it\b', r'\bthankful\b',
        r'\bgreat\s+help\b', r'\bawesome\b', r'\bgood\s+job\b'
    ]
    # 6. Goodbye / Farewell
    goodbye_patterns = [
        r'\bbye\b', r'\bgoodbye\b', r'\bsee\s+you\b', r'\btalk\s+to\s+you\s+later\b',
        r'\bexit\b', r'\bquit\b'
    ]

    # Handle language-specific offline responses
    if lang_pref == "gu":
        if any(re.search(pat, query_clean) for pat in greeting_patterns):
            return "નમસ્તે! હું વિહિલ ઇન્ફોટેક (Vihil InfoTech) નો AI આસિસ્ટન્ટ છું. હું તમારી શું મદદ કરી શકું?"
        if any(re.search(pat, query_clean) for pat in identity_patterns):
            return "હું વિહિલ ઇન્ફોટેક નો ઓફિશિયલ AI આસિસ્ટન્ટ છું. હું તમને અમારી સેવાઓ, ટેકનોલોજી અને ટીમ પ્રોફાઇલ્સ વિશે માહિતી આપી શકું છું!"
        if any(re.search(pat, query_clean) for pat in how_are_you_patterns):
            return "હું એકદમ મજામાં છું, પૂછવા માટે આભાર! હું તમારી મદદ કરવા માટે તૈયાર છું. આજે હું તમારી શું સહાય કરું?"
        if any(re.search(pat, query_clean) for pat in capabilities_patterns):
            return (
                "હું વિહિલ ઇન્ફોટેક નો AI આસિસ્ટન્ટ છું. હું નીચેની બાબતોમાં મદદ કરી શકું છું:\n"
                "- **સેવાઓ**: વેબ ડેવલપમેન્ટ (React/Next.js), મોબાઈલ એપ્સ (React Native/iOS/Android), AI/ML ઇન્ટિગ્રેશન, ક્લાઉડ, સાયબર સિક્યોરિટી, SEO અને ડેસ્કટોપ એપ્સ.\n"
                "- **વર્કફ્લો**: સંશોધન → આયોજન → અમલીકરણ → પરીક્ષણ અને ડિલિવરી.\n"
                "- **ટીમ**: ૨૦+ એન્જિનિયર્સ, ડિઝાઇનર્સ અને AI સ્પેશિયાલિસ્ટ.\n"
                "- **સંપર્ક**: vihil3010@gmail.com | +91 7016421339.\n\n"
                "ગ્રોક API કી સેટ કરવા માટે `/setkey <key>` નો ઉપયોગ કરો!"
            )
        if any(re.search(pat, query_clean) for pat in thanks_patterns):
            return "તમારો ખૂબ ખૂબ આભાર! જો બીજો કોઈ પ્રશ્ન હોય તો જરૂર જણાવજો."
        if any(re.search(pat, query_clean) for pat in goodbye_patterns):
            return "આવજો! વાત કરવા બદલ ખુબ ખુબ આભાર. તમારો દિવસ શુભ રહે!"

    elif lang_pref == "hi":
        if any(re.search(pat, query_clean) for pat in greeting_patterns):
            return "नमस्ते! मैं विहिल इन्फोटेक (Vihil InfoTech) का एआई सहायक हूँ। मैं आपकी क्या मदद कर सकता हूँ?"
        if any(re.search(pat, query_clean) for pat in identity_patterns):
            return "मैं विहिल इन्फोटेक का आधिकारिक एआई सहायक हूँ। मैं आपको हमारी सेवाओं, तकनीकी स्टैक, विकास प्रक्रिया और टीम प्रोफाइल के बारे में जानकारी दे सकता हूँ!"
        if any(re.search(pat, query_clean) for pat in how_are_you_patterns):
            return "मैं बिल्कुल ठीक हूँ, पूछने के लिए धन्यवाद! मैं आपकी मदद करने के लिए तैयार हूँ। आज मैं आपकी क्या सहायता करूँ?"
        if any(re.search(pat, query_clean) for pat in capabilities_patterns):
            return (
                "मैं विहिल इन्फोटेक का एआई सहायक हूँ। मैं निम्नलिखित क्षेत्रों में आपकी मदद कर सकता हूँ:\n"
                "- **सेवाएं**: वेब विकास (React/Next.js), मोबाइल ऐप्स (React Native/iOS/Android), एआई/एमएल एकीकरण, क्लाउड, साइबर सुरक्षा, एसईओ और डेस्कटॉप ऐप्स।\n"
                "- **विकास प्रक्रिया**: अनुसंधान → योजना → कार्यान्वयन → परीक्षण और वितरण।\n"
                "- **टीम**: 20+ इंजीनियर, डिजाइनर और एआई विशेषज्ञ।\n"
                "- **संपर्क**: vihil3010@gmail.com | +91 7016421339.\n\n"
                "ग्रोक एपीआई कुंजी सेट करने के लिए `/setkey <key>` का उपयोग करें!"
            )
        if any(re.search(pat, query_clean) for pat in thanks_patterns):
            return "आपका बहुत-बहुत धन्यवाद! अगर कोई और सवाल हो तो जरूर बताएं।"
        if any(re.search(pat, query_clean) for pat in goodbye_patterns):
            return "अलविदा! बात करने के लिए धन्यवाद। आपका दिन शुभ हो!"

    # Default English responses
    # 1. Greetings
    if any(re.search(pat, query_clean) for pat in greeting_patterns):
        return "Hello! I am Vihil InfoTech's AI assistant. I have been trained on our official company context. How can I help you today?"
        
    # 2. Identity & Name
    if any(re.search(pat, query_clean) for pat in identity_patterns):
        return "I am Vihil InfoTech's official AI assistant. I am programmed to help you explore our services, technical stacks, development process, team profiles, and office locations!"

    # 3. How are you
    if any(re.search(pat, query_clean) for pat in how_are_you_patterns):
        return "I'm doing fantastic, thank you for asking! I'm completely ready to help you explore Vihil InfoTech's engineering offerings. What can I assist you with today?"

    # 4. Capabilities / What can you do
    if any(re.search(pat, query_clean) for pat in capabilities_patterns):
        return (
            "I am Vihil InfoTech's AI assistant. Here's what I can help you with:\n"
            "- **Services**: Web Dev (React/Next.js), Mobile Apps (React Native/iOS/Android), AI/ML Integration, Cloud & Infrastructure, Cyber Security, SEO, PWA, Desktop Apps.\n"
            "- **Development Process**: Research → Plan → Implement → Test & Deliver → Optimize.\n"
            "- **Team**: 20+ engineers, designers, and AI specialists.\n"
            "- **Contact**: vihil3010@gmail.com | +91 7016421339 | Reply within 24 hours.\n"
            "- **Tech Stack**: React, Next.js, Node.js, Python, FastAPI, LangChain, React Native, TypeScript, Cloud (AWS/GCP/Azure).\n\n"
            "Set a Groq API key with `/setkey <key>` to unlock full AI conversation mode!"
        )

    # 5. Thanks / Gratitude
    if any(re.search(pat, query_clean) for pat in thanks_patterns):
        return "You're very welcome! Helping you is what I do best. Let me know if there's anything else about Vihil InfoTech you want to explore!"

    # 6. Goodbye / Farewell
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
        "hetvi", "shama", "sharma", "janvi", "dhaval", "prajapati", "kinjal", "krupal", "valand", "dhruvil", "mistry", "desai",
        "કૃપાલ", "હેત્વી", "શર્મા", "મનીષ", "જાનવી", "ભરત", "ધવલ", "કિંજલ", "ધ્રુવિલ", "કૃપેલ", "વાલાંદ",
        "કોણ", "છે", "કૌન", "હૈ",
        "process", "methodology", "workflow", "step", "planning", "research", "test", "testing", "optimize",
        "faq", "faqs", "question", "questions", "answer", "quote", "cost", "price", "portfolio", "carousel",
        "android", "ios", "react", "nextjs", "python", "fastapi", "node",
        # New AI/ML terms
        "ai", "ml", "llm", "rag", "langchain", "cloud", "automation", "generative", "intelligence",
        "copilot", "assistant", "infrastructure", "devops", "shopify", "typescript",
        "linkedin", "instagram", "facebook", "social"
    }
    
    # Preprocess and expand the query to support multiple languages and synonyms
    expanded_query = preprocess_multilingual_query(query)
    
    # Tokenize the original and expanded queries to check for core keywords
    original_tokens = clean_and_tokenize(query)
    expanded_tokens = clean_and_tokenize(expanded_query)
    
    # Check if the query has at least some relevance to Vihil/Infotech or contains core business keywords
    is_relevant_topic = (
        any(w in core_business_keywords for w in expanded_tokens) 
        or "vihil" in query_clean 
        or "infotech" in query_clean 
        or "વિહિલ" in query_clean 
        or "ઇન્ફોટેક" in query_clean 
        or "વિહિલઇન્ફોટેક" in query_clean
        or "विहिल" in query_clean 
        or "इन्फोटेक" in query_clean
        or "विहिलइन्फोटेक" in query_clean
    )
    
    if not is_relevant_topic and original_tokens:
        # If the question contains no company name and no business keywords, fail early to prevent wrong answers
        return (
            "I am Vihil InfoTech's AI Assistant. I operate on a local cached knowledge base facts when the Live API is disconnected. "
            "I couldn't find a highly-relevant match for your query in our local site cache.\n\n"
            "**To resolve this and unlock smart conversation**:\n"
            "1. **Wait for Rate Limit**: If you configured Groq, you might have hit the free-tier limits. Wait a minute and try again, or use a new key!\n"
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
        "I am Vihil InfoTech's AI Assistant. I operate on a local cached knowledge base facts when the Live API is disconnected. "
        "I couldn't find a highly-relevant match for your query in our local site cache.\n\n"
        "**To resolve this and unlock smart conversation**:\n"
        "1. **Wait for Rate Limit**: If you configured Groq, you might have hit the free-tier limits. Wait a minute and try again, or use a new key!\n"
        "2. **Ask about Vihil InfoTech**: You can ask me about our core services, development process, specialized technologies, and team members, and I'll fetch the answers instantly from our local cache.\n"
        "3. **Contact us directly**: Feel free to reach out to our team at vihil3010@gmail.com or call +91 7016421339. We'd love to help you build your digital vision!"
    )

def detect_language_from_text(text):
    """
    Detects language (gu, hi, or en) from the query text.
    Checks for both Unicode ranges and common Romanized/transliterated words.
    """
    text_clean = text.lower().strip()
    
    # 1. Check Unicode character ranges first (extremely reliable)
    if re.search(r'[\u0A80-\u0AFF]', text):
        return "gu"
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
        
    # 2. Check Romanized Gujarati phrases
    romanized_gu = [
        r'\bkem\s+chho\b', r'\bkem\s+cho\b', r'\bgujarati\s+ma\b', r'\bgujrati\s+ma\b',
        r'\btame\s+kem\s+chho\b', r'\bvaat\s+karo\b', r'\bshu\s+chhe\b', r'\bshu\s+che\b',
        r'\bgujarati\s+ma\s+bolo\b', r'\bgujrati\s+ma\s+bolo\b'
    ]
    if any(re.search(pat, text_clean) for pat in romanized_gu):
        return "gu"
        
    # 3. Check Romanized Hindi phrases
    romanized_hi = [
        r'\bkaise\s+ho\b', r'\bkya\s+haal\b', r'\bhindi\s+me\b', r'\bbaat\s+karo\b',
        r'\bkaise\s+hain\b', r'\bhindi\s+me\s+bolo\b'
    ]
    if any(re.search(pat, text_clean) for pat in romanized_hi):
        return "hi"
        
    return "en"

def check_language_switch_request(query):
    """
    Checks if the user is explicitly requesting to switch the conversational language.
    Returns the target language code (e.g. 'gu', 'hi', 'en') if a match is found, else None.
    """
    q_clean = query.lower().strip()
    
    # Gujarati requests
    gujarati_patterns = [
        r'\bspeak\s+in\s+gujarati\b',
        r'\btalk\s+in\s+gujarati\b',
        r'\bgujarati\s+ma\s+bolo\b',
        r'\bgujarati\s+ma\s+vaat\b',
        r'\bgujrati\s+ma\s+bolo\b',
        r'\bgujrati\s+ma\s+vaat\b',
        r'\bgujarati\s+bolo\b',
        r'\bgujrati\s+bolo\b',
        r'ગુજરાતી\s*માં',
        r'ગુજરાતી\s*બોલો',
        r'ગુજરાતી\s*માં\s*વાત',
        r'\bkem\s+chho\b',
        r'\bkem\s+cho\b'
    ]
    
    # Hindi requests
    hindi_patterns = [
        r'\bspeak\s+in\s+hindi\b',
        r'\btalk\s+in\s+hindi\b',
        r'\bhindi\s+me\s+bolo\b',
        r'\bhindi\s+me\s+baat\b',
        r'\bhindi\s+bolo\b',
        r'हिंदी\s*में',
        r'हिंदी\s*बोलो',
        r'हिंदी\s*में\s*बात',
        r'हिन्दी\s*में',
        r'हिन्दी\s*बोलो'
    ]
    
    # English requests
    english_patterns = [
        r'\bspeak\s+in\s+english\b',
        r'\btalk\s+in\s+english\b',
        r'\benglish\s+me\s+bolo\b',
        r'\benglish\s+me\s+baat\b',
        r'\benglish\s+please\b'
    ]
    
    if any(re.search(pat, q_clean) for pat in gujarati_patterns):
        return "gu"
    if any(re.search(pat, q_clean) for pat in hindi_patterns):
        return "hi"
    if any(re.search(pat, q_clean) for pat in english_patterns):
        return "en"
        
    return None

def is_pure_language_switch(query):
    """
    Determines if the query is just a language switch trigger/command.
    """
    q_clean = query.lower().strip()
    phrases = [
        "speak in gujarati", "talk in gujarati", "gujarati ma bolo", "gujarati ma vaat karo", "gujarati bolo",
        "gujrati ma bolo", "gujrati ma vaat karo", "gujrati bolo",
        "ગુજરાતી માં વાત કરો", "ગુજરાતી માં બોલો", "ગુજરાતી બોલો",
        "speak in hindi", "talk in hindi", "hindi me baat karo", "hindi me bolo", "hindi bolo",
        "हिंदी में बात करो", "हिंदी में बोलो", "hindi bolo", "हिन्दी में बात करो", "हिन्दी में बोलो",
        "speak in english", "talk in english", "english me bolo", "english me baat karo"
    ]
    if q_clean in ["gujarati", "gujrati", "ગુજરાતી", "hindi", "हिंदी", "हिन्दी", "english"]:
        return True
    q_stripped = re.sub(r'[^\w\s\u0A80-\u0AFF\u0900-\u097F]', '', q_clean).strip()
    for phrase in phrases:
        if q_stripped == phrase:
            return True
    return False

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

def query_groq_api(query, kb, api_key, stream=False, lang_pref=None):
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
        "You are the official AI assistant for Vihil InfoTech (Vihil Infotech Private Limited), "
        "a product-focused technology company based in Nadiad, Gujarat, India.\n"
        "Your goal is to answer questions about Vihil InfoTech accurately, helpfully, and warmly using the provided website context.\n\n"
        "Key facts to always have ready:\n"
        "- Company: Vihil InfoTech | Legal: Vihil Infotech Private Limited\n"
        "- Tagline: 'Build faster with a dependable tech partner.'\n"
        "- Services: Web (React/Next.js), Mobile (React Native/iOS/Android), AI/ML (LLMs, RAG, automation), Cloud, Cyber Security, SEO, PWA, Desktop Apps\n"
        "- Tech Stack: React, Next.js, Node.js, Express.js, Python, FastAPI, LangChain, React Native, Shopify, PHP, TypeScript, Cloud (AWS/GCP/Azure)\n"
        "- Team Size: 20+ professionals | Clients: 60+ | Projects: 60+ | Rating: 4.8\n"
        "- Address: 207, Sky Tatva-1, Opposite Amba Aashram, College Road, Nadiad, Gujarat, India\n"
        "- Email: vihil3010@gmail.com | Phone: +91 7016421339\n"
        "- LinkedIn: https://www.linkedin.com/company/vihil-infotech-private-limited/\n"
        "- Instagram: https://www.instagram.com/vihilinfotech/\n"
        "- Facebook: https://www.facebook.com/vihilinfotech\n"
        "- Response time: Within 24 hours\n\n"
        "- Core Team Members & Roles:\n"
        "  * Bharat Desai: CEO & Founder (driving vision and growth)\n"
        "  * Manish V. Shah: CTO (leading technology strategy)\n"
        "  * Dhaval B. Prajapati: HR Manager, Networking & QA Manager\n"
        "  * Janvi M Shah: Sr. Frontend Developer\n"
        "  * Kinjal Patel: Jr. Frontend Developer\n"
        "  * Hetvi Sharma: Jr. Frontend Developer (NOT an actress or founder)\n"
        "  * Krupal Valand: Software Developer (NOT the founder or COO)\n"
        "  * Dhruvil Mistry: FullStack Developer\n\n"
        "Guidelines:\n"
        "- Be professional, insightful, and warm.\n"
        "- CRITICAL TEAM MEMBER RULE: Always refer to team members using their exact roles from the provided context. Specifically, Hetvi Sharma is a Junior Frontend Developer and Krupal Valand is a Software Developer. Under no circumstances should you claim they are founders, CEO, COO, or have any other roles. Hetvi Sharma is NOT an actress. If a query has spelling variations or typos of our team members' names (like 'Hetvi Shama' or 'Krupel'), match them to the corresponding team member in the context and answer about them as a Vihil InfoTech team member.\n"
        "- CRITICAL LANGUAGE RULE: You MUST reply in the exact same language the user writes in. If the user asks in English, reply in English. Do NOT default to Hindi just because the company is in India.\n"
        "- ALWAYS format responses clearly line-by-line with Markdown bullet points or numbered lists. NEVER combine multiple items into a single paragraph.\n"
        "- If the user asks for team members, services, or FAQs, YOU MUST list each one clearly with bullet points.\n"
        "- For company questions not covered by the context, politely guide them to contact vihil3010@gmail.com or call +91 7016421339.\n"
        "- For completely off-topic questions (math, general chat), answer helpfully as a smart AI and tie back to how Vihil InfoTech can help build digital solutions.\n"
    )
    
    if lang_pref and lang_pref.lower() != "auto":
        system_instruction += f"\n- VERY IMPORTANT: The user has explicitly selected the language code '{lang_pref}'. You MUST bypass the English default and respond entirely in this requested language."
        
    if not stream:
        system_instruction += (
            "\nResponse format MUST be a JSON object with two fields:\n"
            "1. 'answer': The actual text response.\n"
            "2. 'lang_code': The standard 2-letter language code (e.g. 'en', 'hi', 'gu', 'es', 'fr', 'ja', 'ru', etc.) of the generated answer."
        )
    else:
        system_instruction += "\nGenerate your response in standard Markdown format. Stream the response directly."
        
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    
    # Use RAG (Retrieval-Augmented Generation) to avoid Groq rate limits
    index = build_search_index(kb)
    expanded_query = preprocess_multilingual_query(query)
    results = compute_tfidf_score(expanded_query, index)
    
    # Inject the top 15 most relevant documents so it can list all team members/services without cutting off
    top_docs = results[:15] if results else []
    context_lines = []
    for score, doc in top_docs:
        context_lines.append(f"[{doc.get('title', 'Info')}]: {doc.get('content', '')}")
        
    context_str = "\n\n".join(context_lines)
    if not context_str.strip():
        context_str = "No specific database details matched. Rely on general Vihil InfoTech facts."
    prompt = (
        f"Current Local Time: {current_time}.\n\n"
        f"Website Context:\n{context_str}\n\n"
        f"User Question: {query}"
    )
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    body = {
        "model": "llama-3.1-8b-instant",
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
    """Query answering coordinator. Uses Groq API if key is present, else fall back to local rule engine."""
    import urllib.request
    import json
    load_dotenv_custom()
    kb = load_knowledge_base(filepath)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    
    # 1. Detect language switch requests or detect language from text
    requested_lang = check_language_switch_request(query)
    if requested_lang:
        lang_pref = requested_lang
        # If it is a pure language switch command, return immediate confirmation
        if is_pure_language_switch(query):
            if requested_lang == "gu":
                return "હા, હવે હું તમારી સાથે ગુજરાતીમાં વાત કરીશ. હું ગુજરાતીમાં બોલી શકું છું! હું તમારી શું મદદ કરી શકું?", "gu"
            elif requested_lang == "hi":
                return "हाँ, अब मैं आपसे हिंदी में बात करूँगा। मैं हिंदी में बोल सकता हूँ! मैं आपकी क्या मदद कर सकता हूँ?", "hi"
            elif requested_lang == "en":
                return "Sure, I will speak with you in English now! How can I help you today?", "en"
    elif not lang_pref or lang_pref.lower() == "auto":
        detected_lang = detect_language_from_text(query)
        if detected_lang != "en":
            lang_pref = detected_lang
            
    # 2. Try Groq API first if available
    if groq_api_key:
        try:
            req, ctx = query_groq_api(query, kb, groq_api_key, stream=False, lang_pref=lang_pref)
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
            if "429" in str(e):
                return "⚠️ **Groq API Rate Limit Reached**\nYou have sent too many requests and hit the free-tier limit for the Groq API. Please wait a moment for the rate limit to reset before trying again, or use a new Groq API key.", "en"
            print(f"Groq API Error: {e}", file=sys.stderr)
            
    ans = fallback_qa(query, kb, lang_pref=lang_pref)
    if lang_pref and lang_pref.lower() not in ["en", "auto"]:
        if not contains_indic_scripts(ans):
            ans = translate_to_target_lang(ans, lang_pref)
    return ans, detect_language_simple(ans)

def stream_answer_query(query, filepath="knowledge_base.json", lang_pref=None):
    """
    Generator that yields chunks of the answer.
    Enables highly responsive real-time streaming in the terminal and browser.
    Supports Groq or local search fallback.
    """
    import urllib.request
    import json
    load_dotenv_custom()
    kb = load_knowledge_base(filepath)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    
    # 1. Detect language switch requests or detect language from text
    requested_lang = check_language_switch_request(query)
    if requested_lang:
        lang_pref = requested_lang
        # If it is a pure language switch command, yield immediate confirmation and return
        if is_pure_language_switch(query):
            if requested_lang == "gu":
                yield "હા, હવે હું તમારી સાથે ગુજરાતીમાં વાત કરીશ. હું ગુજરાતીમાં બોલી શકું છું! હું તમારી શું મદદ કરી શકું?"
            elif requested_lang == "hi":
                yield "हाँ, अब मैं आपसे हिंदी में बात करूँगा। मैं हिंदी में बोल सकता हूँ! मैं आपकी क्या मदद कर सकता हूँ?"
            elif requested_lang == "en":
                yield "Sure, I will speak with you in English now! How can I help you today?"
            return
    elif not lang_pref or lang_pref.lower() == "auto":
        detected_lang = detect_language_from_text(query)
        if detected_lang != "en":
            lang_pref = detected_lang
            
    # 2. Try Groq API first if available
    if groq_api_key:
        try:
            req, ctx = query_groq_api(query, kb, groq_api_key, stream=True, lang_pref=lang_pref)
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
            if "429" in str(e):
                yield "⚠️ **Groq API Rate Limit Reached**\nYou have sent too many requests and hit the free-tier limit for the Groq API. Please wait a moment for the rate limit to reset before trying again, or use a new Groq API key."
                return
            print(f"Groq Stream Error: {e}", file=sys.stderr)
            
    ans = fallback_qa(query, kb, lang_pref=lang_pref)
    if lang_pref and lang_pref.lower() not in ["en", "auto"]:
        if not contains_indic_scripts(ans):
            ans = translate_to_target_lang(ans, lang_pref)
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
    found_groq = False
    env_path = ".env"
    
    key_var = "GROQ_API_KEY"
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(f"{key_var}="):
                    lines.append(f"{key_var}={key}\n")
                    found_groq = True
                else:
                    lines.append(line)
                    
    if not found_groq:
        lines.append(f"GROQ_API_KEY={key}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    os.environ[key_var] = key
    print(f"\n{Colors.GREEN}✔ API key successfully configured and saved to .env!{Colors.ENDC}")
    print(f"{Colors.GREEN}AI assistant is now upgraded to Live Groq Mode.{Colors.ENDC}\n")

def print_status(filepath="knowledge_base.json"):
    kb = load_knowledge_base(filepath)
    groq_api_key = os.environ.get("GROQ_API_KEY")
    
    if groq_api_key:
        api_status = f"{Colors.GREEN}CONNECTED (Groq Llama-3.1-8b-instant){Colors.ENDC}"
    else:
        api_status = f"{Colors.YELLOW}OFFLINE MODE (Local TF-IDF Vector Search Engine){Colors.ENDC}"
    
    services_count = len(kb.get("services", []))
    team_count = len(kb.get("team", []))
    faqs_count = len(kb.get("faqs", []))
    process_count = len([p for p in kb.get("process", []) if p.get("content")])
    techs_count = len(kb.get("technologies", []))
    ai_caps_count = len(kb.get("ai_ml", {}).get("capabilities", []))
    
    cur_time = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== SYSTEM STATUS ==={Colors.ENDC}")
    print(f"- **AI Power Status**: {api_status}")
    print(f"- **Loaded Knowledge Base**: {Colors.CYAN}{filepath}{Colors.ENDC}")
    print(f"  - Core Services: {services_count}")
    print(f"  - Team Members: {team_count}")
    print(f"  - Frequently Asked Qs: {faqs_count}")
    print(f"  - Process Steps: {process_count}")
    print(f"  - Tech Stack Items: {techs_count}")
    print(f"  - AI/ML Capabilities: {ai_caps_count}")
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
    print(f"  {Colors.BOLD}/setkey <key>{Colors.ENDC}     - Save Groq API key to .env file for Live Mode.")
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
            if groq_api_key:
                engine_label = "Groq Llama-3"
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