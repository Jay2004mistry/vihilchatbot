from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys

# Ensure current working directory is in system path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import scraper
    import qa_engine
except ImportError:
    # If working directory path issue, try relative imports
    import sys
    sys.path.insert(0, os.getcwd())
    import scraper
    import qa_engine

app = FastAPI(title="Vihil InfoTech AI Assistant")

class QueryRequest(BaseModel):
    query: str

@app.post("/api/query")
def api_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        ans = qa_engine.answer_query(request.query)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scrape")
def api_scrape():
    try:
        kb = scraper.scrape_vihil()
        if kb:
            return {"status": "success", "message": "Knowledge base successfully updated."}
        else:
            raise HTTPException(status_code=500, detail="Crawl returned empty database.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data")
def api_data():
    try:
        kb = qa_engine.load_knowledge_base("knowledge_base.json")
        return kb
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serves index.html at root
@app.get("/")
def read_index():
    index_path = os.path.join("static", "index.html")
    if not os.path.exists(index_path):
        # Create static folder and files if they do not exist
        os.makedirs("static", exist_ok=True)
    return FileResponse(index_path)

# Mount static files directory
# Create static directory if not exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Launching Vihil InfoTech AI Assistant on http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
