// --- CONFIGURATION ---
// Connects to your Python Server (Brain)
const API_URL = "http://127.0.0.1:5000/predict"; 

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    
    // Listen for the silent check from content.js
    if (message.type === "CHECK_LINK_SILENT") {
        
        fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: message.url })
        })
        .then(res => res.json())
        .then(data => {
            // Send the result (SAFE/DANGER) back to the specific tab
            if (sender.tab && sender.tab.id) {
                chrome.tabs.sendMessage(sender.tab.id, {
                    type: "INSERT_SHIELD",
                    elementId: message.elementId,
                    status: data.result
                });
            }
        })
        .catch(err => {
            console.error("Server Error:", err);
        });

        return true; // Keep connection open
    }
});