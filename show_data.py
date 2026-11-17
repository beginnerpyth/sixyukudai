import sqlite3

conn = sqlite3.connect("repos.db")
cur = conn.execute(
    "SELECT name, language, stars FROM repositories ORDER BY stars DESC"
)
for name, language, stars in cur:
    print(f"{name:40} {str(language):15} {stars}")

print("Total:", conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0])
conn.close()