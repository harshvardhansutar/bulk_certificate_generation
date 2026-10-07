document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentJobId = null;
    let pollInterval = null;

    // Elements
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const bulkJobForm = document.getElementById("bulk-job-form");
    const recipientsTextarea = document.getElementById("recipients-json");
    const loadSampleBtn = document.getElementById("load-sample-btn");
    const loadMixedBtn = document.getElementById("load-mixed-btn");
    const loadBulkBtn = document.getElementById("load-bulk-btn");
    const toast = document.getElementById("toast");

    // Monitor Elements
    const jobStatusBadge = document.getElementById("job-status-badge");
    const jobTitleDisplay = document.getElementById("job-title-display");
    const jobSubtitleDisplay = document.getElementById("job-subtitle-display");
    const progressContainer = document.getElementById("progress-container");
    const progressFill = document.getElementById("progress-fill");
    const progressPercent = document.getElementById("progress-percent");
    const progressRatio = document.getElementById("progress-ratio");
    const statsGrid = document.getElementById("stats-grid");
    const statTotal = document.getElementById("stat-total");
    const statSuccess = document.getElementById("stat-success");
    const statFailed = document.getElementById("stat-failed");
    const statJobId = document.getElementById("stat-job-id");
    const certificatesTableCard = document.getElementById("certificates-table-card");
    const certificatesTbody = document.getElementById("certificates-tbody");
    const jobActionsWrapper = document.getElementById("job-actions-wrapper");
    const downloadZipBtn = document.getElementById("download-zip-btn");

    // Verify Elements
    const verifyForm = document.getElementById("verify-form");
    const verifyCodeInput = document.getElementById("verify-code-input");
    const verifyResult = document.getElementById("verify-result");

    // History Elements
    const historyTbody = document.getElementById("history-tbody");
    const refreshHistoryBtn = document.getElementById("refresh-history-btn");

    // Presets
    const sampleRecipients = [
        { "name": "Alice Montgomery", "email": "alice.m@example.com" },
        { "name": "Dr. Brian O'Connor", "email": "brian.oconnor@uni.edu" },
        { "name": "Elena Rostova", "email": "elena.r@techcorp.io" },
        { "name": "Marcus Aurelius Vance", "email": "marcus.vance@company.org" },
        { "name": "Priya Sharma", "email": "priya.sharma@innovate.in" }
    ];

    const mixedRecipients = [
        { "name": "Sophia Reynolds", "email": "sophia@example.com" },
        { "name": "Liam Gallagher", "email": "liam@example.com" },
        { "name": "Faulty Recipient __FAIL_SIMULATION__", "email": "faulty@simulate.test" },
        { "name": "Emma Watson", "email": "emma.w@academy.org" },
        { "name": "Noah Centineo", "email": "noah.c@studios.com" },
        { "name": "Olivia Wilde", "email": "olivia.w@director.io" }
    ];

    const bulk25Recipients = Array.from({ length: 25 }, (_, i) => ({
        name: `Participant ${i + 1} Candidate`,
        email: `participant${i + 1}@domain.com`
    }));

    // Default Load
    recipientsTextarea.value = JSON.stringify(sampleRecipients, null, 2);

    loadSampleBtn.addEventListener("click", () => {
        recipientsTextarea.value = JSON.stringify(sampleRecipients, null, 2);
        showToast("Loaded 5 valid recipients");
    });

    loadMixedBtn.addEventListener("click", () => {
        recipientsTextarea.value = JSON.stringify(mixedRecipients, null, 2);
        showToast("Loaded mixed recipients (1 will fail to demonstrate fault isolation)");
    });

    loadBulkBtn.addEventListener("click", () => {
        recipientsTextarea.value = JSON.stringify(bulk25Recipients, null, 2);
        showToast("Loaded 25 bulk recipients");
    });

    // Tab Navigation
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tabId = item.dataset.tab;
            switchTab(tabId);
        });
    });

    function switchTab(tabId) {
        navItems.forEach(nav => nav.classList.toggle("active", nav.dataset.tab === tabId));
        tabPanes.forEach(pane => pane.classList.toggle("active", pane.id === tabId));

        if (tabId === "history-tab") {
            loadJobHistory();
        }
    }

    // Submit Job
    bulkJobForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        let recipients;
        try {
            recipients = JSON.parse(recipientsTextarea.value);
            if (!Array.isArray(recipients) || recipients.length === 0) {
                showToast("Recipient payload must be a non-empty array of objects", true);
                return;
            }
        } catch (err) {
            showToast("Invalid JSON syntax in recipients textarea", true);
            return;
        }

        const payload = {
            event_name: document.getElementById("event-name").value,
            issuer_name: document.getElementById("issuer-name").value,
            issue_date: document.getElementById("issue-date").value,
            template_title: document.getElementById("template-title").value,
            recipients: recipients
        };

        const submitBtn = document.getElementById("submit-btn");
        submitBtn.disabled = true;
        submitBtn.innerText = "Submitting Batch...";

        try {
            const resp = await fetch("/api/v1/jobs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) {
                const errorData = await resp.json();
                throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : "Submission failed");
            }

            const data = await resp.json();
            showToast(`Batch accepted! Job ID: ${data.job_id.substring(0, 8)}...`);
            currentJobId = data.job_id;

            // Switch to monitor tab and start tracking
            switchTab("active-tab");
            startPollingJob(currentJobId);

        } catch (err) {
            showToast(`Error: ${err.message}`, true);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
                Launch Bulk Generation Job
            `;
        }
    });

    // Polling Job Status
    function startPollingJob(jobId) {
        if (pollInterval) clearInterval(pollInterval);
        currentJobId = jobId;

        progressContainer.style.display = "block";
        statsGrid.style.display = "grid";
        certificatesTableCard.style.display = "block";

        fetchJobDetails(jobId);
        pollInterval = setInterval(() => {
            fetchJobDetails(jobId);
        }, 800);
    }

    async function fetchJobDetails(jobId) {
        try {
            const resp = await fetch(`/api/v1/jobs/${jobId}`);
            if (!resp.ok) return;

            const job = await resp.json();
            renderJobStatus(job);

            if (job.status === "COMPLETED" || job.status === "PARTIALLY_COMPLETED" || job.status === "FAILED") {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        } catch (err) {
            console.error("Poll error:", err);
        }
    }

    function renderJobStatus(job) {
        // Badge
        jobStatusBadge.className = `badge badge-${job.status.toLowerCase().replace('_', '-')}`;
        jobStatusBadge.innerText = job.status.replace("_", " ");

        jobTitleDisplay.innerText = job.title;
        jobSubtitleDisplay.innerText = `${job.event_name} • Issued by ${job.issuer_name} (${job.issue_date})`;

        // Progress
        const pct = job.progress_percentage || 0;
        progressFill.style.width = `${pct}%`;
        progressPercent.innerText = `${pct}%`;
        progressRatio.innerText = `${job.processed_count} / ${job.total_count} Processed`;

        // Stats
        statTotal.innerText = job.total_count;
        statSuccess.innerText = job.success_count;
        statFailed.innerText = job.failure_count;
        statJobId.innerText = job.id.substring(0, 8);

        // ZIP download
        if (job.zip_download_url && job.success_count > 0) {
            jobActionsWrapper.style.display = "block";
            downloadZipBtn.href = job.zip_download_url;
        } else {
            jobActionsWrapper.style.display = "none";
        }

        // Table
        if (job.certificates && job.certificates.length > 0) {
            certificatesTbody.innerHTML = job.certificates.map(cert => {
                const isSuccess = cert.status === "SUCCESS";
                const isFailed = cert.status === "FAILED";
                const statusBadge = `<span class="badge badge-${cert.status.toLowerCase()}">${cert.status}</span>`;

                let details = "-";
                if (isFailed) {
                    details = `<span class="text-danger" title="${escapeHtml(cert.error_message || '')}">⚠️ ${escapeHtml((cert.error_message || '').substring(0, 45))}...</span>`;
                } else if (isSuccess) {
                    details = `<span class="text-muted" style="font-size:0.75rem;">${(cert.file_size / 1024).toFixed(1)} KB • SHA: ${cert.checksum_hash ? cert.checksum_hash.substring(0, 8) : ''}</span>`;
                }

                let actions = "-";
                if (isSuccess && cert.download_url) {
                    actions = `
                        <a href="${cert.download_url}" target="_blank" class="btn btn-sm btn-primary">
                            Download PDF
                        </a>
                        <button class="btn btn-sm btn-ghost copy-code-btn" data-code="${cert.certificate_code}">
                            Copy Code
                        </button>
                    `;
                }

                return `
                    <tr>
                        <td><strong>${escapeHtml(cert.recipient_name)}</strong></td>
                        <td class="text-muted">${escapeHtml(cert.recipient_email)}</td>
                        <td><code style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">${cert.certificate_code}</code></td>
                        <td>${statusBadge}</td>
                        <td>${details}</td>
                        <td>${actions}</td>
                    </tr>
                `;
            }).join("");

            // Copy code buttons
            document.querySelectorAll(".copy-code-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const code = btn.dataset.code;
                    navigator.clipboard.writeText(code);
                    showToast(`Copied code: ${code}`);
                });
            });
        }
    }

    // Verify Tab
    verifyForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const code = verifyCodeInput.value.trim();
        if (!code) return;

        verifyResult.style.display = "block";
        verifyResult.innerHTML = "<p class='text-muted'>Verifying credential with registry...</p>";

        try {
            const resp = await fetch(`/api/v1/certificates/verify/${encodeURIComponent(code)}`);
            const data = await resp.json();

            if (data.valid) {
                verifyResult.innerHTML = `
                    <div class="verify-badge" style="background-color: var(--success-bg); color: var(--success);">
                        ✓ AUTHENTIC & VALID CREDENTIAL
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                        <div>
                            <span class="text-muted" style="font-size: 0.75rem;">RECIPIENT NAME</span>
                            <p style="font-weight: 700; font-size: 1.1rem;">${escapeHtml(data.recipient_name)}</p>
                        </div>
                        <div>
                            <span class="text-muted" style="font-size: 0.75rem;">CREDENTIAL CODE</span>
                            <p style="font-family: 'JetBrains Mono', monospace;">${data.certificate_code}</p>
                        </div>
                        <div>
                            <span class="text-muted" style="font-size: 0.75rem;">EVENT / COURSE</span>
                            <p style="font-weight: 600;">${escapeHtml(data.event_name)}</p>
                        </div>
                        <div>
                            <span class="text-muted" style="font-size: 0.75rem;">ISSUED BY</span>
                            <p>${escapeHtml(data.issuer_name)}</p>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid var(--border-color);">
                        <span class="text-muted" style="font-size: 0.75rem;">SHA-256 INTEGRITY HASH</span>
                        <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; word-break: break-all; color: var(--gold);">${data.checksum_hash || 'N/A'}</p>
                    </div>
                `;
            } else {
                verifyResult.innerHTML = `
                    <div class="verify-badge" style="background-color: var(--danger-bg); color: var(--danger);">
                        ✗ INVALID OR UNRECOGNIZED CREDENTIAL
                    </div>
                    <p class="text-muted">${escapeHtml(data.message)}</p>
                `;
            }
        } catch (err) {
            verifyResult.innerHTML = `<p class="text-danger">Verification network error: ${err.message}</p>`;
        }
    });

    // History Tab
    async function loadJobHistory() {
        historyTbody.innerHTML = "<tr><td colspan='7' class='text-center text-muted'>Loading jobs...</td></tr>";
        try {
            const resp = await fetch("/api/v1/jobs?page=1&page_size=20");
            const data = await resp.json();

            if (!data.jobs || data.jobs.length === 0) {
                historyTbody.innerHTML = "<tr><td colspan='7' class='text-center text-muted'>No jobs found. Launch one from the New Bulk Job tab!</td></tr>";
                return;
            }

            historyTbody.innerHTML = data.jobs.map(j => {
                const dateStr = j.created_at ? new Date(j.created_at).toLocaleString() : "-";
                const badge = `<span class="badge badge-${j.status.toLowerCase().replace('_', '-')}">${j.status.replace("_", " ")}</span>`;
                return `
                    <tr>
                        <td><strong>${escapeHtml(j.title)}</strong></td>
                        <td>${escapeHtml(j.event_name)}</td>
                        <td>${escapeHtml(j.issue_date)}</td>
                        <td>${badge}</td>
                        <td>${j.success_count} / ${j.total_count}</td>
                        <td class="text-muted" style="font-size: 0.75rem;">${dateStr}</td>
                        <td>
                            <button class="btn btn-sm btn-primary inspect-job-btn" data-id="${j.id}">
                                Inspect
                            </button>
                        </td>
                    </tr>
                `;
            }).join("");

            document.querySelectorAll(".inspect-job-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const id = btn.dataset.id;
                    switchTab("active-tab");
                    startPollingJob(id);
                });
            });

        } catch (err) {
            historyTbody.innerHTML = `<tr><td colspan='7' class='text-danger'>Failed loading history: ${err.message}</td></tr>`;
        }
    }

    refreshHistoryBtn.addEventListener("click", loadJobHistory);

    // Helpers
    function showToast(msg, isError = false) {
        toast.innerText = msg;
        toast.style.borderColor = isError ? "var(--danger)" : "var(--primary)";
        toast.style.color = isError ? "var(--danger)" : "var(--text-primary)";
        toast.style.display = "block";
        setTimeout(() => {
            toast.style.display = "none";
        }, 3500);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
