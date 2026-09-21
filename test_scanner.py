import sys
from detector import SafetyScanner

scanner = SafetyScanner()
res = scanner.scan("my API is sk-123456789")
print(res["status"])
print(res["violations"])
