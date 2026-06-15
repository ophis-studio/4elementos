// app.js - Client-side logic for the repo_to_market_analyzer dashboard

let currentAuditData = null;

// Tab Management
function switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');
    
    tabs.forEach(tab => {
        if (tab.getAttribute('onclick').includes(tabId)) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    panels.forEach(panel => {
        if (panel.id === `panel-${tabId}`) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
}

// Form Submission & Progress Lifecycle
async function runAudit(event) {
    event.preventDefault();
    
    const path = document.getElementById('input-path').value;
    const query = document.getElementById('input-query').value;
    const techStack = document.getElementById('input-tech-stack').value;
    const pattern = document.getElementById('input-pattern').value;
    
    const loader = document.getElementById('loader');
    const loaderSteps = document.querySelectorAll('.step-loading-list li');
    
    // Reset loader states
    loaderSteps.forEach(li => li.className = 'pending');
    loader.style.display = 'flex';
    
    try {
        // Step 1: Start
        setLoaderStep(0, 'active');
        await delay(800);
        
        // Step 2: Code analysis
        setLoaderStep(0, 'done');
        setLoaderStep(1, 'active');
        await delay(600);
        
        // Step 3: API search GitHub
        setLoaderStep(1, 'done');
        setLoaderStep(2, 'active');
        
        // Make the API request to audit.php
        const response = await fetch('audit.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'full',
                path: path,
                query: query,
                tech_stack: techStack,
                monetization_pattern: pattern
            })
        });
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Error del servidor HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || "Ocurrió un error desconocido durante la auditoría.");
        }
        
        currentAuditData = result;
        
        // Step 4: Academic search
        setLoaderStep(2, 'done');
        setLoaderStep(3, 'active');
        await delay(700);
        
        // Step 5: Business mapping
        setLoaderStep(3, 'done');
        setLoaderStep(4, 'active');
        await delay(600);
        
        // Step 6: Render
        setLoaderStep(4, 'done');
        setLoaderStep(5, 'active');
        await delay(500);
        
        loader.style.display = 'none';
        
        // Show dashboard container and render details
        document.getElementById('dashboard-container').style.display = 'grid';
        renderAuditDashboard(result);
        
        // Auto navigate to the first tab (General)
        switchTab('general');
        
    } catch (error) {
        loader.style.display = 'none';
        alert(`Error al ejecutar la auditoría:\n${error.message}`);
    }
}

function setLoaderStep(index, state) {
    const loaderSteps = document.querySelectorAll('.step-loading-list li');
    if (loaderSteps[index]) {
        loaderSteps[index].className = state;
    }
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Rendering Dashboards
function renderAuditDashboard(data) {
    const audit = data.audit;
    const market = data.market;
    const business = data.business;
    
    // --- TAB 1: GENERAL ---
    // Update simple metrics
    document.getElementById('stat-files').innerText = audit.files_count;
    document.getElementById('stat-size').innerText = formatBytes(audit.total_size_bytes);
    document.getElementById('stat-license').innerText = audit.licenses_detected.join(', ');
    
    // Tech debt score dial
    const score = audit.quality_metrics.tech_debt_score;
    const dial = document.getElementById('dial-score-val');
    // Circle circumference is 2 * PI * r = 2 * 3.14159 * 40 = 251.3
    const circumference = 251.3;
    const offset = circumference - (score / 100) * circumference;
    dial.style.strokeDasharray = `${circumference} ${circumference}`;
    dial.style.strokeDashoffset = offset;
    document.getElementById('dial-score-text').innerText = score;
    
    // Tech debt description coloring
    let statusText = "Excelente";
    let statusColor = "#10b981";
    if (score > 60) {
        statusText = "Crítico";
        statusColor = "#f43f5e";
    } else if (score > 35) {
        statusText = "Moderado";
        statusColor = "#f59e0b";
    }
    document.getElementById('dial-score-label').innerText = `DEUDA: ${statusText}`;
    dial.style.stroke = statusColor;
    
    // File extensions chart (glowing bars)
    const extContainer = document.getElementById('extensions-container');
    extContainer.innerHTML = '';
    const sortedExts = Object.entries(audit.extensions).sort((a, b) => b[1] - a[1]);
    const maxVal = sortedExts[0] ? sortedExts[0][1] : 1;
    
    sortedExts.forEach(([ext, count]) => {
        const pct = (count / maxVal) * 100;
        const row = document.createElement('div');
        row.style.marginBottom = '0.75rem';
        row.innerHTML = `
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:0.15rem;">
                <span style="font-family:var(--font-mono); font-weight:600;">${ext || 'sin ext'}</span>
                <span style="color:var(--text-muted);">${count} archivos</span>
            </div>
            <div style="height:6px; background:rgba(255,255,255,0.05); border-radius:3px; overflow:hidden;">
                <div style="width:${pct}%; height:100%; background:linear-gradient(to right, var(--primary), var(--secondary)); border-radius:3px;"></div>
            </div>
        `;
        extContainer.appendChild(row);
    });
    
    // Architecture patterns
    const archContainer = document.getElementById('architecture-container');
    archContainer.innerHTML = '';
    audit.architecture_patterns.forEach(pattern => {
        const span = document.createElement('span');
        span.className = 'meta-badge primary-badge';
        span.style.padding = '0.35rem 0.75rem';
        span.style.fontSize = '0.75rem';
        span.innerText = pattern;
        archContainer.appendChild(span);
    });
    
    
    // --- TAB 2: CODE QUALITY ---
    // Dependencies scan
    const depContainer = document.getElementById('dependencies-container');
    depContainer.innerHTML = '';
    const deps = audit.dependencies;
    let depCount = 0;
    
    const renderDepSection = (title, items, type) => {
        if (!items || items.length === 0) return;
        depCount += items.length;
        const sec = document.createElement('div');
        sec.style.marginBottom = '1.25rem';
        sec.innerHTML = `
            <h5 style="font-family:var(--font-heading); font-size:0.8rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:0.5rem; letter-spacing:0.05em;">
                ${title} (${items.length})
            </h5>
            <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
                ${items.map(i => `<span class="meta-badge">${escapeHTML(i)}</span>`).join('')}
            </div>
        `;
        depContainer.appendChild(sec);
    };
    
    renderDepSection('Dependencias Node.js (npm)', deps.npm, 'npm');
    renderDepSection('Dependencias Python', deps.python, 'python');
    renderDepSection('Dependencias Composer (PHP)', deps.composer, 'composer');
    renderDepSection('Otras dependencias', deps.other, 'other');
    
    if (depCount === 0) {
        depContainer.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted); italic">No se detectaron archivos de manifiesto de dependencias estándar.</p>`;
    }
    
    // Quality issues summaries
    document.getElementById('metric-todos').innerText = audit.quality_metrics.todo_count;
    document.getElementById('metric-risks').innerText = audit.quality_metrics.security_risks_count;
    document.getElementById('metric-tests').innerText = audit.quality_metrics.test_files_count;
    document.getElementById('metric-coverage').innerText = `${audit.quality_metrics.estimated_test_coverage}%`;
    
    // Security risks table
    const riskBody = document.getElementById('risks-table-body');
    riskBody.innerHTML = '';
    const risks = audit.quality_metrics.risk_details;
    
    if (risks.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="4" style="text-align:center; color:var(--text-muted); font-style:italic; padding:1.5rem;">No se detectaron vulnerabilidades críticas ni riesgos SAST estáticos.</td>`;
        riskBody.appendChild(tr);
    } else {
        risks.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <span class="risk-badge ${r.severity.toLowerCase()}">${r.severity}</span>
                </td>
                <td>
                    <div style="font-weight:600;">${escapeHTML(r.risk)}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted); font-family:var(--font-mono);">${escapeHTML(r.file)}:L${r.line}</div>
                </td>
                <td style="font-family:var(--font-mono); font-size:0.75rem; color:#f43f5e; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    <code>${escapeHTML(r.trigger)}</code>
                </td>
            `;
            riskBody.appendChild(tr);
        });
    }
    
    
    // --- TAB 3: MARKET RESEARCH ---
    // Competitors
    const compsContainer = document.getElementById('competitors-container');
    compsContainer.innerHTML = '';
    const comps = market.competitors;
    if (comps.length === 0) {
        compsContainer.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted); font-style:italic">No se encontraron competidores directos con la búsqueda.</p>`;
    } else {
        comps.forEach(c => {
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-details">
                    <h4>${escapeHTML(c.full_name || c.name)}</h4>
                    <p>${escapeHTML(c.description || 'Sin descripción disponible.')}</p>
                    <div class="item-meta">
                        <span class="meta-badge">⭐ ${c.stars} stars</span>
                        <span class="meta-badge">🍴 ${c.forks} forks</span>
                        <span class="meta-badge">${c.license}</span>
                    </div>
                </div>
                <a href="${c.url}" target="_blank" class="link-btn">Ver Repo</a>
            `;
            compsContainer.appendChild(card);
        });
    }
    
    // Papers
    const papersContainer = document.getElementById('papers-container');
    papersContainer.innerHTML = '';
    const papers = market.academic_papers;
    if (papers.length === 0) {
        papersContainer.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted); font-style:italic">No se encontraron papers académicos.</p>`;
    } else {
        papers.forEach(p => {
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-details">
                    <h4>${escapeHTML(p.title)}</h4>
                    <p>Autores: ${escapeHTML(p.authors)}</p>
                    <div class="item-meta">
                        <span class="meta-badge">${p.year}</span>
                        <span class="meta-badge primary-badge">${p.source}</span>
                        <span class="meta-badge" style="text-transform: capitalize;">${p.type}</span>
                    </div>
                </div>
                <a href="${p.url}" target="_blank" class="link-btn">Paper</a>
            `;
            papersContainer.appendChild(card);
        });
    }
    
    // Gap Analysis
    document.getElementById('gap-analysis-text').innerText = market.gap_analysis;
    
    
    // --- TAB 4: BUSINESS ARCHITECTURE ---
    // Monetization recommendations
    document.getElementById('rec-pattern').innerText = business.monetization_pattern;
    document.getElementById('license-remarks').innerText = business.license_compliance.remarks;
    
    // MVP scope
    document.getElementById('mvp-weeks').innerText = business.mvp_scope_estimation.estimated_development_weeks;
    document.getElementById('mvp-hours').innerText = business.mvp_scope_estimation.estimated_development_hours;
    document.getElementById('mvp-complexity').innerText = business.mvp_scope_estimation.complexity_modifier;
    
    const milesContainer = document.getElementById('mvp-milestones-container');
    milesContainer.innerHTML = '';
    business.mvp_scope_estimation.key_milestones.forEach(m => {
        const li = document.createElement('li');
        li.style.marginBottom = '0.5rem';
        li.innerHTML = `<strong>${escapeHTML(m.name)}:</strong> <span style="color:var(--text-muted);">${escapeHTML(m.deliverable)}</span>`;
        milesContainer.appendChild(li);
    });
    
    // Lean Canvas
    const canvas = business.lean_canvas;
    const injectCanvasList = (elementId, items) => {
        const el = document.getElementById(elementId);
        el.innerHTML = '';
        items.forEach(i => {
            const li = document.createElement('li');
            li.innerText = i;
            el.appendChild(li);
        });
    };
    
    injectCanvasList('canvas-problem', canvas.problem);
    injectCanvasList('canvas-solution', canvas.solution);
    injectCanvasList('canvas-uvp', canvas.unique_value_proposition);
    injectCanvasList('canvas-advantage', canvas.unfair_advantage);
    injectCanvasList('canvas-segments', canvas.customer_segments);
    injectCanvasList('canvas-metrics', canvas.key_metrics);
    injectCanvasList('canvas-channels', canvas.channels);
    injectCanvasList('canvas-costs', canvas.cost_structure);
    injectCanvasList('canvas-revenue', canvas.revenue_streams);
    
    // Financial matrices setup
    // Initialise slider defaults from returned backend calculations
    document.getElementById('calc-dev-hours').value = business.mvp_scope_estimation.estimated_development_hours;
    document.getElementById('calc-dev-hours-val').innerText = business.mvp_scope_estimation.estimated_development_hours;
    
    // Trigger calculator
    calculateProjections();
}

function calculateProjections() {
    if (!currentAuditData) return;
    
    const business = currentAuditData.business;
    
    // Read user slider overrides
    const devHours = parseInt(document.getElementById('calc-dev-hours').value);
    const devRate = parseFloat(document.getElementById('calc-dev-rate').value);
    const infraSetup = parseFloat(document.getElementById('calc-infra-setup').value);
    const mrrClients = parseInt(document.getElementById('calc-target-clients').value);
    
    // Recalculate
    const devCost = devHours * devRate;
    const initialInvestment = devCost + infraSetup;
    
    // Find average pricing from business model
    const tiers = business.financial_matrix.pricing_tiers;
    let avgPrice = 29.0; // Startup tier default
    if (tiers && tiers[1] && tiers[1].price_usd > 0) {
        avgPrice = tiers[1].price_usd;
    } else if (tiers && tiers[2] && tiers[2].price_usd > 0) {
        avgPrice = tiers[2].price_usd;
    }
    
    const breakEven = Math.ceil(initialInvestment / (avgPrice || 1));
    const mrrConservative = avgPrice * 10;
    const mrrTarget = (avgPrice * (mrrClients * 0.9)) + ((tiers && tiers[2] && tiers[2].price_usd > 0 ? tiers[2].price_usd : 199.0) * (mrrClients * 0.1));
    
    // Update DOM UI
    document.getElementById('calc-dev-hours-val').innerText = devHours;
    document.getElementById('calc-dev-rate-val').innerText = `$${devRate}`;
    document.getElementById('calc-infra-setup-val').innerText = `$${infraSetup}`;
    document.getElementById('calc-target-clients-val').innerText = mrrClients;
    
    document.getElementById('res-mvp-cost').innerText = `$${devCost.toLocaleString('en-US', {maximumFractionDigits:0})}`;
    document.getElementById('res-initial-invest').innerText = `$${initialInvestment.toLocaleString('en-US', {maximumFractionDigits:0})}`;
    document.getElementById('res-breakeven').innerText = `${breakEven} clientes`;
    document.getElementById('res-mrr-10').innerText = `$${mrrConservative.toLocaleString('en-US', {maximumFractionDigits:0})}`;
    document.getElementById('res-mrr-target').innerText = `$${mrrTarget.toLocaleString('en-US', {maximumFractionDigits:0})}`;
    
    // Render dynamic tier table
    const tierBody = document.getElementById('tiers-table-body');
    tierBody.innerHTML = '';
    if (tiers && tiers.length > 0) {
        tiers.forEach(t => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:600; color:#fff;">${escapeHTML(t.name)}</td>
                <td style="font-family:var(--font-mono); font-weight:700; color:var(--secondary);">$${t.price_usd} / ${t.billing}</td>
                <td style="font-size:0.75rem; color:var(--text-muted);">${escapeHTML(t.features)}</td>
            `;
            tierBody.appendChild(tr);
        });
    }
}

// Helpers
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
