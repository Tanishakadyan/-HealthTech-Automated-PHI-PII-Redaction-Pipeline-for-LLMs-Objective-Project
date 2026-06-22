/*
  ============================================================
  FILE: script.js
  MEMBER 4: Frontend + Documentation
  PROJECT: PHI/PII Redaction Pipeline
  ============================================================

  DAY 5  → File created, DOMContentLoaded wrapper, Clear button
  DAY 5  → Copy button logic added
  DAY 5  → Restore/Show Original toggle function
  DAY 7  → Cleaned up and reviewed for Week 1 commit
  DAY 8  → Redact button click listener + fetch API call to /redact
  DAY 9  → renderRedactedHTML() function with colored badges
  DAY 10 → Full restore button logic calling /restore endpoint
  DAY 11 → showError() / hideError() functions, input validation
  DAY 12 → updateEntityCounts() for stats bar
  DAY 14 → processingTime display added
  DAY 15 → updateEntityBreakdown() per-entity count function
  DAY 16 → Download .txt file button logic
  DAY 17 → Character counter on textarea input event
  DAY 18 → Sample clinical note data + quick-fill button logic
  DAY 19 → Code reviewed, comments improved
  DAY 20 → Final cleanup, all edge cases handled
  ============================================================
*/


/* ============================================================
   DAY 5: GLOBAL STATE VARIABLES
   These store data across button clicks.
   "let" means the value can change later.
   ============================================================ */

// DAY 5: Stores the original text before redaction (for restore)
let originalText = "";

// DAY 5: Stores the redacted text returned from API
let redactedText = "";

// DAY 5: Tracks whether we are currently showing original or redacted
let isShowingOriginal = false;

// DAY 9: Stores the list of entities returned by API
// Example: [ {text:"John Smith", label:"NAME", replacement:"PATIENT_001"} ]
let lastEntities = [];

// DAY 14: Tracks when the request started (for timing display)
let requestStartTime = 0;


/* ============================================================
   DAY 18: SAMPLE CLINICAL NOTES
   Three fake patient notes used for demo and testing.
   IMPORTANT: All patient data here is COMPLETELY MADE UP.
   Never use real patient data in code or GitHub.
   ============================================================ */

// DAY 18: Object with 3 sample notes, accessed by key "1", "2", "3"
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


/* ============================================================
   DAY 5: DOM CONTENT LOADED
   Everything inside this block runs AFTER the page HTML is ready.
   This prevents errors from trying to access elements that don't exist yet.
   ============================================================ */
document.addEventListener("DOMContentLoaded", function () {


  /* ============================================================
     DAY 17: CHARACTER COUNTER
     Shows how many characters are typed vs the 5000 limit.
     Updates every time the user types in the textarea.
     ============================================================ */
  // DAY 17: "input" event fires every time text changes
  document.getElementById("inputText").addEventListener("input", function () {
    const length = this.value.length;
    const counter = document.getElementById("charCount");
    counter.textContent = length + " / 5000 characters";

    // DAY 17: Turn counter red when approaching the limit
    if (length > 4500) {
      counter.style.color = "#dc3545";  // Bootstrap danger red
    } else if (length > 4000) {
      counter.style.color = "#fd7e14";  // Bootstrap warning orange
    } else {
      counter.style.color = "#6c757d";  // Default grey
    }
  });


  /* ============================================================
     DAY 5: CLEAR BUTTON
     Resets everything: textarea, result card, all state variables.
     ============================================================ */
  document.getElementById("clearBtn").addEventListener("click", function () {

    // DAY 5: Clear the textarea
    document.getElementById("inputText").value = "";

    // DAY 5: Reset character counter
    document.getElementById("charCount").textContent = "0 / 5000 characters";
    document.getElementById("charCount").style.color = "#6c757d";

    // DAY 5: Reset result card to placeholder text
    document.getElementById("resultCard").innerHTML =
      '<span class="text-muted" id="placeholderText">Results will appear here after you click <strong>Redact PHI</strong>.</span>';

    // DAY 5: Hide the action buttons and stats
    document.getElementById("resultActions").style.display = "none";
    document.getElementById("statsBar").style.display = "none";
    document.getElementById("entityBreakdown").style.display = "none";

    // DAY 11: Hide any error banners
    hideError();

    // DAY 5: Reset all state variables
    originalText = "";
    redactedText = "";
    isShowingOriginal = false;
    lastEntities = [];

    // DAY 5: Reset the restore button label
    document.getElementById("restoreBtn").textContent = "Show Original";
  });


  /* ============================================================
     DAY 5: COPY BUTTON
     Copies the current text in the result card to clipboard.
     ============================================================ */
  document.getElementById("copyBtn").addEventListener("click", function () {

    // DAY 5: Get plain text (innerText strips HTML tags)
    const text = document.getElementById("resultCard").innerText;

    // DAY 5: Browser clipboard API
    navigator.clipboard.writeText(text).then(function () {
      // DAY 5: Briefly change button text to confirm
      const btn = document.getElementById("copyBtn");
      btn.textContent = "Copied!";
      btn.classList.add("btn-success");
      btn.classList.remove("btn-outline-primary");

      // DAY 5: Reset button after 2 seconds
      setTimeout(function () {
        btn.textContent = "Copy Text";
        btn.classList.remove("btn-success");
        btn.classList.add("btn-outline-primary");
      }, 2000);
    }).catch(function () {
      // DAY 11: If clipboard fails (some browsers block it)
      showError("Could not copy to clipboard. Please select and copy manually.");
    });
  });


  /* ============================================================
     DAY 16: DOWNLOAD BUTTON
     Creates a .txt file from the redacted result and downloads it.
     No server needed — this is done entirely in the browser.
     ============================================================ */
  document.getElementById("downloadBtn").addEventListener("click", function () {

    // DAY 16: Get the plain text content (strips HTML badges)
    const text = document.getElementById("resultCard").innerText;

    // DAY 16: Create a Blob (binary large object) from the text
    // "text/plain" tells the browser this is a plain text file
    const blob = new Blob([text], { type: "text/plain" });

    // DAY 16: Create a temporary URL pointing to the blob
    const url = URL.createObjectURL(blob);

    // DAY 16: Create a hidden <a> link and click it programmatically
    const a = document.createElement("a");
    a.href = url;
    a.download = "redacted_output.txt";  // filename the user sees
    document.body.appendChild(a);
    a.click();

    // DAY 16: Clean up — remove the temporary URL and link
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });


  /* ============================================================
     DAY 18: SAMPLE QUICK-FILL BUTTONS
     When user clicks "Sample 1", "Sample 2", or "Sample 3",
     the corresponding clinical note is loaded into the textarea.
     ============================================================ */
  // DAY 18: querySelectorAll gets ALL buttons with class sample-btn
  document.querySelectorAll(".sample-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {

      // DAY 18: data-sample attribute on the button tells us which sample
      const sampleKey = this.getAttribute("data-sample");

      // DAY 18: Fill textarea with the sample note text
      document.getElementById("inputText").value = sampleNotes[sampleKey];

      // DAY 18: Update character counter to match new text
      const length = sampleNotes[sampleKey].length;
      document.getElementById("charCount").textContent = length + " / 5000 characters";
    });
  });


  /* ============================================================
     DAY 8: REDACT BUTTON
     This is the main action. When clicked:
     1. Reads textarea text
     2. Validates it
     3. Sends it to the FastAPI /redact endpoint
     4. Displays the result
     ============================================================ */
  // DAY 8: "async" because we need to wait for the API response
  document.getElementById("redactBtn").addEventListener("click", async function () {

    // DAY 8: Read what the user typed in the textarea
    const inputText = document.getElementById("inputText").value.trim();

    // DAY 11: VALIDATION — don't send empty text
    if (inputText === "") {
      showError("Please enter some clinical text before clicking Redact PHI.");
      return;  // "return" stops the function here — nothing below runs
    }

    // DAY 11: VALIDATION — don't allow text over 5000 characters
    if (inputText.length > 5000) {
      showError("Text is too long. Maximum is 5000 characters. Please shorten your input.");
      return;
    }

    // DAY 11: Hide any previous error messages
    hideError();

    // DAY 5: Save the original text so Restore button works
    originalText = inputText;
    isShowingOriginal = false;
    document.getElementById("restoreBtn").textContent = "Show Original";

    // DAY 8: SHOW LOADING STATE
    // Show spinner, disable button so user can't click again while waiting
    document.getElementById("loadingMsg").classList.add("show-flex");
    document.getElementById("redactBtn").disabled = true;
    document.getElementById("redactBtn").textContent = "Processing...";

    // DAY 14: Record when we started (for displaying processing time)
    requestStartTime = Date.now();

    // DAY 8: Reset result area while loading
    document.getElementById("resultCard").innerHTML =
      '<span class="text-muted">Detecting PHI entities...</span>';
    document.getElementById("resultActions").style.display = "none";
    document.getElementById("statsBar").style.display = "none";
    document.getElementById("entityBreakdown").style.display = "none";

    try {
      /* ============================================================
         DAY 8: FETCH API CALL TO BACKEND
         fetch() sends an HTTP POST request to the FastAPI server.
         "await" pauses this function until the server responds.

         The backend (Member 1) runs at http://localhost:8000
         The /redact endpoint (Member 1) accepts JSON with "text" field
         ============================================================ */
      const response = await fetch("http://localhost:8000/redact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"   // tells server we're sending JSON
        },
        body: JSON.stringify({ text: inputText })  // convert JS object to JSON string
      });

      // DAY 8: Check if server returned an error status (e.g. 422, 500)
      if (!response.ok) {
        throw new Error("Server returned status " + response.status);
      }

      // DAY 8: Parse the JSON response into a JavaScript object
      const data = await response.json();

      /*
        DAY 8: Expected response format from Member 1's API:
        {
          "redacted_text": "Patient PATIENT_001, DOB DATE_001...",
          "entities": [
            { "text": "John Smith", "label": "NAME", "replacement": "PATIENT_001" },
            { "text": "12/05/1985", "label": "DATE", "replacement": "DATE_001" }
          ]
        }
      */

      // DAY 9: Store entities and redacted text in global variables
      redactedText = data.redacted_text;
      lastEntities = data.entities || [];

      // DAY 9: Render the redacted text with colored badges
      renderRedactedHTML(redactedText, lastEntities);

      // DAY 12: Update the stats bar ("X entities detected")
      updateStatsBar(lastEntities);

      // DAY 15: Show per-entity breakdown (NAME: 2, PHONE: 1, etc.)
      updateEntityBreakdown(lastEntities);

      // DAY 5: Show the action buttons now that we have a result
      document.getElementById("resultActions").classList.add("show-flex");

      // DAY 14: Show processing time
      const elapsed = ((Date.now() - requestStartTime) / 1000).toFixed(2);
      document.getElementById("processingTime").textContent = "(" + elapsed + "s)";

    } catch (error) {
      /* ============================================================
         DAY 11: ERROR HANDLING
         If the fetch fails (server not running, network error, etc.)
         show a friendly message instead of crashing.
         ============================================================ */
      console.error("API Error:", error);  // DAY 11: Log to browser console (F12)

      document.getElementById("resultCard").innerHTML =
        '<span class="text-danger" style="font-size:13px;">' +
        '<strong>Connection Error:</strong> Could not reach the backend server. ' +
        'Make sure the FastAPI server (Member 1) is running on http://localhost:8000' +
        '</span>';

      showError("Backend not reachable. Start the FastAPI server with: uvicorn main:app --reload --port 8000");
    }

    // DAY 8: HIDE LOADING STATE — runs whether success or error
    document.getElementById("loadingMsg").classList.remove("show-flex");
    document.getElementById("redactBtn").disabled = false;
    document.getElementById("redactBtn").textContent = "Redact PHI";
  });


  /* ============================================================
     DAY 10: RESTORE BUTTON
     Toggles between showing the redacted text and the original text.
     If we haven't restored yet → call /restore API to get original back.
     If already showing original → switch back to redacted view.
     ============================================================ */
  document.getElementById("restoreBtn").addEventListener("click", async function () {

    // DAY 10: If currently showing original → switch back to redacted
    if (isShowingOriginal) {
      renderRedactedHTML(redactedText, lastEntities);
      this.textContent = "Show Original";
      isShowingOriginal = false;
      return;
    }

    // DAY 10: Otherwise → call the /restore API endpoint
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

      // DAY 10: Show original plain text (no HTML needed — just text)
      document.getElementById("resultCard").innerText = data.original_text;

      // DAY 10: Update button label
      this.textContent = "Show Redacted";
      isShowingOriginal = true;

    } catch (error) {
      // DAY 11: If restore fails, show the stored original text as fallback
      console.error("Restore Error:", error);
      document.getElementById("resultCard").innerText = originalText;
      this.textContent = "Show Redacted";
      isShowingOriginal = true;
    }
  });


});  // end DOMContentLoaded


/* ============================================================
   DAY 9: renderRedactedHTML()
   Takes the redacted text and entity list from the API.
   Replaces each placeholder token with a colored HTML badge.

   Example:
     Input text: "Patient PATIENT_001 called PHONE_001"
     Entities: [{replacement:"PATIENT_001", label:"NAME"}, {replacement:"PHONE_001", label:"PHONE"}]
     Output HTML: "Patient <span class='entity-NAME'>...</span> called <span class='entity-PHONE'>...</span>"
   ============================================================ */
function renderRedactedHTML(text, entities) {

  // DAY 9: If no entities, just show plain text
  if (!entities || entities.length === 0) {
    document.getElementById("resultCard").innerText = text;
    return;
  }

  // DAY 9: Start with the redacted text as plain text
  // We will replace placeholders with HTML badges
  let displayHTML = escapeHTML(text);  // DAY 20: escape HTML to prevent XSS

  // DAY 9: Loop through each entity and build its colored badge
  entities.forEach(function (entity) {
    const placeholder = entity.replacement;   // e.g. "PATIENT_001"
    const label = entity.label;               // e.g. "NAME"

    // DAY 9: Build the badge HTML
    // We show the label type and the placeholder token
    const badge =
      '<span class="redacted-token entity-' + label + '" ' +
      'title="Original: ' + escapeHTML(entity.text || '') + '">' +
      '[' + label + ']' +
      '</span>';

    // DAY 9: Replace all occurrences of this placeholder with the badge
    // We use a RegExp with the 'g' flag to replace ALL occurrences
    const escapedPlaceholder = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    displayHTML = displayHTML.replace(new RegExp(escapedPlaceholder, 'g'), badge);
  });

  // DAY 9: Write the HTML into the result card
  document.getElementById("resultCard").innerHTML = displayHTML;
}


/* ============================================================
   DAY 12: updateStatsBar()
   Updates the "X PHI entities detected" bar above the result.
   ============================================================ */
function updateStatsBar(entities) {

  // DAY 12: Count total entities
  const total = entities ? entities.length : 0;

  // DAY 12: Set the count in the stats bar span
  document.getElementById("totalCount").textContent = total;

  // DAY 12: Show the stats bar
  document.getElementById("statsBar").classList.add("show-block");
}


/* ============================================================
   DAY 15: updateEntityBreakdown()
   Shows a count for each entity type found.
   Example: NAME: 2  |  PHONE: 1  |  EMAIL: 1
   ============================================================ */
function updateEntityBreakdown(entities) {

  if (!entities || entities.length === 0) return;

  // DAY 15: Count how many of each type
  const counts = {};
  entities.forEach(function (entity) {
    const label = entity.label;
    counts[label] = (counts[label] || 0) + 1;
  });

  // DAY 15: Build the HTML for the breakdown badges
  let html = "";
  for (const label in counts) {
    html +=
      '<span class="redacted-token entity-' + label + '">' +
      label + ': ' + counts[label] +
      '</span>';
  }

  // DAY 15: Insert into the breakdown div and show it
  document.getElementById("entityCounts").innerHTML = html;
  document.getElementById("entityBreakdown").style.display = "block";
}


/* ============================================================
   DAY 11: showError() and hideError()
   Shows and hides the red error banner at the top of the page.
   ============================================================ */

// DAY 11: Show error banner with a custom message
function showError(message) {
  const banner = document.getElementById("errorBanner");
  document.getElementById("errorMessage").textContent = message;
  banner.classList.add("show-block");
}

// DAY 11: Hide error banner (called by Clear button and X on banner)
function hideError() {
  document.getElementById("errorBanner").classList.remove("show-block");
  document.getElementById("errorBanner").style.display = "none";
}


/* ============================================================
   DAY 20: escapeHTML()
   Safety function — converts dangerous characters in text
   so they cannot be executed as HTML code.
   This prevents XSS (Cross-Site Scripting) attacks.
   ============================================================ */
function escapeHTML(text) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
