let originalText = "";
let redactedText = "";
let isShowingOriginal = false;
let lastEntities = [];
let requestStartTime = 0;
const sampleNotes = {
  "1": `Patient: John Smith
Date of Birth: 12/05/1985
MRN: MRN-100234
Phone: +1-555-123-4567
Email: john.smith@email.com
Address: 45 Oak Street, Boston MA 02101

Chief Complaint: Patient reports persistent chest pain for the last 3 days.
History: Diagnosed with Parkinson's disease in 2019.
Current Medications: Levodopa 100mg three times daily.
Attending Physician: Dr. Sarah Adams`,

  "2": `Prescription Record
Patient Name: Emily Johnson
Date of Birth: 03/22/1990
MRN: MRN-200456
Contact: emily.johnson@gmail.com | 617-555-8899

Prescribing Doctor: Dr. Michael Chen
License No: MD-78234
Date: 06/01/2026

Medication: Metformin 500mg
Dosage: Twice daily with meals
Refills: 3
Pharmacy: CVS Boston, 120 Tremont St`,

  "3": `Dear Dr. Williams,

I am writing to refer Mr. David Lee (DOB: 07/14/1975, MRN: MRN-300789).
Mr. Lee resides at 88 Pine Avenue, Chicago IL 60601.
He can be reached at david.lee@hospital.org or 312-555-6677.

Reason for Referral: Mr. Lee presents with symptoms consistent with
Type 2 Diabetes Mellitus. His HbA1c reading of 8.2% is above normal range.
He has no known drug allergies.

Please contact my office at 312-555-1100 for additional records.

Sincerely,
Dr. Rachel Torres
Chicago Medical Center`
};

document.addEventListener("DOMContentLoaded", function () {

  document.getElementById("inputText").addEventListener("input", function () {
    const length = this.value.length;
    const counter = document.getElementById("charCount");
    counter.textContent = length + " / 5000 characters";
    if (length > 4500) {
      counter.style.color = "#dc3545";  
    } else if (length > 4000) {
      counter.style.color = "#fd7e14";  
    } else {
      counter.style.color = "#6c757d";  
    }
  });

  document.getElementById("clearBtn").addEventListener("click", function () {
    document.getElementById("inputText").value = "";
    document.getElementById("charCount").textContent = "0 / 5000 characters";
    document.getElementById("charCount").style.color = "#6c757d";
    document.getElementById("resultCard").innerHTML =
      '<span class="text-muted" id="placeholderText">Results will appear here after you click <strong>Redact PHI</strong>.</span>';

    document.getElementById("resultActions").style.display = "none";
    document.getElementById("statsBar").style.display = "none";
    document.getElementById("entityBreakdown").style.display = "none";

    hideError();

    originalText = "";
    redactedText = "";
    isShowingOriginal = false;
    lastEntities = [];

    document.getElementById("restoreBtn").textContent = "Show Original";
  });

  document.getElementById("copyBtn").addEventListener("click", function () {
    const text = document.getElementById("resultCard").innerText;

    navigator.clipboard.writeText(text).then(function () {
      const btn = document.getElementById("copyBtn");
      btn.textContent = "Copied!";
      btn.classList.add("btn-success");
      btn.classList.remove("btn-outline-primary");

      setTimeout(function () {
        btn.textContent = "Copy Text";
        btn.classList.remove("btn-success");
        btn.classList.add("btn-outline-primary");
      }, 2000);
    }).catch(function () {
      showError("Could not copy to clipboard. Please select and copy manually.");
    });
  });

  document.getElementById("downloadBtn").addEventListener("click", function () {
    const text = document.getElementById("resultCard").innerText;
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "redacted_output.txt";
    document.body.appendChild(a);
    a.click();

    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  document.querySelectorAll(".sample-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const sampleKey = this.getAttribute("data-sample");
      document.getElementById("inputText").value = sampleNotes[sampleKey];

      const length = sampleNotes[sampleKey].length;
      document.getElementById("charCount").textContent = length + " / 5000 characters";
    });
  });

  document.getElementById("redactBtn").addEventListener("click", async function () {
    const inputText = document.getElementById("inputText").value.trim();

    if (inputText === "") {
      showError("Please enter some clinical text before clicking Redact PHI.");
      return;
    }

    if (inputText.length > 5000) {
      showError("Text is too long. Maximum is 5000 characters. Please shorten your input.");
      return;
    }

    hideError();

    originalText = inputText;
    isShowingOriginal = false;
    document.getElementById("restoreBtn").textContent = "Show Original";

    document.getElementById("loadingMsg").classList.add("show-flex");
    document.getElementById("redactBtn").disabled = true;
    document.getElementById("redactBtn").textContent = "Processing...";

    requestStartTime = Date.now();

    document.getElementById("resultCard").innerHTML =
      '<span class="text-muted">Detecting PHI entities...</span>';
    document.getElementById("resultActions").style.display = "none";
    document.getElementById("statsBar").style.display = "none";
    document.getElementById("entityBreakdown").style.display = "none";

    try {
      const response = await fetch("http://localhost:8000/redact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ text: inputText })
      });

      if (!response.ok) {
        throw new Error("Server returned status " + response.status);
      }

      const data = await response.json();

      redactedText = data.redacted_text;
      lastEntities = data.entities || [];

      renderRedactedHTML(redactedText, lastEntities);

      updateStatsBar(lastEntities);

      updateEntityBreakdown(lastEntities);

      document.getElementById("resultActions").classList.add("show-flex");

      const elapsed = ((Date.now() - requestStartTime) / 1000).toFixed(2);
      document.getElementById("processingTime").textContent = "(" + elapsed + "s)";

    } catch (error) {
      console.error("API Error:", error);

      document.getElementById("resultCard").innerHTML =
        '<span class="text-danger" style="font-size:13px;">' +
        '<strong>Connection Error:</strong> Could not reach the backend server. ' +
        'Make sure the FastAPI server (Member 1) is running on http://localhost:8000' +
        '</span>';

      showError("Backend not reachable. Start the FastAPI server with: uvicorn main:app --reload --port 8000");
    }

    document.getElementById("loadingMsg").classList.remove("show-flex");
    document.getElementById("redactBtn").disabled = false;
    document.getElementById("redactBtn").textContent = "Redact PHI";
  });

  document.getElementById("restoreBtn").addEventListener("click", async function () {
    if (isShowingOriginal) {
      renderRedactedHTML(redactedText, lastEntities);
      this.textContent = "Show Original";
      isShowingOriginal = false;
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ redacted_text: redactedText })
      });

      if (!response.ok) {
        throw new Error("Restore failed with status " + response.status);
      }

      const data = await response.json();

      document.getElementById("resultCard").innerText = data.original_text;

      this.textContent = "Show Redacted";
      isShowingOriginal = true;

    } catch (error) {
      console.error("Restore Error:", error);
      document.getElementById("resultCard").innerText = originalText;
      this.textContent = "Show Redacted";
      isShowingOriginal = true;
    }
  });

});

function renderRedactedHTML(text, entities) {
  if (!entities || entities.length === 0) {
    document.getElementById("resultCard").innerText = text;
    return;
  }

  let displayHTML = escapeHTML(text);

  entities.forEach(function (entity) {
    const placeholder = entity.replacement;
    const label = entity.label;

    const badge =
      '<span class="redacted-token entity-' + label + '" ' +
      'title="Original: ' + escapeHTML(entity.text || '') + '">' +
      '[' + label + ']' +
      '</span>';

    const escapedPlaceholder = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    displayHTML = displayHTML.replace(new RegExp(escapedPlaceholder, 'g'), badge);
  });

  document.getElementById("resultCard").innerHTML = displayHTML;
}

function updateStatsBar(entities) {
  const total = entities ? entities.length : 0;
  document.getElementById("totalCount").textContent = total;
  document.getElementById("statsBar").classList.add("show-block");
}

function updateEntityBreakdown(entities) {
  if (!entities || entities.length === 0) return;

  const counts = {};
  entities.forEach(function (entity) {
    const label = entity.label;
    counts[label] = (counts[label] || 0) + 1;
  });

  let html = "";
  for (const label in counts) {
    html +=
      '<span class="redacted-token entity-' + label + '">' +
      label + ': ' + counts[label] +
      '</span>';
  }

  document.getElementById("entityCounts").innerHTML = html;
  document.getElementById("entityBreakdown").style.display = "block";
}

function showError(message) {
  const banner = document.getElementById("errorBanner");
  document.getElementById("errorMessage").textContent = message;
  banner.classList.add("show-block");
}

function hideError() {
  document.getElementById("errorBanner").classList.remove("show-block");
  document.getElementById("errorBanner").style.display = "none";
}

function escapeHTML(text) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
