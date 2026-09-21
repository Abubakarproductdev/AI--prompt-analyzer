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
            label.textContent = 'Active Engine';
            label.style.color = '#fff';
        } else {
            label.textContent = 'Engine Paused';
            label.style.color = '#666';
        }
    }

    document.getElementById('manage-rules-btn').addEventListener('click', () => {
        chrome.runtime.openOptionsPage();
    });
});
