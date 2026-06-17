# Member 4 — Frontend & Documentation
## PHI/PII Redaction Pipeline — Infotact Cybersecurity Internship

This README covers **only Member 4's part** of the project: the frontend (what the
user sees and clicks) and the documentation. It explains what each file does and
how to actually work with them, step by step.

---

## My Files

| File | What it is |
|------|-----------|
| `index.html` | The webpage itself — every box, button, and panel you see on screen |
| `style.css` | All the colors, spacing, fonts, and animations |
| `script.js` | All the logic — what happens when you click a button, how it talks to the backend |
| `architecture.html` | A visual diagram of how the whole system fits together |
| `README.md` | This file |
| `API_DOCS.md` | Explains exactly what data the backend expects and sends back |
| `COMPONENTS.md` | Explains each UI piece individually, for reference |

You do not need to touch any other team member's files. Member 1 owns the FastAPI
backend code, Member 2 owns the detection logic, Member 3 owns Redis — your three
files (`index.html`, `style.css`, `script.js`) are the entire frontend.

---

## How These Three Files Connect

```
index.html  →  loads style.css  (for colors/layout)
index.html  →  loads script.js  (for button clicks and API calls)
script.js   →  reads/changes elements inside index.html using their "id"
script.js   →  sends data to the backend, which Member 1 builds
```

Nothing needs to be installed or compiled. You write HTML/CSS/JS, save the file,
and refresh the browser to see the change. There is no build step.

---

## How to Open and Run This Project

1. Download or clone this folder onto your computer.
2. Open the folder in **VS Code** (File → Open Folder).
3. Double-click `index.html` in your file explorer — it opens directly in your browser.
4. To see a change you made: save the file in VS Code (`Ctrl+S`), then go to the
   browser tab and press `F5` to refresh.

That's the entire workflow. No servers, no `npm install`, nothing — for the frontend alone.

The **Redact** and **Restore** buttons need Member 1's backend running on
`http://localhost:8000`. Until that's ready, you can still build and test
everything else (the layout, the buttons, the styling).

---

## How to Test Without the Backend Ready

Open the browser, press `F12`, click the **Console** tab. If the backend isn't
running, clicking "Redact PHI" will show a friendly error message in the result
card telling you the backend isn't reachable — that's expected and correct
behavior, not a bug.

To see what the UI looks like *as if* it worked, you can temporarily test the
display function directly in the Console tab:

```javascript
renderRedactedHTML(
  "Patient PATIENT_001, phone PHONE_001",
  [
    { text: "John Smith", label: "NAME", replacement: "PATIENT_001" },
    { text: "555-1234", label: "PHONE", replacement: "PHONE_001" }
  ]
);
```

Paste that into the Console and press Enter — you'll see the colored badges
appear in the result card.

---

## Making Changes

**To change a color:** open `style.css`, find the entity class (e.g. `.entity-NAME`),
change the `background-color` / `border-color` / `color` values, save, refresh browser.

**To change text on the page:** open `index.html`, find the text you want to change
(use `Ctrl+F` to search), edit it, save, refresh.

**To change what happens on a button click:** open `script.js`, find the relevant
`addEventListener` block (e.g. search for `redactBtn`), edit the code inside the
`function() { ... }`, save, refresh.

**Always test after every change** — refresh the browser and click around to make
sure nothing broke.

---

## Daily Workflow (Do This Every Day)

1. Open VS Code, open the project folder.
2. Make your change for the day (see `DAILY_COMMIT_GUIDE.md` for what each day covers).
3. Save all files (`Ctrl+S`).
4. Test in browser — refresh and click around.
5. Open Terminal in VS Code (View → Terminal).
6. Run:
   ```bash
   git add .
   git commit -m "paste today's commit message from DAILY_COMMIT_GUIDE.md"
   git push origin member-4-frontend
   ```
7. Confirm on github.com that your commit shows up.

Do this **every single day**, even on days with small changes. Missing a day during
the Final Review window (the last 20 days) can cause the project to be marked incomplete.

---

## If Something Breaks

- **Page looks broken / blank:** press `F12` → **Console** tab → look for red error text. It usually tells you exactly which file and line is wrong.
- **Styles not applying:** make sure `style.css` is saved and that `index.html` still has `<link rel="stylesheet" href="style.css" />` in the `<head>`.
- **Buttons not responding:** make sure `script.js` is linked at the bottom of `index.html`, just before `</body>`.
- **API errors:** check that Member 1's backend is actually running, and that the URL in `script.js` (`API_BASE_URL`) matches the address it's running on.

---

## Where to Look for More Detail

- Want to know exactly what data goes to/from the backend? → `API_DOCS.md`
- Want to know what a specific button or panel does and which file it's in? → `COMPONENTS.md`

---

*Member 4 — Frontend & Documentation. Infotact Solutions Cybersecurity Internship, 2026.*

