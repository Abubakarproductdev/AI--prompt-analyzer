chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'scanPrompt') {
        scanPrompt(request.prompt)
            .then(data => sendResponse(data))
            .catch(error => sendResponse({ error: error.message }));
        return true; 
    }
});

async function scanPrompt(promptText) {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: promptText,
                user_id: 'chrome_ext_user'
            })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error scanning prompt:', error);
        throw error;
    }
}
