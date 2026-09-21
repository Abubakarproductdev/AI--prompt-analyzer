console.log("Enterprise AI Guard: Enhanced Real-Time Content Script Loaded");

let extensionActive = true;
chrome.storage.local.get(['isActive'], (result) => {
    if (result.isActive === false) extensionActive = false;
});
chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.isActive) {
        extensionActive = changes.isActive.newValue;
        if (!extensionActive) hideFloatingAlert();
    }
});

const scanCache = new Map();
let bypassTexts = new Set();
let typingTimer;
let currentText = "";
let isScanning = false;

const floatingUI = document.createElement('div');
floatingUI.id = 'aig-floating';
floatingUI.className = 'aig-floating';
floatingUI.innerHTML = `
    <div class="aig-floating-icon" id="aig-icon">🛡️</div>
    <div class="aig-floating-text">
        <div class="aig-floating-title" id="aig-title">Analyzing...</div>
        <div class="aig-floating-subtitle" id="aig-subtitle">Real-time scan</div>
    </div>
`;
document.documentElement.appendChild(floatingUI);

function showFloatingAlert(status, summary) {
    floatingUI.className = `aig-floating visible ${status.toLowerCase()}`;
    
    let icon = '🛡️';
    if (status === 'WARN') icon = '⚠️';
    if (status === 'BLOCK') icon = '🛑';
    if (status === 'ALLOW') icon = '✅';
    
    document.getElementById('aig-icon').textContent = icon;
    document.getElementById('aig-title').textContent = status === 'ALLOW' ? 'Safe Query' : 'Risk Detected';
    document.getElementById('aig-subtitle').textContent = summary;
    
    if (status === 'ALLOW') {
        setTimeout(() => hideFloatingAlert(), 3000);
    }
}

function hideFloatingAlert() {
    floatingUI.className = 'aig-floating';
}

function setNativeValue(element, value) {
    const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
    if (element.tagName === 'TEXTAREA' && valueSetter) {
        valueSetter.call(element, value);
        element.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
        element.innerText = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
    }
}

document.addEventListener('input', (e) => {
    if (!extensionActive) return;
    
    const target = e.target;
    if (target.tagName === 'TEXTAREA' || target.isContentEditable) {
        const text = target.tagName === 'TEXTAREA' ? target.value : target.innerText;
        currentText = text.trim();
        
        clearTimeout(typingTimer);
        
        if (currentText.length === 0) {
            hideFloatingAlert();
            return;
        }
        
        if (bypassTexts.has(currentText)) {
            hideFloatingAlert();
            return;
        }

        if (!scanCache.has(currentText)) {
            document.getElementById('aig-icon').textContent = '⏳';
            document.getElementById('aig-title').textContent = 'Analyzing...';
            document.getElementById('aig-subtitle').textContent = 'Checking policy';
            floatingUI.className = 'aig-floating visible';
        }

        typingTimer = setTimeout(() => {
            performScan(currentText);
        }, 600);
    }
}, { capture: true });

async function performScan(textToScan) {
    if (!textToScan || scanCache.has(textToScan)) {
        const cached = scanCache.get(textToScan);
        if (cached && currentText === textToScan) showFloatingAlert(cached.status, cached.summary);
        return cached;
    }
    
    isScanning = true;
    try {
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'scanPrompt', prompt: textToScan }, (res) => resolve(res));
        });
        
        isScanning = false;
        if (response && response.scan_result) {
            scanCache.set(textToScan, response.scan_result);
            if (currentText === textToScan) { 
                showFloatingAlert(response.scan_result.status, response.scan_result.summary);
            }
            return response.scan_result;
        }
    } catch (e) {
        isScanning = false;
        console.error(e);
    }
    return null;
}

document.addEventListener('keydown', async (e) => {
    if (!extensionActive) return;
    if (e.key === 'Enter' && !e.shiftKey) {
        const target = e.target;
        if (target.tagName === 'TEXTAREA' || target.isContentEditable) {
            const text = target.tagName === 'TEXTAREA' ? target.value : target.innerText;
            if (text.trim().length > 0) {
                if (bypassTexts.has(text.trim())) return; 
                
                const cached = scanCache.get(text.trim());
                if (cached && cached.status === 'ALLOW') return; 
                
                if (cached && (cached.status === 'WARN' || cached.status === 'BLOCK')) {
                    e.preventDefault();
                    e.stopPropagation();
                    showModal(cached, target, text.trim());
                    return;
                }
                
                e.preventDefault();
                e.stopPropagation();
                document.getElementById('aig-title').textContent = 'Finalizing scan...';
                
                const result = await performScan(text.trim());
                if (!result || result.status === 'ALLOW') {
                    bypassTexts.add(text.trim());
                    showFloatingAlert('ALLOW', 'Ready to send safely. Press Enter again.');
                } else {
                    showModal(result, target, text.trim());
                }
            }
        }
    }
}, { capture: true });

document.addEventListener('click', async (e) => {
    if (!extensionActive) return;
    const btn = e.target.closest('button');
    if (btn) {
        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
        const testId = (btn.getAttribute('data-testid') || '').toLowerCase();
        if (ariaLabel.includes('send') || testId.includes('send') || btn.querySelector('svg')) {
            const container = btn.closest('form') || document.body;
            const textarea = container.querySelector('textarea, [contenteditable="true"]');
            
            if (textarea) {
                const text = textarea.tagName === 'TEXTAREA' ? textarea.value : textarea.innerText;
                const trimmed = text.trim();
                if (trimmed.length > 0) {
                    if (bypassTexts.has(trimmed)) return;
                    
                    const cached = scanCache.get(trimmed);
                    if (cached && cached.status === 'ALLOW') return; 
                    
                    if (cached && (cached.status === 'WARN' || cached.status === 'BLOCK')) {
                        e.preventDefault();
                        e.stopPropagation();
                        showModal(cached, textarea, trimmed);
                        return;
                    }
                    
                    e.preventDefault();
                    e.stopPropagation();
                    const result = await performScan(trimmed);
                    if (!result || result.status === 'ALLOW') {
                        bypassTexts.add(trimmed);
                        showFloatingAlert('ALLOW', 'Ready to send safely. Click Send again.');
                    } else {
                        showModal(result, textarea, trimmed);
                    }
                }
            }
        }
    }
}, { capture: true });

function showModal(scanResult, inputElement, originalText) {
    const overlay = document.createElement('div');
    overlay.className = 'ai-guard-overlay';
    
    let violationsHtml = scanResult.violations.map(v => 
        `<div class="ai-guard-violation">
            <span class="ai-guard-category">${v.category}:</span> 
            <span class="ai-guard-text">${v.matched_text}</span>
        </div>`
    ).join('');

    const isBlock = scanResult.status === 'BLOCK';
    const titleClass = isBlock ? 'block' : 'warn';
    const titleText = isBlock ? '🛑 Blocked by Security Policy' : '⚠️ Security Warning';
    
    let buttonsHtml = '';
    if (isBlock) {
        buttonsHtml = `<button class="ai-guard-btn ai-guard-btn-secondary" id="aig-close">Dismiss</button>`;
    } else {
        buttonsHtml = `
            <button class="ai-guard-btn ai-guard-btn-secondary" id="aig-close">Cancel</button>
            <button class="ai-guard-btn ai-guard-btn-primary" id="aig-sanitize">Sanitize Text</button>
            <button class="ai-guard-btn ai-guard-btn-warning" id="aig-override">Ignore & Approve</button>
        `;
    }

    overlay.innerHTML = `
        <div class="ai-guard-modal">
            <div class="ai-guard-title ${titleClass}">${titleText}</div>
            <p style="margin-bottom: 12px;">${scanResult.summary}</p>
            <div class="ai-guard-details">
                ${violationsHtml}
            </div>
            <p style="font-size:12px; color:#94a3b8; margin-bottom: 12px;">
                ${isBlock ? 'This prompt cannot be sent.' : 'Please resolve before sending.'}
            </p>
            <div class="ai-guard-buttons">
                ${buttonsHtml}
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('aig-close')?.addEventListener('click', () => {
        overlay.remove();
    });

    document.getElementById('aig-sanitize')?.addEventListener('click', () => {
        overlay.remove();
        setNativeValue(inputElement, scanResult.sanitized_prompt);
        bypassTexts.add(scanResult.sanitized_prompt.trim());
        showFloatingAlert('ALLOW', 'Text sanitized! You can now send safely.');
    });

    document.getElementById('aig-override')?.addEventListener('click', () => {
        overlay.remove();
        bypassTexts.add(originalText);
        showFloatingAlert('ALLOW', 'Warning bypassed. You can now send.');
    });
}
