// --- CONFIGURATION ---
const API_URL = "http://127.0.0.1:5000"; 

// [Keep your existing styles here...]
const style = document.createElement('style');
style.textContent = `
    .ai-shield { display: inline-block; margin-left: 4px; font-size: 14px; cursor: help; vertical-align: middle; z-index: 10; }
    .ai-shield:hover { transform: scale(1.2); }
    #ai-danger-popup-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(5px); z-index: 2147483647; display: flex; justify-content: center; align-items: center; font-family: -apple-system, sans-serif; animation: fadeIn 0.2s ease-out; }
    #ai-danger-box { background: #ffffff; padding: 30px; border-radius: 12px; width: 400px; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.4); animation: popUp 0.3s forwards; }
    .ai-url-box { background: #f1f3f5; border: 1px solid #dee2e6; padding: 10px; border-radius: 6px; font-family: monospace; color: #d63384; font-size: 12px; word-break: break-all; margin: 15px 0; }
    .ai-buttons { display: flex; gap: 10px; justify-content: center; margin-top: 20px; }
    button { cursor: pointer; border: none; font-weight: 600; font-size: 14px; transition: 0.2s; }
    button#ai-btn-back { background: #212529; color: white; padding: 10px 20px; border-radius: 6px; flex: 1; }
    button#ai-btn-report { background: #e9ecef; color: #495057; padding: 10px 20px; border-radius: 6px; flex: 1; }
    button#ai-btn-proceed { background: white; color: #fa5252; border: 2px solid #fa5252; padding: 10px 20px; border-radius: 6px; flex: 1; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes popUp { from { transform: scale(0.9); } to { transform: scale(1); } }
`;
document.head.appendChild(style);

function hasPasswordField() { return document.querySelector('input[type="password"]') !== null; }

function scanLinks() {
    if (document.hidden) return;

    const links = document.querySelectorAll('a:not([data-ai-checked])');
    
    links.forEach((link, index) => {
        if (link.querySelector('img, svg, i')) {
             link.setAttribute('data-ai-checked', 'skipped');
             return;
        }

        const text = link.innerText.trim();

        // 1. Standard URLs
        const isStandardUrl = /(https?:\/\/|www\.|[a-zA-Z0-9-]+\.(com|net|org|ph|gov|edu|io|site|xyz|info))/i.test(text);

        // 2. Shorteners (Expanded List)
        const isShortUrl = /(bit\.ly|goo\.gl|tinyurl\.com|ow\.ly|is\.gd|buff\.ly|t\.co|tr\.im|mcaf\.ee|rb\.gy|fb\.me|youtu\.be)/i.test(text);

        if (!isStandardUrl && !isShortUrl) {
             link.setAttribute('data-ai-checked', 'skipped');
             return;
        }
        
        if (!link.href || link.href.startsWith('javascript') || link.href.includes('#')) {
             link.setAttribute('data-ai-checked', 'skipped');
             return;
        }

        const uniqueId = "ai-link-" + Date.now() + "-" + index;
        link.setAttribute('data-ai-checked', uniqueId);
        
        chrome.runtime.sendMessage({ 
            type: "CHECK_LINK_SILENT", 
            url: link.href, 
            elementId: uniqueId 
        });
    });
}

// Smart Debouncer
let scanTimeout = null;
const observer = new MutationObserver(() => {
    if (scanTimeout) clearTimeout(scanTimeout);
    scanTimeout = setTimeout(scanLinks, 700); 
});
observer.observe(document.body, { childList: true, subtree: true });
scanLinks();

// --- POPUP LOGIC ---
chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "INSERT_SHIELD" && message.status !== "SKIPPED") {
        const linkElement = document.querySelector(`[data-ai-checked="${message.elementId}"]`);
        if (linkElement && !linkElement.querySelector('.ai-shield')) {
            linkElement.dataset.aiStatus = message.status;
            if (message.status === "DANGER" || message.status === "SAFE") { 
                const shield = document.createElement('span');
                shield.className = 'ai-shield';
                shield.innerText = message.status === "SAFE" ? "✅" : "⛔";
                shield.title = message.status === "SAFE" ? "Verified Safe" : "AI Warning: Phishing Suspected";
                linkElement.appendChild(shield);
            }
        }
    }
});

document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link && link.dataset.aiStatus === "DANGER") {
        e.preventDefault(); e.stopPropagation();
        const isCritical = hasPasswordField(); 
        const warningTitle = isCritical ? "CRITICAL PHISHING ALERT" : "Suspicious Site Detected";
        const warningColor = isCritical ? "#ff0000" : "#d32f2f";

        const popupHTML = `
            <div id="ai-danger-popup-overlay">
                <div id="ai-danger-box" style="border-top: 6px solid ${warningColor}">
                    <div style="font-size: 40px; margin-bottom: 10px;">🛡️</div>
                    <h2 style="color: ${warningColor}; margin: 0 0 5px 0;">${warningTitle}</h2>
                    <p style="color:#666; margin-top:5px; font-size:14px;">The AI flagged this link as dangerous.</p>
                    ${isCritical ? '<p style="font-weight:bold; color:red; font-size:13px;">⚠️ You are on a page with password fields!</p>' : ''}
                    <div class="ai-url-box">${link.href}</div>
                    <div class="ai-buttons">
                        <button id="ai-btn-back">Go Back</button>
                        <button id="ai-btn-report">Mark Safe</button>
                        <button id="ai-btn-proceed">Visit Anyway</button>
                    </div>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', popupHTML);
        document.getElementById('ai-btn-report').onclick = () => {
            fetch(`${API_URL}/report_safe`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ url: link.href }) })
            .then(() => { document.getElementById('ai-danger-popup-overlay').remove(); link.dataset.aiStatus = "SAFE"; alert("Thanks! Updated."); });
        };
        document.getElementById('ai-btn-back').onclick = () => { document.getElementById('ai-danger-popup-overlay').remove(); };
        document.getElementById('ai-btn-proceed').onclick = () => { document.getElementById('ai-danger-popup-overlay').remove(); window.location.href = link.href; };
    }
}, true);