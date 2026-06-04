const DASHBOARD_URL = "../outputs/backend/dashboard.json";
const API_PORT = (typeof window !== "undefined" && window.FYP_API_PORT) || 9511;
const API_BASE = `http://127.0.0.1:${API_PORT}`;

let dashboardData = null;
let visibleSamples = [];
let manualRequestSeq = 0;

document.addEventListener("DOMContentLoaded", () => {
    initializeDashboard();
});

async function initializeDashboard() {
    setStatus("Loading longitudinal-trajectory artifacts from outputs/backend/dashboard.json...");

    try {
        const response = await fetch(DASHBOARD_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        dashboardData = await response.json();
        visibleSamples = dashboardData.samples || [];

        renderOverview();
        renderStateModelChart();
        renderTrajectoryValidationChart();
        populateStateSelect();
        renderStateProfileChart(dashboardData.state_profiles[0]?.State);
        renderTrajectoryPrototypes();
        buildManualForm();
        bindFilters();
        renderSampleTable(visibleSamples);
        runManualAssignment();
        setStatus("Dashboard loaded from generated backend artifacts.");
    } catch (error) {
        console.error(error);
        setStatus("Backend output is missing. Run ./run/run_backend.ps1 and refresh this page.");
    }
}

function renderOverview() {
    const overview = dashboardData.overview;
    document.getElementById("totalRecords").textContent = overview.total_records;
    document.getElementById("uniqueStudents").textContent = overview.unique_students;
    document.getElementById("chosenStates").textContent = overview.chosen_states;
    document.getElementById("chosenTrajectories").textContent = overview.chosen_trajectories;
}

function renderStateModelChart() {
    const metrics = dashboardData.state_model_selection || [];
    Plotly.newPlot("stateModelChart", [
        {
            type: "scatter",
            mode: "lines+markers",
            name: "BIC",
            x: metrics.map((item) => item.components),
            y: metrics.map((item) => item.bic),
            line: { color: "#176087", width: 3 }
        },
        {
            type: "scatter",
            mode: "lines+markers",
            name: "AIC",
            x: metrics.map((item) => item.components),
            y: metrics.map((item) => item.aic),
            line: { color: "#b65f2a", width: 3, dash: "dot" }
        }
    ], {
        margin: { t: 20, r: 20, b: 40, l: 50 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        xaxis: { title: "Components" },
        yaxis: { title: "Criterion", gridcolor: "#e8dece" },
        legend: { orientation: "h" }
    }, { responsive: true, displayModeBar: false });
}

function renderTrajectoryValidationChart() {
    const metrics = dashboardData.trajectory_validation || [];
    Plotly.newPlot("trajectoryValidationChart", [
        {
            type: "scatter",
            mode: "lines+markers",
            x: metrics.map((item) => item.clusters),
            y: metrics.map((item) => item.silhouette),
            line: { color: "#176087", width: 3 },
            marker: { color: "#b65f2a", size: 10 }
        }
    ], {
        margin: { t: 20, r: 20, b: 40, l: 50 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        xaxis: { title: "Trajectory Clusters" },
        yaxis: { title: "Silhouette", gridcolor: "#e8dece" }
    }, { responsive: true, displayModeBar: false });
}

function populateStateSelect() {
    const select = document.getElementById("stateSelect");
    select.innerHTML = "";

    for (const profile of dashboardData.state_profiles || []) {
        const option = document.createElement("option");
        option.value = profile.State;
        option.textContent = profile.State;
        select.appendChild(option);
    }

    select.addEventListener("change", (event) => renderStateProfileChart(event.target.value));
}

function renderStateProfileChart(stateName) {
    const profile = (dashboardData.state_profiles || []).find((item) => item.State === stateName);
    if (!profile) {
        return;
    }

    const columns = dashboardData.feature_columns || [];
    Plotly.newPlot("stateProfileChart", [
        {
            type: "bar",
            x: columns.map((column) => dashboardData.feature_labels[column] || column),
            y: columns.map((column) => profile[column]),
            marker: { color: "#176087" },
            hovertemplate: "%{x}: %{y:.2f}<extra></extra>"
        }
    ], {
        margin: { t: 20, r: 20, b: 90, l: 45 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        yaxis: { title: "Mean standardized value", gridcolor: "#e8dece" }
    }, { responsive: true, displayModeBar: false });
}

function renderTrajectoryPrototypes() {
    const container = document.getElementById("trajectoryPrototypeList");
    container.innerHTML = "";
    for (const profile of dashboardData.trajectory_profiles || []) {
        const card = document.createElement("div");
        card.className = "prototype-card";
        card.innerHTML = `
            <strong>${profile.trajectory_label}</strong>
            Students: ${profile.size}<br>
            Mean final grade: ${Number(profile.mean_final_grade).toFixed(2)}<br>
            Prototype: ${profile.prototype_sequence.join(" -> ")}
        `;
        container.appendChild(card);
    }
}

function buildManualForm() {
    const form = document.getElementById("manualForm");
    form.innerHTML = "";
    for (const field of dashboardData.manual_demo.field_schema || []) {
        const wrapper = document.createElement("div");
        wrapper.className = "input-field";
        const select = document.createElement("select");
        select.id = `field-${field.name}`;
        for (const state of dashboardData.manual_demo.states || []) {
            const option = document.createElement("option");
            option.value = state;
            option.textContent = state;
            option.selected = state === field.default;
            select.appendChild(option);
        }

        const label = document.createElement("label");
        label.setAttribute("for", select.id);
        label.textContent = field.label;

        wrapper.appendChild(label);
        wrapper.appendChild(select);
        form.appendChild(wrapper);
    }

    const submitButton = document.createElement("button");
    submitButton.type = "submit";
    submitButton.textContent = "Estimate Trajectory";
    form.appendChild(submitButton);

    const resetButton = document.createElement("button");
    resetButton.type = "button";
    resetButton.className = "secondary";
    resetButton.textContent = "Reset Defaults";
    resetButton.addEventListener("click", () => {
        for (const field of dashboardData.manual_demo.field_schema || []) {
            document.getElementById(`field-${field.name}`).value = field.default;
        }
        runManualAssignment();
    });
    form.appendChild(resetButton);

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        runManualAssignment();
    });
}

async function runManualAssignment() {
    const summary = document.getElementById("manualSummary");
    const values = {};
    for (const field of dashboardData.manual_demo.field_schema || []) {
        values[field.name] = document.getElementById(`field-${field.name}`).value;
    }
    const requestId = ++manualRequestSeq;
    summary.innerHTML = "<em>Contacting backend API...</em>";
    let payload;
    try {
        const response = await fetch(`${API_BASE}/predict`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ values })
        });
        payload = await response.json();
        if (!response.ok) {
            summary.innerHTML = `<strong>Backend error (HTTP ${response.status}).</strong><br><small>${payload.detail || payload.error || ""}</small>`;
            return;
        }
    } catch (error) {
        if (requestId !== manualRequestSeq) return;
        summary.innerHTML = `<strong>Backend unreachable.</strong> Start <code>run/run_backend.ps1</code> (port ${API_PORT}).<br><small>${error.message}</small>`;
        return;
    }
    if (requestId !== manualRequestSeq) return;

    const best = payload.prediction || {};
    const distances = payload.scores || [];
    summary.innerHTML = `
        <strong>${best.trajectory || "--"}</strong>
        Position mismatches: ${best.mismatches ?? "--"}<br>
        Mean trajectory grade: ${Number(best.mean_final_grade ?? 0).toFixed(2)}<br>
        Prototype path: ${(best.prototype || []).join(" -> ")}<br>
        <small>Served by FastAPI on :${API_PORT}</small>
    `;

    Plotly.newPlot("manualTrajectoryChart", [
        {
            type: "bar",
            x: distances.map((item) => item.label),
            y: distances.map((item) => item.distance),
            marker: { color: distances.map((item, index) => index === 0 ? "#176087" : "#d8cfbf") },
            hovertemplate: "%{x}: %{y} mismatches<extra></extra>"
        }
    ], {
        margin: { t: 20, r: 20, b: 60, l: 45 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        yaxis: { title: "Mismatch Count", gridcolor: "#e8dece" }
    }, { responsive: true, displayModeBar: false });
}

function bindFilters() {
    document.getElementById("studentSearch").addEventListener("input", () => {
        const searchValue = document.getElementById("studentSearch").value.trim().toLowerCase();
        visibleSamples = (dashboardData.samples || []).filter((sample) => sample.UserID.toLowerCase().includes(searchValue));
        renderSampleTable(visibleSamples);
    });
}

function renderSampleTable(samples) {
    const body = document.getElementById("sampleTableBody");
    body.innerHTML = "";
    for (const sample of samples.slice(0, 180)) {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${sample.UserID}</td>
            <td><span class="trajectory-pill">${sample.trajectory_label}</span></td>
            <td>${Number(sample.Final_Grade).toFixed(2)}</td>
            <td>${sample.state_sequence}</td>
        `;
        body.appendChild(row);
    }
}

function setStatus(message) {
    document.getElementById("statusMessage").textContent = message;
}