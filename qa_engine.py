import os
import json
import re
import sys

def load_knowledge_base(filepath="knowledge_base.json"):
    """Load the crawled structured knowledge base."""
    if not os.path.exists(filepath):
        # Fallback to default structural dict if file doesn't exist yet
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading knowledge base: {e}", file=sys.stderr)
        return {}

def fallback_qa(query, kb):
    """Local fallback QA engine using rule-based keyword matching and FAQ similarity search."""
    if not kb:
        return "I am sorry, but the knowledge base is currently empty. Please trigger a crawl first."
        
    query_lower = query.lower().strip()
    
    # 1. CEO / Founder
    if any(w in query_lower for w in ["ceo", "founder", "head", "who runs", "leader", "chief executive"]):
        ceo = next((m for m in kb.get("team", []) if "ceo" in m.get("position", "").lower()), None)
        if ceo:
            return f"The CEO of Vihil InfoTech is {ceo['name']}. Under his profile, he is described as a '{ceo.get('desc', '')}'."
        return "The CEO of Vihil InfoTech is Bharat Desai."
        
    # 2. CTO
    if any(w in query_lower for w in ["cto", "technology officer"]):
        cto = next((m for m in kb.get("team", []) if "cto" in m.get("position", "").lower()), None)
        if cto:
            return f"The CTO of Vihil InfoTech is {cto['name']}. Under his profile: '{cto.get('desc', '')}'."
        return "The CTO of Vihil InfoTech is Manish Shah."
        
    # 3. Address / Location / Place
    if any(w in query_lower for w in ["address", "location", "office", "where is", "situated", "located", "place", "nadiad", "gujarat", "india"]):
        addr = kb.get("company", {}).get("contact", {}).get("address", "")
        if addr:
            return f"Vihil InfoTech is located at: {addr}."
        return "Vihil InfoTech's address is 207, Sky Tatva-1, Opp. Amba Ashram, College road, Nadiad, Gujarat, India. (PIN: 387001)."
        
    # 4. Email / Contact info
    if any(w in query_lower for w in ["email", "mail", "contact", "phone", "mobile", "number", "call", "social", "facebook", "linkedin", "instagram", "twitter"]):
        contact = kb.get("company", {}).get("contact", {})
        email = contact.get("email", "vihil3010@gmail.com")
        phone = contact.get("phone", "+91 7016421339")
        socials = contact.get("social_links", {})
        social_str = ", ".join([f"{k.capitalize()}: {v}" for k, v in socials.items()])
        return f"You can contact Vihil InfoTech via:\n- Email: {email}\n- Phone: {phone}\n- Social Media: {social_str}"
        
    # 5. Cost / Pricing / Website Development Cost
    if any(w in query_lower for w in ["cost", "price", "pricing", "budget", "charge", "rate", "fee", "how much"]):
        return "The website does not specify any exact development cost figures or pricing packages. It mentions that they provide 'in-budget and on-time solutions' and invites clients to contact them directly for a personalized project quote."
        
    # 6. Team list / Employees
    if any(w in query_lower for w in ["team", "member", "staff", "employees", "who works", "people", "developer", "manager"]):
        team = kb.get("team", [])
        if team:
            team_str = "\n".join([f"- {m['name']}: {m['position'].replace('(', '').replace(')', '').strip()}" for m in team])
            return f"Vihil InfoTech's team members include:\n{team_str}"
        return "I am sorry, but that information is not available on the Vihil InfoTech website."
        
    # 7. Services / What we do
    if any(w in query_lower for w in ["service", "what do you do", "capabilities", "core services", "offerings", "develop"]):
        services = kb.get("services", [])
        what_we_do = kb.get("what_we_do", [])
        response = "Vihil InfoTech offers the following services:\n"
        if services:
            response += "\nCore Services:\n" + "\n".join([f"- {s['title'].strip()}: {s.get('desc1', '').strip()}" for s in services])
        if what_we_do:
            response += "\n\nCapabilities & Solutions:\n" + "\n".join([f"- {w['name'].strip()}: {w.get('desc', '').strip()}" for w in what_we_do])
        if services or what_we_do:
            return response
        return "I am sorry, but that information is not available on the Vihil InfoTech website."
        
    # 8. Technologies Used
    if any(w in query_lower for w in ["technology", "tech", "stack", "languages", "tools"]):
        techs = kb.get("technologies", [])
        if techs:
            return f"Vihil InfoTech specializes in the following technologies: {', '.join(techs)}."
        return "Vihil InfoTech specializes in technologies including React, Next.js, Node.js, PHP, Python, Flutter, Ionic, Angular, Vue.js, Firebase, AWS, HTML, WordPress, Shopify, Android, and iOS."
        
    # 9. Company Stats
    if any(w in query_lower for w in ["stats", "statistics", "completed projects", "happy clients", "ratings", "staff count"]):
        stats = kb.get("company", {}).get("statistics", [])
        if stats:
            stats_str = "\n".join([f"- {s['content']}: {s['name']}" for s in stats])
            return f"Vihil InfoTech's key statistics are:\n{stats_str}"
        return "Vihil InfoTech's key statistics are: Happy Clients: 60, Completed Projects: 60, Experienced Staff: 20+, Ratings: 4.8."
        
    # 10. Vision
    if any(w in query_lower for w in ["vision", "mission", "philosophy"]):
        vision = kb.get("company", {}).get("vision", {})
        if vision:
            return f"{vision.get('area', 'Vision of our Company')}: {vision.get('description', '')}"
        return "I am sorry, but that information is not available on the Vihil InfoTech website."
        
    # 11. Process Steps / Procedure / Workflow
    if any(w in query_lower for w in ["process", "step", "stages", "methodology", "how do you work", "procedure", "workflow", "lifecycle", "development process", "how do you build", "method", "steps"]):
        process = kb.get("process", [])
        process_steps = [p for p in process if 'content' in p]
        if process_steps:
            proc_str = "\n".join([f"- Step {p.get('title', '').replace('.', '').strip()} ({p.get('content', '').strip()}): {p.get('dis', '').strip()}" for p in process_steps])
            return f"Vihil InfoTech follows a structured 5-step development process:\n{proc_str}"
        return "I am sorry, but that information is not available on the Vihil InfoTech website."
        
    # 12. FAQ Keyword Match (using Jaccard index J(A, B) = |A ∩ B| / |A ∪ B|)
    faqs = kb.get("faqs", [])
    best_faq = None
    max_overlap = 0
    
    # Tokenize and clean query
    query_words = set(re.findall(r'\w+', query_lower))
    # Remove common English stop words + Vihil InfoTech keyword bias
    stop_words = {
        "what", "is", "are", "do", "you", "how", "can", "i", "get", "a", "the", "to", 
        "for", "of", "in", "on", "about", "with", "does", "vihil", "infotech", "company"
    }
    query_words = query_words - stop_words
    
    for faq in faqs:
        faq_q = faq['question'].lower()
        faq_words = set(re.findall(r'\w+', faq_q)) - stop_words
        if not query_words or not faq_words:
            continue
        overlap = len(query_words.intersection(faq_words)) / len(query_words.union(faq_words))
        if overlap > max_overlap:
            max_overlap = overlap
            best_faq = faq
            
    if best_faq and max_overlap >= 0.2:
        return best_faq['answer']
        
    # 13. Default Fallback
    return "I am sorry, but that information is not available on the Vihil InfoTech website."

def answer_query(query, filepath="knowledge_base.json"):
    """Query answering coordinator. Uses Gemini API if key is present, else fall back to local rule engine."""
    kb = load_knowledge_base(filepath)
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("GEMINI_API_KEY not found in environment. Using local fallback engine.", file=sys.stderr)
        return fallback_qa(query, kb)
        
    # Initialize Gemini API
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # We use gemini-1.5-flash as the fast and accurate model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=(
                "You are Vihil InfoTech's AI assistant. Your sole purpose is to answer questions about Vihil InfoTech accurately and concisely using ONLY the provided website data context. "
                "Do not make up any facts, extrapolate, or mention any services, pricing, names, or contact details not explicitly written in the context. "
                "IMPORTANT: The user wants you to communicate primarily in Gujarati, English, and Hindi. You must detect the language of the user's prompt and reply in that same language. "
                "Guidelines:\n"
                "- Answer the question directly and concisely.\n"
                "- If the answer is not present in the context, reply exactly with the equivalent of: 'I am sorry, but that information is not available on the Vihil InfoTech website.' in the detected language.\n"
                "- Do not assume anything. Strict alignment is paramount."
            )
        )
        
        # Prepare context
        context_str = json.dumps(kb, indent=2, ensure_ascii=False)
        prompt = f"Website Context:\n{context_str}\n\nUser Question: {query}"
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error using Gemini API: {e}. Falling back to local engine.", file=sys.stderr)
        return fallback_qa(query, kb)

if __name__ == "__main__":
    # Test script directly
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(f"Question: {q}")
        print(f"Answer: {answer_query(q)}")
    else:
        print("Please provide a test query.")
