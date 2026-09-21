import sqlite3

conn = sqlite3.connect('safety_audit.db')
cursor = conn.cursor()
new_pattern = r"(?i)(?:password|passwd|pwd|secret|key).{0,30}[:=]?\s*[\'\"\[]?([a-zA-Z0-9_\-\/\@\!\#\$\%\^]{8,})"
cursor.execute('UPDATE rules SET pattern = ? WHERE name = ?', (new_pattern, 'Database Passwords'))
conn.commit()
print("Updated Database Passwords regex successfully!")
