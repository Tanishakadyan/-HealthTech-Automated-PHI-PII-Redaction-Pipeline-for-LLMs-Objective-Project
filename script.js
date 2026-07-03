/*
=======================================================================
  PHI / PII REDACTION TOOL — JAVASCRIPT
  Connects the frontend UI to the live FastAPI backend.

  Backend must be running at API_BASE_URL (default http://127.0.0.1:8000)
  Start it with: cd backend && uvicorn main:app --reload --port 8000
=======================================================================
*/

let originalText = "";
let redactedText = "";
let lastEntities = [];
let isShowingOriginal = false;

// Backend URL — change this if your backend runs elsewhere
const API_BASE_URL = "http://127.0.0.1:8000";

// Pre-filled demo clinical notes (fake data only — never use real PHI here)
const SAMPLE_NOTES = {
  "1":
    "Patient John Smith, DOB 12/05/1985, MRN 100234, called on 555-123-4567. " +
    "Email: john.smith@email.com. Address: 45 Oak Street, Boston MA 02101. " +
    "Diagnosed with Parkinson's disease in 2019.",

  "2":
    "Prescription for Emily Johnson, DOB 03/22/1990, MRN-200456. " +
    "Doctor: Dr. Robert Chen. Date: 06/01/2026. " +
    "Contact: emily.johnson@gmail.com | 617-555-8899.",

  "3":
    "Dear Dr. Patricia Williams, I am referring Mr. David Lee, born 07/14/1975, " +
    "MRN 300789, residing at 88 Pine Avenue, Chicago IL 60601. " +
    "Contact: david.lee@hospital.org | 312-555-6677."
};


document.addEventListener("DOMContentLoaded", function () {

  const inputTextarea = document.getElementById("inputText");
  const charCountEl = document.getElementById("charCount");

  // -- Character counter --
  inputTextarea.addEventListener("input", function () {
    const len = this.value.length;
    charCountEl.textContent = len + " / 5000";
    charCountEl.style.color = len > 4500 ? "#dc3545" : "#6c757d";
  });

  // -- Clear button --
  document.getElementById("clearBtn").addEventListener("click", function () {
    inputTextarea.value = "";
    charCountEl.textContent = "0 / 5000";
    charCountEl.style.color = "#6c757d";

    document.getElementById("resultCard").innerHTML =
      '<span class="text-muted" id="placeholderText">Results will appear here after you click <strong>Redact PHI</strong>.</span>';
    document.getElementById("resultCard").classList.remove("has-result");
    document.getElementById("resultActions").style.display = "none";
    document.getElementById("statsBar").style.display = "none";
    document.getElementById("entityLegend").style.display = "none";
    hideError();

    originalText = "";
    redactedText = "";
    lastEntities = [];
    isShowingOriginal = false;
    document.getElementById("restoreBtn").textContent = "Show Original Text";
  });

  // -- Redact button: main API call --
  document.getElementById("redactBtn").addEventListener("click", async function () {

    const inputText = inputTextarea.value.trim();

    if (inputText === "") {
      showError("Please enter some clinical text before clicking Redact PHI.");
      inputTextarea.focus();
      return;
    }
    if (inputText.length > 5000) {
      showError("Text is too long. Please enter less than 5000 characters.");
      return;
    }

    document.getElementById("loadingMsg").style.display = "flex";
    document.getElementById("redactBtn").disabled = true;
    document.getElementById("resultCard").innerHTML =
      '<span class="text-muted">Analyzing text and detecting PHI entities...</span>';
    document.getElementById("resultActions").style.display = "none";
    document.getElementById("statsBar").style.display = "none";
    document.getElementById("entityLegend").style.display = "none";
    hideError();

    originalText = inputText;
    isShowingOriginal = false;
    document.getElementById("restoreBtn").textContent = "Show Original Text";

    try {
      const response = await fetch(API_BASE_URL + "/redact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || ("Server error " + response.status));
      }

      const data = await response.json();
      redactedText = data.redacted_text || "";
      lastEntities = data.entities || [];

      renderRedactedHTML(redactedText, lastEntities);
      updateEntityCounts(lastEntities);
      updateStatsBar(lastEntities);

      document.getElementById("resultActions").style.display = "flex";

    } catch (error) {
      console.error("Redact API Error:", error);

      if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
        showError(
          "Cannot connect to backend. Make sure the FastAPI server is running: " +
          "cd backend and run uvicorn main:app --reload --port 8000"
        );
        document.getElementById("resultCard").innerHTML =
          '<span class="text-danger"><strong>Connection failed.</strong> Backend API is not reachable at ' +
          API_BASE_URL + '<br><small class="text-muted">Start it with: ' +
          '<code>uvicorn main:app --reload --port 8000</code></small></span>';
      } else {
        showError("Error: " + error.message);
        document.getElementById("resultCard").innerHTML =
          '<span class="text-danger">An error occurred. See the message above.</span>';
      }
    }

    document.getElementById("loadingMsg").style.display = "none";
    document.getElementById("redactBtn").disabled = false;
  });

  // -- Restore button: toggle redacted/original via /restore API --
  document.getElementById("restoreBtn").addEventListener("click", async function () {

    if (isShowingOriginal) {
      renderRedactedHTML(redactedText, lastEntities);
      this.textContent = "Show Original Text";
      isShowingOriginal = false;
      return;
    }

    try {
      this.textContent = "Restoring...";
      this.disabled = true;

      const response = await fetch(API_BASE_URL + "/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ redacted_text: redactedText })
      });

      if (!response.ok) throw new Error("Restore failed: " + response.status);

      const data = await response.json();
      document.getElementById("resultCard").innerText = data.original_text;
      document.getElementById("resultCard").classList.remove("has-result");

      this.textContent = "Show Redacted Text";
      isShowingOriginal = true;

    } catch (error) {
      console.warn("Restore API failed, using local copy:", error);
      document.getElementById("resultCard").innerText = originalText;
      this.textContent = "Show Redacted Text";
      isShowingOriginal = true;
    }

    this.disabled = false;
  });

  // -- Copy button --
  document.getElementById("copyBtn").addEventListener("click", function () {
    const text = document.getElementById("resultCard").innerText;
    navigator.clipboard.writeText(text).then(function () {
      const btn = document.getElementById("copyBtn");
      const original = btn.textContent;
      btn.textContent = "Copied!";
      btn.classList.add("btn-success");
      btn.classList.remove("btn-outline-primary");
      setTimeout(function () {
        btn.textContent = original;
        btn.classList.remove("btn-success");
        btn.classList.add("btn-outline-primary");
      }, 2000);
    }).catch(function () {
      showError("Could not copy - please select the text manually and copy with Ctrl+C.");
    });
  });

  // -- Download button --
  document.getElementById("downloadBtn").addEventListener("click", function () {
    const text = document.getElementById("resultCard").innerText;
    const timestamp = new Date().toLocaleString();
    const fileContent =
      "PHI/PII REDACTED CLINICAL NOTE\n" +
      "Generated by: PHI Redaction Tool\n" +
      "Timestamp: " + timestamp + "\n" +
      "-----------------------------------------------\n\n" + text;

    const blob = new Blob([fileContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "redacted_output_" + Date.now() + ".txt";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  });

  // -- Sample note buttons --
  document.querySelectorAll(".sample-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const sampleNumber = this.getAttribute("data-sample");
      const sampleText = SAMPLE_NOTES[sampleNumber];
      if (sampleText) {
        inputTextarea.value = sampleText;
        charCountEl.textContent = sampleText.length + " / 5000";
        charCountEl.style.color = "#6c757d";
        inputTextarea.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  });

});


// -- renderRedactedHTML: shows colored badges for each entity --
function renderRedactedHTML(text, entities) {
  if (!entities || entities.length === 0) {
    document.getElementById("resultCard").innerText = text;
    document.getElementById("resultCard").classList.remove("has-result");
    return;
  }

  let displayText = escapeHTML(text);

  // Replace longest tokens first to avoid partial overlaps
  const sorted = [...entities].sort(
    (a, b) => (b.replacement || "").length - (a.replacement || "").length
  );

  sorted.forEach(function (entity) {
    const placeholder = entity.replacement || "";
    const label = entity.label || "OTHER";
    const original = entity.text || "";
    if (!placeholder) return;

    const badge =
      '<span class="redacted-token entity-' + label + '" ' +
      'title="Original: ' + escapeHTML(original) + ' (' + label + ')">' +
      '[' + label + ']' +
      '</span>';

    displayText = displayText.split(placeholder).join(badge);
  });

  displayText = displayText.replace(/\n/g, "<br>");
  document.getElementById("resultCard").innerHTML = displayText;
  document.getElementById("resultCard").classList.add("has-result");
}


// -- updateEntityCounts: fills entity legend with counts --
function updateEntityCounts(entities) {
  if (!entities || entities.length === 0) {
    document.getElementById("entityLegend").style.display = "none";
    return;
  }

  const counts = {};
  entities.forEach(function (entity) {
    const label = entity.label || "OTHER";
    counts[label] = (counts[label] || 0) + 1;
  });

  let html = "";
  for (const label in counts) {
    html += '<span class="redacted-token entity-' + label + '">' +
      label + ': ' + counts[label] + '</span>';
  }

  document.getElementById("entityCounts").innerHTML = html;
  document.getElementById("entityLegend").style.display = "block";
}


// -- updateStatsBar: total entity count summary --
function updateStatsBar(entities) {
  const total = entities ? entities.length : 0;
  document.getElementById("totalCount").textContent = total;
  document.getElementById("statsBar").style.display = total > 0 ? "block" : "none";
}


// -- showError / hideError --
function showError(message) {
  const banner = document.getElementById("errorBanner");
  const msgSpan = document.getElementById("errorMessage");
  msgSpan.textContent = message;
  banner.style.display = "flex";
  clearTimeout(window._errorTimeout);
  window._errorTimeout = setTimeout(hideError, 8000);
}

function hideError() {
  document.getElementById("errorBanner").style.display = "none";
}


// -- escapeHTML: prevents HTML injection from clinical text --
function escapeHTML(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
