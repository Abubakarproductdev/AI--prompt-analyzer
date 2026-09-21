import re
from database import get_rules, get_custom_keywords
from presidio_analyzer import AnalyzerEngine

class SafetyScanner:
    def __init__(self):
        try:
            self.analyzer = AnalyzerEngine()
        except Exception as e:
            print(f"Warning: Failed to initialize Presidio analyzer: {e}")
            self.analyzer = None

    def _get_dynamic_patterns(self):
        active_rules = get_rules(active_only=True)
        credentials_patterns = {}
        pii_patterns = {}
        injection_patterns = {}
        
        for rule in active_rules:
            cat = rule['category']
            name = rule['name']
            try:
                pattern = re.compile(rule['pattern'])
                if cat == "Credentials & Secrets":
                    credentials_patterns[name] = {"pattern": pattern, "weight": rule['weight']}
                elif cat == "PII & Internal Data":
                    pii_patterns[name] = {"pattern": pattern, "weight": rule['weight']}
                elif cat == "Prompt Injection":
                    injection_patterns[name] = {"pattern": pattern, "weight": rule['weight']}
            except re.error:
                print(f"Warning: Invalid regex in rule '{name}'")
                
        return credentials_patterns, pii_patterns, injection_patterns

    def sanitize_prompt(self, text, matches):
        sanitized = text
        for match in sorted(matches, key=lambda x: len(x['matched_text']), reverse=True):
            cat = match["category"]
            group = match.get("group", "")
            matched_text = match["matched_text"]
            
            if cat == "Email Addresses" or cat == "EMAIL_ADDRESS":
                redacted = "[REDACTED_EMAIL]"
            elif "Credentials" in group or cat == "CRYPTO":
                redacted = "[REDACTED_SECRET]"
            elif cat == "Credit Cards" or cat == "CREDIT_CARD":
                redacted = "[REDACTED_CREDIT_CARD]"
            elif cat == "Social Security Numbers" or cat == "US_SSN":
                redacted = "[REDACTED_SSN]"
            elif cat == "Phone Numbers" or cat == "PHONE_NUMBER":
                redacted = "[REDACTED_PHONE]"
            elif "PII" in group or cat in ["PERSON", "LOCATION", "NRP", "ORGANIZATION"]:
                redacted = "[REDACTED_PII]"
            elif "Injection" in group:
                redacted = "[REDACTED_INJECTION]"
            else:
                redacted = f"[REDACTED]"
            
            sanitized = sanitized.replace(matched_text, redacted)
        return sanitized

    def scan(self, prompt: str):
        total_score = 0
        violations = []
        
        credentials_patterns, pii_patterns, injection_patterns = self._get_dynamic_patterns()
        
        def check_patterns(patterns, category_group):
            nonlocal total_score
            for category_name, rule_data in patterns.items():
                pattern = rule_data["pattern"]
                weight = rule_data["weight"]
                for match in pattern.finditer(prompt):
                    matched_text = match.group(0)
                    violations.append({
                        "category": category_name,
                        "group": category_group,
                        "entity": category_name,
                        "weight": weight,
                        "matched_text": matched_text
                    })
                    total_score += weight
        
        check_patterns(credentials_patterns, "Credentials & Secrets")
        check_patterns(pii_patterns, "PII & Internal Data")
        check_patterns(injection_patterns, "Prompt Injection")

        # Custom Keyword Proximity Scanner
        custom_keywords = get_custom_keywords()
        if custom_keywords:
            keywords_escaped = [re.escape(k["keyword"]) for k in custom_keywords]
            keywords_joined = "|".join(keywords_escaped)
            # Match keyword, up to 20 chars, assignment operator, and sensitive value (8+ chars)
            proximity_pattern = re.compile(rf"(?i)\b({keywords_joined})\b.{{0,20}}?(?:[:=]|is|->)\s*(['\"]?[A-Za-z0-9_!@#$%^&*\-\\]{{8,}}['\"]?)")
            
            for match in proximity_pattern.finditer(prompt):
                matched_text = match.group(0)
                violations.append({
                    "category": "Custom Policy Leak",
                    "group": "Custom Policy Leak",
                    "entity": match.group(1),
                    "weight": 40,
                    "matched_text": matched_text
                })
                total_score += 40

        # Microsoft Presidio NLP Scanning (Semantic Context)
        if self.analyzer:
            try:
                # Catch names, locations, and more that regex misses
                results = self.analyzer.analyze(text=prompt, entities=["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD", "CRYPTO"], language='en')
                for res in results:
                    if res.score >= 0.8: # Only high confidence to avoid false positives
                        matched_text = prompt[res.start:res.end]
                        violations.append({
                            "category": res.entity_type,
                            "group": "PII & Semantic Data",
                            "entity": res.entity_type,
                            "weight": 25,
                            "matched_text": matched_text
                        })
                        total_score += 25
            except Exception as e:
                pass

        # Deduplicate violations based on exact matched text and category
        unique_violations = []
        seen_texts = set()
        for v in violations:
            key = (v["category"], v["matched_text"])
            if key not in seen_texts:
                seen_texts.add(key)
                unique_violations.append(v)
            else:
                total_score -= v["weight"] 
        
        final_score = min(total_score, 100)
        
        if final_score <= 24:
            status = "ALLOW"
            summary = "Safe to pass to AI"
        elif final_score <= 49:
            status = "WARN"
            summary = "Warning: PII or sensitive corporate data identified"
        else:
            status = "BLOCK"
            summary = "Critical danger: Injections, leaked keys, or severe breaches"

        sanitized = self.sanitize_prompt(prompt, unique_violations)

        return {
            "risk_score": final_score,
            "status": status,
            "summary": summary,
            "violations": unique_violations,
            "sanitized_prompt": sanitized
        }
