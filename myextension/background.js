chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "CHECK_LINK_SILENT") {
        fetch('http://127.0.0.1:8000/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: message.url })
        })
        .then(response => response.json())
        .then(data => {
            // Send the result back to the specific link on the page
            chrome.tabs.sendMessage(sender.tab.id, {
                type: "INSERT_SHIELD",
                url: message.url,
                status: data.result,
                elementId: message.elementId
            });

            // Play sound ONLY if it's a DANGER site found on the feed
            if (data.result === "DANGER") { playWarningSound(); }
        })
        .catch(err => console.error("Silent Scan Error:", err));
    }
});

async function playWarningSound() {
    if (await chrome.offscreen.hasDocument()) return;
    await chrome.offscreen.createDocument({
        url: 'alert.html', reasons: ['AUDIO_PLAYBACK'], justification: 'Threat Alert'
    });
}