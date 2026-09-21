document.addEventListener('DOMContentLoaded', () => {
    loadRules();

    document.getElementById('add-rule-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const rule = {
            category: document.getElementById('rule-category').value,
            name: document.getElementById('rule-name').value,
            pattern: document.getElementById('rule-pattern').value,
            weight: parseInt(document.getElementById('rule-weight').value)
        };

        try {
            const res = await fetch('http://127.0.0.1:8000/api/rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rule)
            });
            if (res.ok) {
                e.target.reset();
                loadRules();
            }
        } catch (err) {
            alert("Error connecting to backend: " + err);
        }
    });
});

async function loadRules() {
    const tbody = document.getElementById('rules-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Loading rules...</td></tr>';
    
    try {
        const res = await fetch('http://127.0.0.1:8000/api/rules');
        const rules = await res.json();
        
        tbody.innerHTML = '';
        rules.forEach(rule => {
            const tr = document.createElement('tr');
            
            const badgeClass = rule.is_active ? 'badge-active' : 'badge-inactive';
            const badgeText = rule.is_active ? 'ACTIVE' : 'OFF';
            
            tr.innerHTML = `
                <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                <td>${rule.category}</td>
                <td><strong>${rule.name}</strong></td>
                <td><span class="code">${rule.pattern}</span></td>
                <td>${rule.weight}</td>
                <td style="display:flex; gap:8px;">
                    <button class="btn btn-outline" onclick="toggleRule(${rule.id}, ${!rule.is_active})">${rule.is_active ? 'Disable' : 'Enable'}</button>
                    <button class="btn btn-danger" onclick="deleteRule(${rule.id})">Drop</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#ff4444;">Failed to connect to backend engine.</td></tr>`;
    }
}

window.toggleRule = async function(id, newState) {
    try {
        await fetch(`http://127.0.0.1:8000/api/rules/${id}/toggle?is_active=${newState}`, { method: 'PUT' });
        loadRules();
    } catch (err) {
        alert("Failed to toggle rule.");
    }
}

window.deleteRule = async function(id) {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    try {
        await fetch(`http://127.0.0.1:8000/api/rules/${id}`, { method: 'DELETE' });
        loadRules();
    } catch (err) {
        alert("Failed to delete rule.");
    }
}
