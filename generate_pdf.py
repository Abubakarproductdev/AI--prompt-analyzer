from fpdf import FPDF

html_content = """
<h1 align="center">Enterprise AI Guard: Complete Project Report</h1>

<h2>1. Executive Summary</h2>
<p>The <b>Enterprise AI Guard</b> is a comprehensive, zero-trust Data Leak Prevention (DLP) platform designed to protect corporate assets from being accidentally or maliciously leaked to public Generative AI platforms like ChatGPT, Claude, and Gemini.</p>
<p>Rather than relying on network-level proxies which break end-to-end encryption, this project utilizes a client-side Chrome Extension paired with a centralized FastAPI backend to analyze, sanitize, and block sensitive prompts in real-time, right inside the employee's browser.</p>

<h2>2. Technical Stack</h2>
<ul>
    <li><b>Backend:</b> Python 3.10+, FastAPI, Uvicorn</li>
    <li><b>Database:</b> Embedded SQLite (safety_audit.db) for serverless, zero-config data persistence.</li>
    <li><b>Detection Engine:</b> Native Python Regex, Microsoft Presidio Analyzer (spaCy NLP).</li>
    <li><b>Browser Extension:</b> Chrome Manifest V3, Vanilla JavaScript, CSS.</li>
    <li><b>Web Dashboard:</b> HTML5, Tailwind CSS, Chart.js for analytics.</li>
</ul>

<h2>3. Architectural Components</h2>

<h3>A. The Browser Extension (The Client Shield)</h3>
<p>The extension acts as the primary enforcement layer on the employee's machine.</p>
<ul>
    <li><b>Real-Time Interception:</b> A debounced content script (content.js) listens to keystrokes inside AI chat windows.</li>
    <li><b>Safe React Intercepts:</b> Instead of hijacking standard submit buttons, the extension gracefully intercepts the Enter key.</li>
    <li><b>CSP Bypass:</b> To bypass strict Content Security Policies on platforms like ChatGPT, the extension uses a Service Worker to securely route fetch requests to the local backend.</li>
    <li><b>Local UI:</b> Features a sleek, Vercel-inspired dark mode Popup and Options page.</li>
</ul>

<h3>B. The Detection Engine (The Brain)</h3>
<p>The Python-based SafetyScanner evaluates text through three distinct security phases:</p>
<ol>
    <li><b>Custom Proximity Matching:</b> Uses Anchor-Value logic. It searches for custom keywords defined by the CISO (e.g., "password", "api").</li>
    <li><b>Static Signature Rules:</b> Uses strict mathematical RegEx patterns to instantly identify standard secrets (AWS Keys, RSA Private Keys, Credit Cards).</li>
    <li><b>Semantic NLP (Microsoft Presidio):</b> Uses Artificial Intelligence to read the context of the sentence, identifying Personally Identifiable Information (PII).</li>
</ol>

<h3>C. The Central Backend & Database (The Command Center)</h3>
<p>The FastAPI backend serves as the central hub for the enterprise.</p>
<ul>
    <li><b>Stateless API:</b> Exposes endpoints for prompt scanning, rule management, and keyword management.</li>
    <li><b>Immutable Auditing:</b> Every scan is logged to the SQLite database.</li>
</ul>

<h3>D. The CISO Dashboard (The UI)</h3>
<p>A centralized web dashboard designed for security administrators.</p>
<ul>
    <li><b>Analytics:</b> Visualizes risk category distributions using Chart.js doughnut charts.</li>
    <li><b>Live Audit Trail:</b> A real-time table displaying every prompt intercepted.</li>
    <li><b>Global Policy Management:</b> Allows administrators to dynamically add new Custom Monitored Keywords.</li>
</ul>

<h2>4. Risk Scoring & Remediation</h2>
<p>Every violation detected by the engine is assigned a <b>Threat Weight</b>. The engine aggregates these weights to calculate a final Risk Score:</p>
<ul>
    <li><b>ALLOW (Score 0-24):</b> The prompt is safe. The extension forwards it to the AI natively.</li>
    <li><b>WARN (Score 25-39):</b> Minor PII detected. The extension halts the prompt and shows a floating warning UI, allowing the user to override.</li>
    <li><b>BLOCK (Score 40+):</b> Critical data detected (e.g., API Keys, Passwords). The extension entirely blocks the transmission.</li>
</ul>

<h2>5. Security & Privacy</h2>
<ul>
    <li><b>Zero External Dependencies:</b> Because the platform relies entirely on an embedded SQLite database and a local Python server, no corporate data is ever transmitted to a third-party cloud provider for analysis.</li>
    <li><b>Sanitization:</b> When a prompt is flagged, the backend automatically generates a sanitized version of the text (masking the sensitive data).</li>
</ul>
"""

class PDF(FPDF):
    pass

pdf = PDF()
pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.write_html(html_content)
pdf.output("project_report.pdf")
print("PDF generated successfully.")
