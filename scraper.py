import urllib.request
import re
import json
import urllib.parse
import ssl
import sys

# Disable SSL verification for safety against self-signed or legacy cert issues
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=10):
    """Fetch URL contents with basic headers and SSL bypass."""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def extract_balanced_chunk(text, start_char, end_char, start_pos):
    """Find a balanced block of start_char and end_char in text starting at start_pos."""
    count = 0
    end_pos = -1
    for i in range(start_pos, len(text)):
        char = text[i]
        if char == start_char:
            count += 1
        elif char == end_char:
            count -= 1
            if count == 0:
                end_pos = i
                break
    if end_pos != -1:
        return text[start_pos : end_pos + 1]
    return None

def extract_variable_array(var_name, text, start_pos=0):
    """Find assignment of var_name to an array and extract it, handling JavaScript syntax details."""
    pattern = r'\b' + re.escape(var_name) + r'\s*[=:]\s*(?:\[|\()'
    if var_name.startswith('$'):
        pattern = re.escape(var_name) + r'\s*[=:]\s*(?:\[|\()'
        
    match = re.search(pattern, text[start_pos:])
    if not match:
        return None
        
    pos = start_pos + match.end() - 1  # Index of [ or (
    
    if text[pos] == '[':
        return extract_balanced_chunk(text, '[', ']', pos)
    elif text[pos] == '(':
        paren_chunk = extract_balanced_chunk(text, '(', ')', pos)
        if paren_chunk:
            bracket_match = list(re.finditer(r'\[', paren_chunk))
            if bracket_match:
                start_bracket = bracket_match[-1].start()
                return extract_balanced_chunk(paren_chunk, '[', ']', start_bracket)
    return None

def parse_js_array_to_dicts(js_str):
    """Parse a JavaScript object array into Python dictionaries by extracting fields using regular expressions."""
    if not js_str:
        return []
        
    items = []
    # Find all object boundaries { ... }
    brace_matches = list(re.finditer(r'\{', js_str))
    for m in brace_matches:
        block = extract_balanced_chunk(js_str, '{', '}', m.start())
        if block:
            item = {}
            # Extract common string properties
            keys = [
                'name', 'position', 'desc', 'desc1', 'title', 'post', 'copy', 
                'question', 'answer', 'area', 'description', 'content', 'dis'
            ]
            for key in keys:
                # Matches key:"value" or key:'value'
                m_val = re.search(r'\b' + key + r'\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', block)
                if m_val:
                    item[key] = m_val.group(1).encode().decode('unicode_escape', errors='ignore')
                else:
                    m_val_s = re.search(r'\b' + key + r'\s*:\s*\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', block)
                    if m_val_s:
                        item[key] = m_val_s.group(1).encode().decode('unicode_escape', errors='ignore')
            
            # Extract numerical ID
            m_id = re.search(r'\bid\s*:\s*([0-9]+)', block)
            if m_id:
                item['id'] = int(m_id.group(1))
                
            # If we extracted any relevant field, append it
            if item:
                items.append(item)
    return items

def scrape_vihil():
    print("Starting crawl of https://www.vihilinfotech.com/...")
    homepage_html = fetch_url("https://www.vihilinfotech.com/")
    if not homepage_html:
        print("Failed to fetch home page. Cannot proceed.")
        return None
        
    # Search for React main js bundle
    js_match = re.search(r'/static/js/main\.[a-f0-9]+\.js', homepage_html)
    if not js_match:
        print("Could not find the React JavaScript bundle URL on the home page.")
        return None
        
    bundle_url = "https://www.vihilinfotech.com" + js_match.group(0)
    print(f"Found React JS bundle: {bundle_url}")
    
    js_bundle = fetch_url(bundle_url)
    if not js_bundle:
        print("Failed to download JavaScript bundle.")
        return None
        
    print("Successfully downloaded JavaScript bundle. Extracting metadata...")
    
    # Anchor to Bharat Desai to find the correct data definitions
    anchor_idx = js_bundle.find("Bharat Desai")
    if anchor_idx == -1:
        print("Warning: Anchor 'Bharat Desai' not found in JS bundle. Parsing globally...")
        search_area = js_bundle
        anchor_idx = 0
    else:
        search_area = js_bundle[anchor_idx:]
        
    # 1. Team Array: Find the array containing Bharat Desai
    team_list = []
    team_start = js_bundle.rfind('[', 0, anchor_idx)
    if team_start != -1:
        team_js = extract_balanced_chunk(js_bundle, '[', ']', team_start)
        team_list = parse_js_array_to_dicts(team_js)
        print(f"Extracted {len(team_list)} team members.")
        
    # 2. Services Array (Qo)
    services_js = extract_variable_array("Qo", js_bundle)
    services_list = parse_js_array_to_dicts(services_js)
    # Clean up bracket placeholders in services list
    for s in services_list:
        for k in s:
            if isinstance(s[k], str):
                s[k] = s[k].replace("[Vihil infotech]", "Vihil InfoTech")
    print(f"Extracted {len(services_list)} core services.")
    
    # 3. FAQs Array (GS)
    faqs_js = extract_variable_array("GS", js_bundle)
    faqs_list = parse_js_array_to_dicts(faqs_js)
    for f in faqs_list:
        for k in f:
            if isinstance(f[k], str):
                f[k] = f[k].replace("[Vihil infotech]", "Vihil InfoTech")
    print(f"Extracted {len(faqs_list)} FAQs.")
    
    # 4. What we do Array (ls)
    what_we_do_js = extract_variable_array("ls", js_bundle)
    what_we_do_list = parse_js_array_to_dicts(what_we_do_js)
    print(f"Extracted {len(what_we_do_list)} 'What We Do' capabilities.")
    
    # 5. Process Steps Array (os)
    process_js = extract_variable_array("os", search_area)
    process_list = parse_js_array_to_dicts(process_js)
    print(f"Extracted {len(process_list)} development process steps.")
    
    # 6. Carousel Slider (ss)
    carousel_js = extract_variable_array("ss", search_area)
    carousel_list = parse_js_array_to_dicts(carousel_js)
    print(f"Extracted {len(carousel_list)} carousel slider items.")
    
    # 7. Tech category arrays
    tech_categories = {
        "mobile": parse_js_array_to_dicts(extract_variable_array("$o", search_area)),
        "web_frontend": parse_js_array_to_dicts(extract_variable_array("es", search_area)),
        "fullstack": parse_js_array_to_dicts(extract_variable_array("ts", search_area)),
        "backend": parse_js_array_to_dicts(extract_variable_array("ns", search_area)),
        "cross_platform": parse_js_array_to_dicts(extract_variable_array("rs", search_area)),
        "frontend_frameworks": parse_js_array_to_dicts(extract_variable_array("is", search_area))
    }
    
    # Aggregate technologies lists
    all_techs = set()
    for cat, items in tech_categories.items():
        for item in items:
            if 'desc' in item:
                all_techs.add(item['desc'])
    print(f"Extracted {len(all_techs)} technologies used: {list(all_techs)}")
    
    # 8. Company Statistics (Vy)
    stats = [
        {"name": "60", "content": "Happy Clients"},
        {"name": "60", "content": "Completed Projects"},
        {"name": "20+", "content": "Experienced Staff"},
        {"name": "4.8", "content": "Ratings"}
    ]
    
    # 9. Vision statement (_y)
    vision_description = "At Vihil InfoTech, we believe in a systematic approach for any project be it complex or simple. We are a group of individuals with a various set of skill set varies from Digital Marketing to IoT/Robotics solutions. We have our dedicated team for your project which uses various methods such as agile Scrum & agile Kanban. We ensure top-notch quality, on-time delivery, and agility for your project."
    vision_statement = {
        "area": "Vision of our Company",
        "description": vision_description
    }
    
    # 10. Contact Info & Socials
    contact_info = {
        "address": "207, Sky Tatva-1, Opp. Amba Ashram, College road, Nadiad, Gujarat, India. (PIN: 387001)",
        "email": "vihil3010@gmail.com",
        "phone": "+91 7016421339",
        "social_links": {
            "facebook": "https://www.facebook.com/profile.php?id=100090324282115&mibextid=ViGcVu",
            "instagram": "https://www.instagram.com/vihilinfotech/",
            "twitter": "https://twitter.com/VihilInfoTech",
            "linkedin": "https://in.linkedin.com/in/vihil-infotech-5a78b5266"
        }
    }
    
    # 11. Backend API Queries (Live API crawl attempt with timeout handling)
    print("Attempting to query backend REST APIs for potential updates...")
    api_base = "http://143.244.141.111:3000/forntadmin/v1/"
    
    try:
        # Check visionData
        vision_url = api_base + "common?page=1&limit=50&placeOfContent=vision"
        html_vision = fetch_url(vision_url, timeout=4)
        if html_vision:
            api_vis = json.loads(html_vision)
            if 'data' in api_vis and len(api_vis['data']) > 0:
                vision_statement = api_vis['data'][0]
                print("Successfully updated Vision statement from Live API.")
    except Exception as e:
        print(f"API Vision fetch skipped: {e}")
        
    try:
        # Check statisticsData
        stats_url = api_base + "common?page=1&limit=50&placeOfContent=statistics"
        html_stats = fetch_url(stats_url, timeout=4)
        if html_stats:
            api_stats = json.loads(html_stats)
            if 'data' in api_stats and len(api_stats['data']) > 0:
                stats = api_stats['data']
                print("Successfully updated Statistics from Live API.")
    except Exception as e:
        print(f"API Statistics fetch skipped: {e}")

    try:
        # Check FAQs
        faq_url = api_base + "faq"
        html_faq = fetch_url(faq_url, timeout=4)
        if html_faq:
            api_faq = json.loads(html_faq)
            if 'data' in api_faq and len(api_faq['data']) > 0:
                faqs_list = api_faq['data']
                print("Successfully updated FAQs from Live API.")
    except Exception as e:
        print(f"API FAQ fetch skipped: {e}")

    # Compile Knowledge Base
    kb = {
        "metadata": {
            "source": "https://www.vihilinfotech.com/",
            "crawled_at": "urlopen"
        },
        "company": {
            "name": "Vihil InfoTech",
            "tagline": "Cutting Edge Technology & Cross Device Compatibility",
            "vision": vision_statement,
            "statistics": stats,
            "contact": contact_info
        },
        "services": services_list,
        "what_we_do": what_we_do_list,
        "team": team_list,
        "technologies": sorted(list(all_techs)),
        "tech_categories": tech_categories,
        "process": process_list,
        "faqs": faqs_list,
        "carousel": carousel_list
    }
    
    # Save to file
    with open("knowledge_base.json", "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=4, ensure_ascii=False)
    print("Knowledge base successfully built and saved to knowledge_base.json.")
    return kb

if __name__ == "__main__":
    scrape_vihil()
