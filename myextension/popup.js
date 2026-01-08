const API_URL = "http://127.0.0.1:5000/predict"; 

// --- DOM ELEMENTS ---
const tabScanner = document.getElementById('tab-scanner');
const tabHistory = document.getElementById('tab-history');
const viewScanner = document.getElementById('view-scanner');
const viewHistory = document.getElementById('view-history');
const btnScan = document.getElementById('btn-scan');
const inputUrl = document.getElementById('url-input');
const resultArea = document.getElementById('result-area');
const historyList = document.getElementById('history-list');

// --- TABS LOGIC ---
tabScanner.addEventListener('click', () => {
    switchTab('scanner');
});

tabHistory.addEventListener('click', () => {
    switchTab('history');
    loadHistory(); // Reload history when clicking tab
});

function switchTab(tab) {
    if (tab === 'scanner') {
        tabScanner.classList.add('active');
        tabHistory.classList.remove('active');
        viewScanner.classList.add('active');
        viewScanner.classList.remove('hidden');
        viewHistory.classList.remove('active');
        viewHistory.classList.add('hidden');
    } else {
        tabHistory.classList.add('active');
        tabScanner.classList.remove('active');
        viewHistory.classList.add('active');
        viewHistory.classList.remove('hidden');
        viewScanner.classList.remove('active');
        viewScanner.classList.add('hidden');
    }
}

// --- SCANNER LOGIC ---
btnScan.addEventListener('click', async () => {
    const url = inputUrl.value.trim();
    if (!url) return;

    // UI Loading State
    btnScan.innerText = "Scanning...";
    btnScan.disabled = true;
    resultArea.classList.add('hidden');

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await response.json();
        
        showResult(data.result);
        saveToHistory(url, data.result);

    } catch (error) {
        showResult("ERROR");
        console.error(error);
    }

    // Reset UI
    btnScan.innerText = "Scan URL";
    btnScan.disabled = false;
});

function showResult(status) {
    resultArea.classList.remove('hidden');
    const icon = document.getElementById('result-icon');
    const title = document.getElementById('result-title');
    const desc = document.getElementById('result-desc');

    if (status === "SAFE") {
        icon.innerText = "✅";
        title.innerText = "Safe Website";
        title.style.color = "#28a745";
        desc.innerText = "This URL appears legitimate.";
        resultArea.style.borderLeft = "5px solid #28a745";
    } else if (status === "DANGER") {
        icon.innerText = "⛔";
        title.innerText = "Phishing Detected";
        title.style.color = "#dc3545";
        desc.innerText = "Do not visit this link.";
        resultArea.style.borderLeft = "5px solid #dc3545";
    } else {
        icon.innerText = "⚠️";
        title.innerText = "Connection Error";
        title.style.color = "#ffc107";
        desc.innerText = "Is the python server running?";
        resultArea.style.borderLeft = "5px solid #ffc107";
    }
}

// --- HISTORY LOGIC ---
function saveToHistory(url, status) {
    chrome.storage.local.get({ scanHistory: [] }, (data) => {
        const history = data.scanHistory;
        
        // Add new item to top
        history.unshift({
            url: url,
            status: status,
            date: new Date().toLocaleDateString()
        });

        // Keep only last 20 items
        if (history.length > 20) history.pop();

        chrome.storage.local.set({ scanHistory: history });
    });
}

function loadHistory() {
    chrome.storage.local.get({ scanHistory: [] }, (data) => {
        const history = data.scanHistory;
        historyList.innerHTML = ""; // Clear list

        if (history.length === 0) {
            historyList.innerHTML = '<div class="empty-state">No scans yet.</div>';
            return;
        }

        history.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <div class="history-url" title="${item.url}">${item.url}</div>
                <div class="badge ${item.status.toLowerCase()}">${item.status}</div>
            `;
            historyList.appendChild(div);
        });
    });
}

// Clear History Button
document.getElementById('btn-clear').addEventListener('click', () => {
    chrome.storage.local.set({ scanHistory: [] }, () => {
        loadHistory();
    });
});