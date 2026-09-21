from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

import database
import seed
from detector import SafetyScanner

app = FastAPI(title="AI Safety Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

database.init_db()
scanner = SafetyScanner()

class ScanRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "employee_demo"

class LogActionRequest(BaseModel):
    log_id: int
    action: str

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

@app.post("/api/scan")
def scan_prompt(req: ScanRequest):
    result = scanner.scan(req.prompt)
    
    action = "PENDING"
    if result["status"] == "BLOCK":
        action = "TERMINATED"
    elif result["status"] == "ALLOW":
        action = "PASSED"
        
    log_id = database.insert_audit_log(
        prompt=req.prompt,
        score=result["risk_score"],
        status=result["status"],
        violations=result["violations"],
        action_taken=action,
        user_identifier=req.user_id
    )
    
    return {
        "log_id": log_id,
        "scan_result": result
    }

@app.post("/api/action")
def log_action(req: LogActionRequest):
    valid_actions = ["PASSED", "USER_BYPASS", "TERMINATED", "SANITIZED_PASSED"]
    if req.action not in valid_actions:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    database.update_action(req.log_id, req.action)
    return {"status": "success"}

@app.get("/api/analytics")
def get_analytics():
    return database.get_analytics_summary()

@app.get("/api/logs")
def get_logs(limit: int = 50, offset: int = 0):
    return database.get_paginated_logs(limit=limit, offset=offset)

@app.post("/api/seed")
def trigger_seed():
    seed.seed_database()
    return {"status": "Database seeded successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
class RuleCreate(BaseModel):
    category: str
    name: str
    pattern: str
    weight: int

@app.get("/api/rules")
def fetch_rules():
    return database.get_rules(active_only=False)

@app.post("/api/rules")
def create_rule(rule: RuleCreate):
    rule_id = database.add_rule(rule.category, rule.name, rule.pattern, rule.weight)
    return {"id": rule_id, "status": "success"}

@app.delete("/api/rules/{rule_id}")
def remove_rule(rule_id: int):
    database.delete_rule(rule_id)
    return {"status": "success"}

@app.put("/api/rules/{rule_id}/toggle")
def toggle_rule_status(rule_id: int, is_active: bool):
    database.toggle_rule(rule_id, is_active)
    return {"status": "success"}
class KeywordCreate(BaseModel):
    keyword: str

@app.get("/api/keywords")
def fetch_keywords():
    return database.get_custom_keywords()

@app.post("/api/keywords")
def create_keyword(kw: KeywordCreate):
    kw_id = database.add_custom_keyword(kw.keyword)
    if not kw_id:
        raise HTTPException(status_code=400, detail="Keyword already exists")
    return {"id": kw_id, "status": "success"}

@app.delete("/api/keywords/{kw_id}")
def remove_keyword(kw_id: int):
    database.delete_custom_keyword(kw_id)
    return {"status": "success"}
