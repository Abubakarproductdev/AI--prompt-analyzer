document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('guard-toggle');
    const label = document.getElementById('status-label');

    chrome.storage.local.get(['isActive'], (result) => {
        const isActive = result.isActive !== false; 
        toggle.checked = isActive;
        updateUI(isActive);
    });

    toggle.addEventListener('change', (e) => {
        const isActive = e.target.checked;
        chrome.storage.local.set({ isActive: isActive });
        updateUI(isActive);
    });

    function updateUI(isActive) {
        if (isActive) {
            label.textContent = 'Protection Active';
            label.style.color = '#10b981';
        } else {
            label.textContent = 'Protection Paused';
            label.style.color = '#ef4444';
        }
    }

    document.getElementById('manage-rules-btn').addEventListener('click', () => {
        chrome.runtime.openOptionsPage();
    });
});
