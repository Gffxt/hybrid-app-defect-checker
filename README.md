# 🔍 Hybrid App UI/UX Defect & Function Break Checker

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-16%2B-green.svg)](https://nodejs.org/)
[![Platform](https://img.shields.io/badge/Platform-Capacitor%20%7C%20Cordova%20%7C%20WebView%20%7C%20PWA-orange.svg)](#)

An automated static analysis and dynamic audit suite designed to detect **UI/UX layout collisions, overlapping elements, broken JavaScript bindings, missing DOM IDs, unhandled event functions, and device status bar clashes** in Hybrid Mobile Apps (Capacitor, Cordova, WebView, Jetpack Compose) and Web Apps.

---

## 🎯 The Problem This Tool Solves

Hybrid mobile apps and web apps frequently suffer from silent, catastrophic defects that traditional linters miss:

- **Floating navigation bars covering buttons or cards** at the bottom of the screen.
- **Top headers colliding with device notches, camera punch-holes, or status bars**.
- **`TypeError: Cannot read properties of null`** when `document.getElementById('...')` queries an element missing from the DOM.
- **Dead clicks** when inline event handlers (`onclick="startStream()"`) call functions that were renamed, misspelled, or never exported to `window`.
- **Z-Index conflicts** where background cards peek through modals or floating menus.
- **Missing local assets** (images, icons, fonts) resulting in broken `404` icons on mobile devices.

This tool automatically scans your codebase and outputs a detailed **console summary**, an **interactive Material Design 3 HTML dashboard**, and a **CI/CD JSON report** pinpointing the exact file and line number of every defect.

---

## 📋 Comprehensive Audit Modules

| Module | What It Audits | Defect Prevented |
| :--- | :--- | :--- |
| **1. UI/UX Overlap & Collisions** | Checks `.main-body` padding vs floating bottom nav height, verifies nav suppression during fullscreen video/manga views (`.nav-hidden`). | Bottom navigation blocking content, buttons, or video player controls. |
| **2. Status Bar & Notch Safety** | Scans for `env(safe-area-inset-top)` in headers and checks Android `setDecorFitsSystemWindows(window, true)`. | Header text and brand icons colliding with phone camera cutouts or status bar clock/battery. |
| **3. Z-Index Layering Hierarchy** | Verifies modals, drawers, and overlays have strictly higher `z-index` than sticky headers and floating bottom navigation. | Modals appearing underneath floating buttons or partial background bleed-through. |
| **4. JavaScript AST Syntax** | Validates every `.js` file via Node.js syntax parsing (`node -c`). | Catches unclosed brackets, syntax typos, and runtime parsing breaks before packaging. |
| **5. DOM ID Binding Scanner** | Cross-references every `document.getElementById('...')` call across all `.js` files against static and dynamic HTML templates. | Prevents `null.textContent` and `null.addEventListener` app crashes. |
| **6. Event Handler & Function Map** | Validates all HTML inline event handlers (`onclick`, `onchange`, `onsubmit`) against declared functions in JavaScript. | Dead buttons and missing action handlers. |
| **7. Navigation Route Integrity** | Scans dynamic route controllers (e.g. `navigateTo('...')`) and ensures matching `<section id="section-...">` elements exist. | Blank white screens when navigating between app tabs or pages. |
| **8. Static Asset Resolution** | Verifies all local `<img src>`, `<link href>`, and `<script src>` paths exist on disk. | Broken images, missing stylesheets, or missing script tags. |
| **9. CSS Design Tokens & Variables** | Checks that every `var(--custom-token)` is declared in `:root` or theme palettes. | Blank colors or broken styling due to undefined CSS tokens. |
| **10. Android & Compose Bridge** | Verifies `MainActivity`, Jetpack Compose shell, hardware `BackHandler`, and `AndroidManifest.xml` permissions. | Hardware back button crashing out of app; missing internet permissions. |

---

## 🚀 Quick Start Tutorial

### 1. Prerequisites

- **Python 3.8+** (Required)
- **Node.js 16+** (Recommended, used for JavaScript AST syntax checking)

### 2. Download or Clone the Repository

```bash
git clone https://github.com/Gffxt/hybrid-app-defect-checker.git
cd hybrid-app-defect-checker
chmod +x check_defects.sh check_defects.py
```

### 3. Run the Audit on Your Project

#### Option A: Run inside your project directory

Copy `check_defects.py` into your project's root folder and run:

```bash
python3 check_defects.py
```

Or run via the shell wrapper:

```bash
./check_defects.sh
```

#### Option B: Run remotely pointing to your project path

You can keep the tool anywhere and point it to any project directory using `--path`:

```bash
python3 /path/to/check_defects.py --path /path/to/my-capacitor-app
```

---

## ⚙️ CLI Options & Flags

```text
usage: check_defects.py [-h] [--path PATH] [--output-dir OUTPUT_DIR]
                        [--no-network] [--strict]

Hybrid & Web App Automated UI/UX Defect and Function Break Checker

options:
  -h, --help            Show this help message and exit
  --path PATH           Target project root directory (default: current directory)
  --output-dir OUTPUT_DIR
                        Directory to output report files (default: target project root)
  --no-network          Skip live network / API connectivity checks (offline mode)
  --strict              Fail (exit code 1) on warnings as well as critical defects
```

### Examples

```bash
# Run in strict mode for CI/CD pipelines (fails if warnings exist):
python3 check_defects.py --strict

# Run offline without testing live API endpoints:
python3 check_defects.py --no-network

# Specify custom output location for generated reports:
python3 check_defects.py --path ./my-app --output-dir ./audit-results
```

---

## 📊 Understanding the Reports

When the audit completes, it produces three levels of reporting:

### 1. Terminal Console Summary
Outputs color-coded feedback directly in your terminal:
- `✔ Checks Passed`: Functional tests that succeeded.
- `⚠ Warnings`: Potential risks (e.g. missing status bar insets or undeclared CSS variables).
- `✖ Critical Defects`: Actionable bugs (e.g. broken handlers, missing assets, content overlaps) with file paths, line numbers, and copy-paste fix recommendations.

### 2. Interactive Material Design 3 HTML Dashboard (`defect_report.html`)
Open `defect_report.html` in any browser to explore:
- High-level metric summary cards (Passed, Warnings, Defects).
- Color-coded defect breakdown cards.
- Direct code snippets and suggested fixes.

### 3. Machine-Readable JSON Report (`defect_report.json`)
A structured JSON file ideal for parsing in automated deployment scripts or custom dashboards:

```json
{
  "passed": [
    { "category": "UI/UX Overlap", "title": "Bottom Navigation Clearance Safe" }
  ],
  "warnings": [],
  "defects": []
}
```

---

## 🔄 Automatic Integration in Build Pipelines

### 1. In `package.json`

Add the audit tool to your project's npm scripts:

```json
{
  "scripts": {
    "audit": "python3 check_defects.py",
    "test": "python3 check_defects.py --strict",
    "build": "npx cap copy android && npm run audit"
  }
}
```

Now you can audit your app anytime with:

```bash
npm run audit
```

### 2. In Android / Release Build Scripts (`build_apk.sh`)

Ensure the defect checker runs after each build before distributing APKs:

```bash
#!/usr/bin/env bash
set -e

# ... [Your build & signing commands] ...

echo "🛠️ Running Automated UI/UX Defect & Function Break Checker..."
python3 check_defects.py

echo "🎉 Build Complete and Verified!"
```

### 3. In GitHub Actions CI/CD (`.github/workflows/audit.yml`)

Add automated pull request checks on GitHub:

```yaml
name: "UI/UX Defect & Function Audit"

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Run Defect Audit
        run: |
          chmod +x check_defects.sh
          ./check_defects.sh --no-network
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: defect-report
          path: defect_report.html
```

---

## 🤝 Contributing

Contributions are warmly welcome!
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/new-audit-module`).
3. Commit your changes (`git commit -m 'Add support for iOS safe area checks'`).
4. Push to the branch (`git push origin feature/new-audit-module`).
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - feel free to use and adapt it for personal and commercial projects.
