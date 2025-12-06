// script.js – Final Phase 4 version (functional Browse + extraction + feedback)

document.addEventListener("DOMContentLoaded", () => {
  let selectedFile = null;
  let lastResponse = null;

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const uploadBtn = document.getElementById("uploadBtn");
  const clearBtn = document.getElementById("clearBtn");
  const output = document.getElementById("output");
  const feedbackOutput = document.getElementById("feedbackOutput");
  const photoOutput = document.getElementById("photoOutput");
  const errorBox = document.getElementById("error");
  const healthBadge = document.getElementById("health");
  const progress = document.getElementById("progress");
  const bar = document.getElementById("bar");
  const downloadBtn = document.getElementById("downloadBtn");

  const dzText = dropzone.querySelector(".dz-text");
  const originalDzText = dzText.innerHTML;  // guardamos el HTML original del dropzone

    // ---------------------------------------------------------
  // Render AI feedback into human-readable HTML
  // ---------------------------------------------------------
  function renderFeedback(feedback) {
    if (!feedback || typeof feedback !== "object") {
      return "<p>No feedback available.</p>";
    }

    let html = "";

    // Overall section
    if (feedback.overall) {
      const score =
        feedback.overall.score != null
          ? Math.round(feedback.overall.score * 100)
          : null;
      const label = feedback.overall.label || "";
      const notes = feedback.overall.notes || [];

      html += `<div class="feedback-section">`;
      html += `<div class="feedback-score-big">${
        score !== null ? score + "%" : "—"
      }</div>`;
      html += `<div class="feedback-score-label">${label}</div>`;

      if (notes.length) {
        html += `<ul class="feedback-list">`;
        for (const n of notes) {
          html += `<li>${n}</li>`;
        }
        html += `</ul>`;
      }
      html += `</div>`;
    }

    // Summary section
    if (feedback.summary) {
      const qLabel = feedback.summary.quality_label || "";
      const suggestions = feedback.summary.suggestions || [];
      html += `<div class="feedback-section">
        <h3>Summary</h3>
        <p><strong>Quality:</strong> ${qLabel}</p>`;

      if (suggestions.length) {
        html += `<p><strong>Suggestions:</strong></p><ul class="feedback-list">`;
        for (const s of suggestions) {
          html += `<li>${s}</li>`;
        }
        html += `</ul>`;
      }
      html += `</div>`;
    }

    // Experience section
    if (Array.isArray(feedback.experience) && feedback.experience.length) {
      html += `<div class="feedback-section">
        <h3>Experience</h3>`;
      for (const exp of feedback.experience) {
        const meta = exp.meta || {};
        const q = exp.quality || {};
        const title = meta.title || "Untitled role";
        const company = meta.company || "";
        const start = meta.start_date || "";
        const end = meta.end_date || "";
        const qLabel = q.clarity_label || "";
        const suggestions = exp.suggestions || [];

        let header = `<strong>${title}</strong>`;
        if (company) header += ` at ${company}`;
        if (start || end) header += ` (${start || "?"} – ${end || "present"})`;

        html += `<p>${header}</p>`;
        if (qLabel) {
          html += `<p><strong>Quality:</strong> ${qLabel}</p>`;
        }
        if (suggestions.length) {
          html += `<ul class="feedback-list">`;
          for (const s of suggestions) {
            html += `<li>${s}</li>`;
          }
          html += `</ul>`;
        }
      }
      html += `</div>`;
    }

    // Skills section
    if (feedback.skills) {
      const rec = feedback.skills.missing_recommended || [];
      const notes = feedback.skills.notes || [];
      html += `<div class="feedback-section">
        <h3>Skills</h3>`;

      if (notes.length) {
        html += `<ul class="feedback-list">`;
        for (const n of notes) {
          html += `<li>${n}</li>`;
        }
        html += `</ul>`;
      }

      if (rec.length) {
        html += `<p><strong>Consider adding:</strong></p><ul class="feedback-list">`;
        for (const s of rec) {
          html += `<li>${s}</li>`;
        }
        html += `</ul>`;
      }

      html += `</div>`;
    }

    if (!html) {
      html = "<p>No detailed feedback available.</p>";
    }

    return html;
  }

  // ---------------------------------------------------------
  // Helper functions
  // ---------------------------------------------------------

  function setError(message) {
    if (!message) {
      errorBox.hidden = true;
      errorBox.textContent = "";
    } else {
      errorBox.hidden = false;
      errorBox.textContent = message;
    }
  }

  function setHealth(status, msg) {
    healthBadge.textContent = msg;
    healthBadge.classList.remove("pill-ok", "pill-error", "pill-warn");
    if (status === "ok") healthBadge.classList.add("pill-ok");
    else if (status === "error") healthBadge.classList.add("pill-error");
    else healthBadge.classList.add("pill-warn");
  }

  function resetOutputs() {
    output.textContent = "{}";
    feedbackOutput.textContent =
      "No feedback yet. Upload a profile to see analysis.";
    photoOutput.textContent =
      "No photo feedback yet. If the PDF contains a profile photo, scores will appear here.";
    lastResponse = null;
    downloadBtn.disabled = true;
  }

  function setProgressVisible(visible) {
    progress.hidden = !visible;
    if (visible) bar.style.width = "0%";
  }

  function setProgressValue(percent) {
    bar.style.width = percent + "%";
  }

  // ---------------------------------------------------------
  // Health check
  // ---------------------------------------------------------
  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) throw new Error("Bad status");
      setHealth("ok", "backend: ok");
    } catch {
      setHealth("error", "backend: offline");
    }
  }
  checkHealth();

  // ---------------------------------------------------------
  // File selection
  // ---------------------------------------------------------
  function handleFiles(files) {
    if (!files || !files.length) return;
    selectedFile = files[0];
    uploadBtn.disabled = false;
    setError("");
    dropzone.classList.add("has-file");
    dzText.innerHTML =
      `<strong>Selected:</strong> ${selectedFile.name}`;
  }

  fileInput.addEventListener("change", (e) => {
    handleFiles(e.target.files);
  });

  // Delegation for Browse button (WORKS EVEN AFTER CLEAR)
  dropzone.addEventListener("click", (e) => {
    if (e.target && e.target.id === "browseBtn") {
      fileInput.click();
    }
  });

  // Drag & Drop
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });
  dropzone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    handleFiles(e.dataTransfer.files);
  });

  // ---------------------------------------------------------
  // Clear button
  // ---------------------------------------------------------
  clearBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    uploadBtn.disabled = true;

    setError("");
    resetOutputs();

    dropzone.classList.remove("has-file");
    dzText.innerHTML = originalDzText;  // restauramos HTML ORIGINAL
  });

  // ---------------------------------------------------------
  // Upload & Extract
  // ---------------------------------------------------------
  uploadBtn.addEventListener("click", async () => {
    if (!selectedFile) {
      setError("Please select a file first.");
      return;
    }

    setError("");
    uploadBtn.disabled = true;
    clearBtn.disabled = true;

    setProgressVisible(true);
    setProgressValue(20);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      setProgressValue(60);

      if (!res.ok) {
        const text = await res.text();
        setError(`Server error ${res.status}: ${text.slice(0, 200)}`);
        setProgressVisible(false);
        return;
      }

      const data = await res.json();
      lastResponse = data;
      downloadBtn.disabled = false;

      // Profile JSON
      output.textContent = JSON.stringify(data.profile, null, 2);

      // NLP Feedback
      if (data.feedback)
        feedbackOutput.textContent = JSON.stringify(data.feedback, null, 2);
      else
        feedbackOutput.textContent = "No NLP feedback returned.";

      // Photo Quality
      if (data.photo_feedback)
        photoOutput.textContent = JSON.stringify(data.photo_feedback, null, 2);
      else
        photoOutput.textContent =
          "No profile photo detected or image analysis unavailable.";

      setProgressValue(100);
      setTimeout(() => setProgressVisible(false), 500);
    } catch (err) {
      console.error(err);
      setError("NetworkError: Cannot reach backend.");
      setProgressVisible(false);
    } finally {
      uploadBtn.disabled = false;
      clearBtn.disabled = false;
    }
  });

  // ---------------------------------------------------------
  // Download final JSON
  // ---------------------------------------------------------
  downloadBtn.addEventListener("click", () => {
    if (!lastResponse) return;

    const blob = new Blob([JSON.stringify(lastResponse, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = (lastResponse.source || "profile") + "_analysis.json";
    a.click();

    URL.revokeObjectURL(url);
  });
});
