(function () {
    const dashboardUrl = "../outputs/backend/dashboard.json";
    const liveModeKey = `fyp-standalone-live-mode:${window.location.pathname}`;
    const pollIntervalMs = 10000;

    let liveModeEnabled = window.localStorage.getItem(liveModeKey) !== "off";
    let pollTimer = null;
    let latestGeneratedAt = null;

    function setChipState(statusChip, nextText, stateClass) {
        statusChip.textContent = nextText;
        statusChip.classList.remove("is-live", "is-missing");
        if (stateClass) {
            statusChip.classList.add(stateClass);
        }
    }

    function renderLiveModeButton(button) {
        button.textContent = liveModeEnabled ? "Live mode: on" : "Live mode: off";
        button.classList.toggle("is-live-mode", liveModeEnabled);
    }

    async function fetchPayload() {
        const response = await fetch(dashboardUrl, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    }

    function applyPayload(payload, elements) {
        const generatedAt = payload.project?.generated_at || null;
        elements.titleEl.textContent = payload.project?.title || document.title;
        setChipState(elements.statusChip, "Live output ready", "is-live");
        latestGeneratedAt = generatedAt;
    }

    async function pollPayload(elements, options) {
        try {
            const payload = await fetchPayload();
            const nextGeneratedAt = payload.project?.generated_at || null;
            if (options.reloadOnChange && latestGeneratedAt && nextGeneratedAt && latestGeneratedAt !== nextGeneratedAt) {
                window.location.reload();
                return;
            }
            applyPayload(payload, elements);
        } catch (error) {
            console.error(error);
            setChipState(elements.statusChip, "Output missing", "is-missing");
        }
    }

    function syncPolling(elements) {
        if (pollTimer) {
            window.clearInterval(pollTimer);
            pollTimer = null;
        }
        if (!liveModeEnabled) {
            return;
        }
        pollTimer = window.setInterval(() => {
            pollPayload(elements, { reloadOnChange: true });
        }, pollIntervalMs);
    }

    function buildShell() {
        if (document.querySelector(".fyp-utility-bar")) {
            return;
        }

        document.body.classList.add("fyp-shell-enhanced");

        const shell = document.createElement("div");
        shell.className = "fyp-utility-bar";
        shell.innerHTML = `
            <div class="fyp-utility-meta">
                <span class="fyp-utility-title" data-role="title">${document.title}</span>
                <button type="button" class="fyp-utility-chip is-button" data-role="live-mode"></button>
                <span class="fyp-utility-chip" data-role="status">Checking live output...</span>
                <span class="fyp-utility-chip">Python-only runtime</span>
                <span class="fyp-utility-chip">Manual demo enabled</span>
            </div>
            <nav class="fyp-utility-links" aria-label="Project shortcuts">
                <a href="../README.md">README</a>
                <a href="../data/raw/">Local Data</a>
                <a href="../outputs/backend/dashboard.json">Live Output JSON</a>
                <a href="../run/">Run Scripts</a>
                <button type="button" data-role="refresh">Refresh</button>
            </nav>
        `;
        document.body.prepend(shell);

        // Thin strip at the very top edge; hovering it slides the auto-hidden bar in.
        const hoverZone = document.createElement("div");
        hoverZone.className = "fyp-shell-hover-zone";
        hoverZone.setAttribute("aria-hidden", "true");
        document.body.prepend(hoverZone);

        const elements = {
            titleEl: shell.querySelector('[data-role="title"]'),
            statusChip: shell.querySelector('[data-role="status"]'),
            liveModeButton: shell.querySelector('[data-role="live-mode"]'),
            refreshButton: shell.querySelector('[data-role="refresh"]'),
        };

        renderLiveModeButton(elements.liveModeButton);
        elements.liveModeButton.addEventListener("click", () => {
            liveModeEnabled = !liveModeEnabled;
            window.localStorage.setItem(liveModeKey, liveModeEnabled ? "on" : "off");
            renderLiveModeButton(elements.liveModeButton);
            syncPolling(elements);
        });
        elements.refreshButton.addEventListener("click", () => {
            window.location.reload();
        });

        pollPayload(elements, { reloadOnChange: false });
        syncPolling(elements);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", buildShell);
    } else {
        buildShell();
    }
})();
