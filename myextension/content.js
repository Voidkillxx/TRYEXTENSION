// Styles for Popup and Shield
const style = document.createElement('style');
style.textContent = `
    .ai-shield { 
        float: right;            
        margin-left: 8px; 
        font-size: 16px;         
        line-height: normal;
        text-decoration: none; 
        border: none;
        background: transparent;
        cursor: help;
        transition: transform 0.2s;
    }
    .ai-shield:hover { transform: scale(1.2); }
    
    #ai-danger-popup-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.6); 
        backdrop-filter: blur(8px);
        z-index: 2147483647; 
        display: flex; justify-content: center; align-items: center;
        font-family: sans-serif;
        animation: fadeIn 0.2s ease-out;
    }
    #ai-danger-box {
        background: #ffffff; padding: 30px; border-radius: 16px; width: 420px;
        text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        animation: popUp 0.3s forwards;
    }
    .ai-url-box {
        background: #f8f9fa; border: 1px solid #e9ecef; padding: 12px;
        border-radius: 8px; font-family: monospace; color: #d63384;
        font-size: 13px; word-break: break-all; margin-bottom: 25px;
    }
    .ai-buttons { display: flex; gap: 12px; justify-content: center; }
    button#ai-btn-back { background: #212529; color: white; padding: 12px 24px; border-radius: 8px; border:none; cursor: pointer; flex: 1; }
    button#ai-btn-proceed { background: white; color: #dc3545; border: 2px solid #dc3545; padding: 12px 24px; border-radius: 8px; cursor: pointer; flex: 1; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes popUp { from { transform: scale(0.9); } to { transform: scale(1); } }
`;
document.head.appendChild(style);

function hasPasswordField() {
    return document.querySelector('input[type="password"]') !== null;
}

// Scanner Loop
setInterval(() => {
    if (document.hidden) return; 

    const links = document.querySelectorAll('a:not([data-ai-checked])');
    
    links.forEach((link, index) => {
        if (link.querySelector('img, svg')) return; 
        
        const text = link.innerText.trim();
        
        // Check for URL-like text or Shorteners
        const isLikelyUrl = /^(https?:\/\/|www\.|[a-z0-9-]+\.[a-z]{2,}\/)/i.test(text);

        if (!isLikelyUrl) {
            link.setAttribute('data-ai-checked', 'skipped'); 
            return; 
        }

        const url = link.href;
        const uniqueId = "ai-link-" + Date.now() + "-" + index;
        link.setAttribute('data-ai-checked', uniqueId);
        
        chrome.runtime.sendMessage({ 
            type: "CHECK_LINK_SILENT", 
            url: url, 
            elementId: uniqueId 
        });
    });
}, 800); 

// Handle Server Result
chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "INSERT_SHIELD" && message.status !== "SKIPPED") {
        const linkElement = document.querySelector(`[data-ai-checked="${message.elementId}"]`);
        
        if (linkElement && !linkElement.querySelector('.ai-shield')) {
            linkElement.dataset.aiStatus = message.status;
            const shield = document.createElement('span');
            shield.className = 'ai-shield';
            
            // UI Icons for Safe/Danger
            shield.innerText = message.status === "SAFE" ? "✅" : "⚠️";
            shield.title = message.status === "SAFE" ? "Verified Safe" : "Warning: Hidden Threat Detected";
            linkElement.appendChild(shield);
        }
    }
});

// Popup Logic
document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link && link.dataset.aiStatus === "DANGER") {
        e.preventDefault(); 
        e.stopPropagation();
        
        const isCritical = hasPasswordField(); 
        const warningTitle = isCritical ? "CRITICAL PHISHING ALERT" : "Suspicious Site Detected";
        const warningColor = isCritical ? "#ff0000" : "#d32f2f";

        // Popup HTML Structure
        const popupHTML = `
            <div id="ai-danger-popup-overlay">
                <div id="ai-danger-box" style="border: 2px solid ${warningColor}">
                    <div style="font-size: 50px; margin-bottom: 15px;">🛡️</div>
                    <h2 style="color: ${warningColor}; margin: 0 0 10px 0;">${warningTitle}</h2>
                    <p style="color:#555;">The AI flagged this link.</p>
                    ${isCritical ? '<p style="font-weight:bold; color:red;">⚠️ WARNING: Password fields detected!</p>' : ''}
                    
                    <div class="ai-url-box">${link.href}</div>
                    
                    <div class="ai-buttons">
                        <button id="ai-btn-back">Go Back</button>
                        <button id="ai-btn-report" style="background:#555; color:white; border:none; padding:12px; border-radius:8px; cursor:pointer;">Report Safe</button>
                        <button id="ai-btn-proceed">Proceed</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', popupHTML);

        document.getElementById('ai-btn-report').onclick = () => {
            fetch('http://127.0.0.1:8000/report_safe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: link.href })
            });
            alert("Thanks! Site marked as safe.");
            document.getElementById('ai-danger-popup-overlay').remove();
            window.location.reload();
        };

        document.getElementById('ai-btn-back').onclick = () => document.getElementById('ai-danger-popup-overlay').remove();
        document.getElementById('ai-btn-proceed').onclick = () => {
            document.getElementById('ai-danger-popup-overlay').remove();
            window.location.href = link.href; 
        };
    }
}, true);