import sqlite3

conn = sqlite3.connect('safety_audit.db')
cursor = conn.cursor()

keywords = ["api", "password", "secret", "key", "token", "credential"]
for kw in keywords:
    try:
        cursor.execute("INSERT INTO custom_keywords (keyword) VALUES (?)", (kw,))
    except sqlite3.IntegrityError:
        pass

# Also update the strict default API Keys rule to be more conversational just in case
new_api_pattern = r"(?i)(?:api[_-]?key|secret|token|auth).{0,30}[:=]?\s*[\'\"\[]?([a-zA-Z0-9_\-]{16,})"
cursor.execute("UPDATE rules SET pattern = ? WHERE name = ?", (new_api_pattern, 'Generic API Keys'))

conn.commit()
print("Keywords added and rules updated!")
