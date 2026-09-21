import sqlite3
import json
import threading
from datetime import datetime, timezone
import os

DB_PATH = "safety_audit.db"
db_lock = threading.Lock()

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_identifier TEXT DEFAULT 'emp_sec_anon',
                    prompt_preview TEXT,
                    full_prompt TEXT,
                    risk_score INTEGER,
                    status TEXT,
                    violations TEXT,
                    action_taken TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    weight INTEGER NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON audit_logs (status)')
            conn.commit()
    seed_default_rules()

def insert_audit_log(prompt, score, status, violations, action_taken, user_identifier="emp_sec_anon"):
    timestamp = datetime.now(timezone.utc).isoformat()
    prompt_preview = (prompt[:80] + '...') if len(prompt) > 80 else prompt
    violations_json = json.dumps(violations)
    
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_logs (
                    timestamp, user_identifier, prompt_preview, full_prompt,
                    risk_score, status, violations, action_taken
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, user_identifier, prompt_preview, prompt, score, status, violations_json, action_taken))
            conn.commit()
            return cursor.lastrowid

def update_action(log_id, action):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE audit_logs SET action_taken = ? WHERE id = ?', (action, log_id))
            conn.commit()

def get_analytics_summary():
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM audit_logs')
            total_scans = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE status = 'BLOCK'")
            blocked_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE status = 'WARN'")
            warned_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE status = 'ALLOW'")
            allowed_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(risk_score) FROM audit_logs')
            avg_score_row = cursor.fetchone()[0]
            avg_risk_score = round(avg_score_row, 1) if avg_score_row else 0.0
            
            cursor.execute('SELECT violations FROM audit_logs')
            all_violations_rows = cursor.fetchall()
            
            category_counts = {}
            for row in all_violations_rows:
                violations_json = row[0]
                if violations_json:
                    try:
                        violations = json.loads(violations_json)
                        for v in violations:
                            cat = v.get('category', 'Unknown')
                            category_counts[cat] = category_counts.get(cat, 0) + 1
                    except json.JSONDecodeError:
                        pass
            
            cursor.execute('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 20')
            recent_logs = [dict(row) for row in cursor.fetchall()]
            for log in recent_logs:
                if log['violations']:
                    log['violations'] = json.loads(log['violations'])
            
            return {
                "total_scans": total_scans,
                "blocked_count": blocked_count,
                "warned_count": warned_count,
                "allowed_count": allowed_count,
                "avg_risk_score": avg_risk_score,
                "category_counts": category_counts,
                "recent_logs": recent_logs
            }

def get_paginated_logs(limit=50, offset=0):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?', (limit, offset))
            logs = [dict(row) for row in cursor.fetchall()]
            for log in logs:
                if log['violations']:
                    log['violations'] = json.loads(log['violations'])
            
            cursor.execute('SELECT COUNT(*) FROM audit_logs')
            total = cursor.fetchone()[0]
            return {"logs": logs, "total": total}

def seed_default_rules():
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM rules")
            if cursor.fetchone()[0] == 0:
                default_rules = [
                    ("Credentials & Secrets", "AWS Access Key", r"\bAKIA[0-9A-Z]{16}\b", 40),
                    ("Credentials & Secrets", "Generic Bearer Tokens", r"(?i)bearer\s+[a-z0-9_\-\.]{20,}", 40),
                    ("Credentials & Secrets", "SSH/Private Keys", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", 40),
                    ("Credentials & Secrets", "Generic API Keys", r"(?i)(?:api[_-]?key|secret|token|auth)\s*[:=]\s*[\'\"][a-zA-Z0-9_\-]{16,}[\'\"]", 40),
                    ("Credentials & Secrets", "Database Passwords", r"(?i)(?:password|passwd|pwd)\s*[:=]\s*[\'\"][^\s\'\"]{6,}[\'\"]", 40),
                    ("PII & Internal Data", "Email Addresses", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", 25),
                    ("PII & Internal Data", "Credit Cards", r"\b(?:\d{4}[ -]?){3}\d{4}\b", 25),
                    ("PII & Internal Data", "Social Security Numbers", r"\b\d{3}-\d{2}-\d{4}\b", 25),
                    ("PII & Internal Data", "Phone Numbers", r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", 25),
                    ("PII & Internal Data", "Confidential Watermarks", r"(?i)\b(confidential|strictly private|internal use only|do not distribute|trade secret)\b", 25),
                    ("Prompt Injection", "Instruction Resets", r"(?i)(ignore\s+(all\s+)?(previous|prior)\s+instructions|disregard\s+all\s+(rules|prompts))", 45),
                    ("Prompt Injection", "Persona Hijacking", r"(?i)(you\s+are\s+now|act\s+as)\s+(an?\s+unrestricted|dan|jailbreak|chaos)", 45),
                    ("Prompt Injection", "System Leak Attacks", r"(?i)(reveal\s+your\s+system\s+prompt|repeat\s+the\s+words\s+above|output\s+initial\s+instructions)", 45),
                    ("Prompt Injection", "Delimiter / Syntax Escapes", r"(?i)(<\|im_start\|>|<\|im_end\|>|\[system\]|system:\s*$)", 45)
                ]
                cursor.executemany(
                    "INSERT INTO rules (category, name, pattern, weight) VALUES (?, ?, ?, ?)",
                    default_rules
                )
                conn.commit()

def get_rules(active_only=False):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, category, name, pattern, weight, is_active FROM rules"
            if active_only:
                query += " WHERE is_active = 1"
            cursor.execute(query)
            return [
                {
                    "id": r["id"], "category": r["category"], "name": r["name"], 
                    "pattern": r["pattern"], "weight": r["weight"], "is_active": bool(r["is_active"])
                }
                for r in cursor.fetchall()
            ]

def add_rule(category, name, pattern, weight):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO rules (category, name, pattern, weight, is_active) VALUES (?, ?, ?, ?, 1)",
                (category, name, pattern, weight)
            )
            conn.commit()
            return cursor.lastrowid
            
def delete_rule(rule_id):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            conn.commit()
            
def toggle_rule(rule_id, is_active):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE rules SET is_active = ? WHERE id = ?", (int(is_active), rule_id))
            conn.commit()

def get_custom_keywords():
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, keyword, added_at FROM custom_keywords ORDER BY added_at DESC")
            return [{"id": r["id"], "keyword": r["keyword"], "added_at": r["added_at"]} for r in cursor.fetchall()]

def add_custom_keyword(keyword: str):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO custom_keywords (keyword) VALUES (?)", (keyword,))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

def delete_custom_keyword(keyword_id: int):
    with db_lock:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_keywords WHERE id = ?", (keyword_id,))
            conn.commit()
