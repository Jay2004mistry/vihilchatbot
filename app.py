from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import os
import sys

# Ensure current working directory is in system path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import qa_engine
except ImportError:
    # If working directory path issue, try relative imports
    import sys
    sys.path.insert(0, os.getcwd())
    import qa_engine

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app = FastAPI(title="Vihil InfoTech AI Assistant")

_cached_voices = None

class QueryRequest(BaseModel):
    query: str
    lang: str = None
    voice_response: bool = False

@app.post("/api/query")
def api_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        ans, lang_code = qa_engine.answer_query(request.query, lang_pref=request.lang)
        
        # Generate base64 audio using edge-tts
        audio_b64 = None
        if request.voice_response:
            try:
                import asyncio
                import edge_tts
                import base64
                
                clean_text = ans.replace("*", "").replace("#", "").replace("_", "")
                
                async def get_voice_for_lang(lang):
                    global _cached_voices
                    if not _cached_voices:
                        try:
                            _cached_voices = await edge_tts.list_voices()
                        except Exception as err:
                            print("Error listing edge-tts voices:", err)
                            return "en-US-AriaNeural"
                    
                    lang_prefix = lang.lower().split("-")[0]
                    # 1. Try to find female voice matching the language prefix
                    for v in _cached_voices:
                        short_name = v["ShortName"].lower()
                        if short_name.startswith(f"{lang_prefix}-") and v.get("Gender") == "Female":
                            return v["ShortName"]
                    # 2. Try to find any voice matching the language prefix
                    for v in _cached_voices:
                        short_name = v["ShortName"].lower()
                        if short_name.startswith(f"{lang_prefix}-"):
                            return v["ShortName"]
                    return "en-US-AriaNeural"
                
                async def get_audio(text, lang):
                    voice_name = await get_voice_for_lang(lang)
                    comm = edge_tts.Communicate(text, voice=voice_name, rate="+15%")
                    audio_data = b""
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            audio_data += chunk["data"]
                    return base64.b64encode(audio_data).decode("utf-8")
                    
                audio_b64 = asyncio.run(get_audio(clean_text, lang_code))
            except Exception as e:
                print("TTS Error:", e)

        return {"answer": ans, "audio": audio_b64, "lang": lang_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/data")
def api_data():
    try:
        kb = qa_engine.load_knowledge_base("knowledge_base.json")
        return kb
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_index():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=500, detail="static/index.html is missing.")
    return FileResponse(INDEX_FILE)

STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")



if __name__ == "__main__":
    import uvicorn
    print("Launching Vihil InfoTech AI Assistant on http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
