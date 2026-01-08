document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const views = { scan: document.getElementById('viewScan'), history: document.getElementById('viewHistory') };
    const tabs = { scan: document.getElementById('tabScan'), history: document.getElementById('tabHistory') };
    
    // Tab Logic
    tabs.scan.onclick = () => switchTab('scan');
    tabs.history.onclick = () => { switchTab('history'); loadHistory(); };

    function switchTab(mode) {
        views.scan.classList.add('hidden');
        views.history.classList.add('hidden');
        tabs.scan.classList.remove('active');
        tabs.history.classList.remove('active');
        
        views[mode].classList.remove('hidden');
        tabs[mode].classList.add('active');
    }

    // Scan Logic
    document.getElementById('checkBtn').onclick = async () => {
        const text = document.getElementById('userInput').value.trim();
        if (!text) return;
        
        const btn = document.getElementById('checkBtn');
        const resDiv = document.getElementById('result');
        
        btn.innerText = "Scanning...";
        resDiv.className = "hidden";

        try {
            const response = await fetch('http://127.0.0.1:8000/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: text })
            });
            const data = await response.json();
            
            resDiv.classList.remove('hidden');
            if (data.result === "SAFE") {
                resDiv.className = "status-safe";
                resDiv.innerHTML = "✅ <b>Safe Link</b>";
            } else {
                resDiv.className = "status-danger";
                resDiv.innerHTML = "⚠️ <b>PHISHING DETECTED</b>";
            }
        } catch (e) {
            resDiv.className = "status-neutral";
            resDiv.innerText = "Error: Server Offline";
        }
        btn.innerText = "Scan URL";
    };

    // History Logic
    async function loadHistory() {
        const list = document.getElementById('historyList');
        list.innerHTML = "Loading...";
        try {
            const response = await fetch('http://127.0.0.1:8000/history');
            const data = await response.json();
            list.innerHTML = "";
            
            if (data.history.length === 0) {
                list.innerHTML = "<li>No recent threats detected.</li>";
                return;
            }

            data.history.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `<span>⚠️ ${item.url.substring(0, 30)}...</span><small>${item.date.split(' ')[1]}</small>`;
                list.appendChild(li);
            });
        } catch (e) {
            list.innerHTML = "Failed to load history.";
        }
    }
    
    document.getElementById('refreshHistory').onclick = loadHistory;
});