#!/usr/bin/env python3
"""
==============================================================================
Hybrid & Web App UI/UX Defect & Functional Break Checker Tool
==============================================================================
Author: Pixi (Gffxt)
Repository: https://github.com/Gffxt/hybrid-app-defect-checker
License: MIT

Automated static analysis and dynamic audit suite for:
  - Hybrid Mobile Apps (Capacitor, Cordova, WebView, Jetpack Compose)
  - Progressive Web Apps (PWA) & Single Page Applications (SPA)
==============================================================================
"""

import os
import sys
import re
import json
import argparse
import subprocess
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

# ANSI Terminal Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class DefectReport:
    def __init__(self, root_dir, output_dir=None):
        self.root_dir = Path(root_dir).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else self.root_dir
        self.defects = []
        self.warnings = []
        self.passed_checks = []

    def add_defect(self, category, title, description, file_path=None, line=None, recommendation=None):
        self.defects.append({
            'severity': 'CRITICAL',
            'category': category,
            'title': title,
            'description': description,
            'file': str(file_path) if file_path else None,
            'line': line,
            'recommendation': recommendation
        })

    def add_warning(self, category, title, description, file_path=None, line=None, recommendation=None):
        self.warnings.append({
            'severity': 'WARNING',
            'category': category,
            'title': title,
            'description': description,
            'file': str(file_path) if file_path else None,
            'line': line,
            'recommendation': recommendation
        })

    def add_pass(self, category, title, detail=""):
        self.passed_checks.append({
            'category': category,
            'title': title,
            'detail': detail
        })


# HTML Parser to extract IDs, event handlers, assets, sections
class DOMExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.id_locations = {}
        self.event_handlers = []
        self.asset_references = []
        self.sections = set()
        self.nav_targets = set()

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        line = self.getpos()[0]

        # Extract IDs
        if 'id' in attrs_dict:
            elem_id = attrs_dict['id'].strip()
            self.ids.add(elem_id)
            self.id_locations[elem_id] = line
            if tag == 'section' and elem_id.startswith('section-'):
                self.sections.add(elem_id.replace('section-', ''))

        # Extract data-target (navigation links)
        if 'data-target' in attrs_dict:
            self.nav_targets.add(attrs_dict['data-target'])

        # Extract inline event handlers
        for attr, val in attrs:
            if attr.startswith('on') and val:
                self.event_handlers.append({
                    'tag': tag,
                    'event': attr,
                    'code': val,
                    'line': line
                })

        # Extract asset links
        if tag in ('img', 'video', 'audio', 'source') and 'src' in attrs_dict:
            self.asset_references.append({'src': attrs_dict['src'], 'tag': tag, 'line': line})
        elif tag == 'link' and attrs_dict.get('rel') == 'stylesheet' and 'href' in attrs_dict:
            self.asset_references.append({'src': attrs_dict['href'], 'tag': tag, 'line': line})
        elif tag == 'script' and 'src' in attrs_dict:
            self.asset_references.append({'src': attrs_dict['src'], 'tag': tag, 'line': line})


# ==============================================================================
# AUDIT SUITE IMPLEMENTATION
# ==============================================================================
class AuditSuite:
    def __init__(self, root_dir, output_dir=None):
        self.root = Path(root_dir).resolve()
        self.report = DefectReport(self.root, output_dir)
        
        # Locate web root (support www/, dist/, or root)
        if (self.root / 'www').is_dir():
            self.www = self.root / 'www'
        elif (self.root / 'dist').is_dir() and (self.root / 'dist/index.html').exists():
            self.www = self.root / 'dist'
        else:
            self.www = self.root

        self.android = self.root / 'android'

    def run_all(self, check_network=True):
        print(f"\n{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════════{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN} 🔍 HYBRID APP UI/UX DEFECT & FUNCTION BREAK CHECKER{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN} Target Directory: {self.root}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN} Web Assets Directory: {self.www}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════════{Colors.RESET}\n")

        # 1. Parse DOM
        index_html_path = self.www / 'index.html'
        if not index_html_path.exists():
            # Try searching anywhere in root
            found = list(self.root.rglob('index.html'))
            if found:
                index_html_path = found[0]
                self.www = index_html_path.parent
            else:
                self.report.add_defect('Filesystem', 'Missing index.html', 'Could not locate index.html in target project directory.', self.root)
                return self.report

        html_content = index_html_path.read_text(encoding='utf-8', errors='ignore')
        parser = DOMExtractor()
        parser.feed(html_content)

        # Execute check modules
        self.check_javascript_syntax_integrity()
        self.check_ui_ux_layout(parser, html_content)
        self.check_dom_binding_and_js_calls(parser)
        self.check_inline_event_handlers(parser)
        self.check_navigation_routes(parser)
        self.check_static_asset_references(parser)
        self.check_css_variables_and_conflicts()
        self.check_native_android_compose_bridge()

        if check_network:
            self.check_critical_api_endpoints()

        return self.report

    # --------------------------------------------------------------------------
    # Check 1: JavaScript Syntax & Compilation Break Scanner
    # --------------------------------------------------------------------------
    def check_javascript_syntax_integrity(self):
        print(f"{Colors.BOLD}[1/8] Validating JavaScript Syntax with Node.js AST Parser...{Colors.RESET}")
        js_files = list(self.www.glob('*.js'))
        if not js_files:
            js_files = list(self.www.glob('**/*.js'))

        tested = 0
        for js_file in js_files:
            if any(x in js_file.name for x in ('min.js', 'vendor', 'node_modules', 'capacitor.js', 'cordova.js')):
                continue
            tested += 1
            try:
                proc = subprocess.run(['node', '-c', str(js_file)], capture_output=True, text=True, timeout=6)
                if proc.returncode == 0:
                    self.report.add_pass('JS Syntax', f"{js_file.name} Syntax Clean", "0 syntax/parse errors")
                else:
                    self.report.add_defect('JS Syntax Break', f"Syntax Error in {js_file.name}", proc.stderr.strip(), js_file)
            except FileNotFoundError:
                # node not installed
                self.report.add_warning('Environment', 'Node.js Not Found', 'Install node to enable automated AST syntax checks.')
                break
            except Exception as e:
                self.report.add_warning('JS Audit Warning', f"Could not audit {js_file.name}", str(e))

    # --------------------------------------------------------------------------
    # Check 2: UI/UX Layout, Overlaps, Z-Index, and Screen Space
    # --------------------------------------------------------------------------
    def check_ui_ux_layout(self, parser, html_content):
        print(f"{Colors.BOLD}[2/8] Scanning UI/UX Layout & Overlap Defects...{Colors.RESET}")
        css_files = list(self.www.glob('*.css')) + list(self.www.glob('**/*.css'))
        css_content = ""
        for cf in css_files:
            if 'node_modules' not in str(cf):
                css_content += "\n" + cf.read_text(encoding='utf-8', errors='ignore')

        # Check bottom navigation padding clearance
        if any(x in css_content for x in ('.mobile-bottom-nav', '.miku-bottom-nav', '.bottom-nav', '.tab-bar')):
            has_sufficient_bottom_padding = False
            for match in re.finditer(r'(?:\.main-body|main|#main-content|\.content-container)\s*\{([^}]+)\}', css_content):
                body_block = match.group(1)
                if 'padding-bottom' in body_block:
                    if any(x in body_block for x in ('80px', '85px', '90px', '96px', '100px', 'safe-area-inset-bottom')):
                        has_sufficient_bottom_padding = True
                        break

            if has_sufficient_bottom_padding:
                self.report.add_pass('UI/UX Overlap', 'Bottom Navigation Clearance Safe',
                                     'Main scroll container includes bottom padding avoiding fixed nav collision.')
            else:
                self.report.add_defect('UI/UX Overlap', 'Content Overlapped by Bottom Nav',
                                       'Main content area has insufficient padding-bottom (< 85px). Bottom cards and buttons will be blocked by fixed bottom nav.',
                                       recommendation='Add .main-body { padding-bottom: calc(96px + env(safe-area-inset-bottom, 20px)) !important; }')

        # Check suppression of bottom bar during immersive views (player / reader)
        if any(x in css_content for x in ('.mobile-bottom-nav', '.bottom-nav')):
            if any(x in css_content for x in ('.nav-hidden', 'body.in-player', 'body.in-reader')):
                self.report.add_pass('UI/UX Cleanliness', 'Immersive View Navigation Suppression',
                                     'Bottom navigation hides during video playback or fullscreen reader views.')
            else:
                self.report.add_warning('UI/UX Defect Risk', 'Bottom Bar Visible in Fullscreen Views',
                                        'Ensure bottom navigation is suppressed during video streaming or reader views to prevent blocking controls.')

        # Check Z-Index Layering
        z_overlays = [int(m.group(1)) for m in re.finditer(r'(?:modal|overlay|drawer|dialog|popup)[^{]*\{[^}]*z-index:\s*(\d+)', css_content, re.IGNORECASE)]
        z_bars = [int(m.group(1)) for m in re.finditer(r'(?:bottom-nav|topbar|navbar|header)[^{]*\{[^}]*z-index:\s*(\d+)', css_content, re.IGNORECASE)]
        
        if z_overlays and z_bars:
            max_bar = max(z_bars)
            min_overlay = min(z_overlays)
            if min_overlay >= max_bar:
                self.report.add_pass('UI/UX Z-Index', 'Modal & Overlay Layering Hierarchy Clean',
                                     f'Overlay z-index ({min_overlay}) properly exceeds navigation bar z-index ({max_bar}).')
            else:
                self.report.add_warning('UI/UX Z-Index', 'Potential Modal Layer Collision',
                                        f'Found overlay with z-index ({min_overlay}) lower than or equal to navigation bar ({max_bar}).')

        # Check Mobile Header Safe Area Insets
        if 'safe-area-inset-top' in css_content:
            self.report.add_pass('UI/UX Status Bar', 'Device Notch & Status Bar Safe Area Active',
                                 'Header styles respect env(safe-area-inset-top) for camera notches and status bars.')
        else:
            self.report.add_warning('UI/UX Status Bar', 'Missing Status Bar Safe Area Inset',
                                    'Top header does not declare padding-top: env(safe-area-inset-top). May clash with device status bar on edge-to-edge screens.')

    # --------------------------------------------------------------------------
    # Check 3: DOM ID Bindings & JS Null References
    # --------------------------------------------------------------------------
    def check_dom_binding_and_js_calls(self, parser):
        print(f"{Colors.BOLD}[3/8] Scanning DOM Element Bindings & JavaScript Bindings...{Colors.RESET}")
        js_files = list(self.www.glob('*.js')) + list(self.www.glob('**/*.js'))
        dom_ids = set(parser.ids)

        # Detect dynamically created IDs in JS files
        for js_path in js_files:
            if any(x in js_path.name for x in ('min.js', 'vendor', 'node_modules')):
                continue
            code = js_path.read_text(encoding='utf-8', errors='ignore')
            for m in re.finditer(r'id=[\'"]([a-zA-Z0-9_\-]+)[\'"]', code):
                dom_ids.add(m.group(1))
            for m in re.finditer(r'id:\s*[\'"]([a-zA-Z0-9_\-]+)[\'"]', code):
                dom_ids.add(m.group(1))

        missing_bindings = []
        for js_path in js_files:
            if any(x in js_path.name for x in ('min.js', 'vendor', 'node_modules', 'capacitor.js', 'cordova.js')):
                continue
            code = js_path.read_text(encoding='utf-8', errors='ignore')
            for line_idx, line in enumerate(code.splitlines(), start=1):
                matches = re.finditer(r'document\.getElementById\s*\(\s*[\'"]([a-zA-Z0-9_\-]+)[\'"]\s*\)', line)
                for m in matches:
                    elem_id = m.group(1)
                    if elem_id not in dom_ids:
                        if not any(k in elem_id for k in ('preset-', 'modal-', 'ep-', 'item-', 'player-embed', 'sub-', 'card-', 'chapter-', 'page-')):
                            missing_bindings.append({
                                'id': elem_id,
                                'file': js_path.name,
                                'line': line_idx,
                                'source_line': line.strip()
                            })

        if not missing_bindings:
            self.report.add_pass('Functional Binding', 'All DOM Element IDs Validated',
                                 f'Verified {len(dom_ids)} HTML and dynamically injected IDs across all JS files.')
        else:
            seen = set()
            for b in missing_bindings:
                key = (b['id'], b['file'])
                if key not in seen:
                    seen.add(key)
                    self.report.add_warning(
                        'DOM Binding Risk',
                        f"Unmatched document.getElementById('{b['id']}')",
                        f"File {b['file']}:{b['line']} queries '#{b['id']}' which was not found in static or injected templates.",
                        self.www / b['file'],
                        line=b['line']
                    )

    # --------------------------------------------------------------------------
    # Check 4: Inline HTML Event Handlers Integrity
    # --------------------------------------------------------------------------
    def check_inline_event_handlers(self, parser):
        print(f"{Colors.BOLD}[4/8] Verifying HTML Event Handlers & Function Existence...{Colors.RESET}")
        combined_js = ""
        for js_path in self.www.glob('*.js'):
            if 'min.js' not in js_path.name:
                combined_js += "\n" + js_path.read_text(encoding='utf-8', errors='ignore')

        reserved_keywords = {
            'if', 'else', 'for', 'while', 'switch', 'case', 'break', 'return',
            'typeof', 'void', 'delete', 'new', 'in', 'instanceof', 'var', 'let', 'const',
            'alert', 'confirm', 'prompt', 'setTimeout', 'clearTimeout', 'parseInt', 'parseFloat'
        }

        broken_handlers = []
        for h in parser.event_handlers:
            code = h['code'].strip()
            # Match standalone function calls not preceded by a dot
            cleaned_calls = re.findall(r'(?<![\.\w$])([a-zA-Z0-9_$]+)\s*\(', code)
            for func_name in cleaned_calls:
                if func_name in reserved_keywords:
                    continue
                pattern = rf'(function\s+{func_name}\b|window\.{func_name}\s*=|const\s+{func_name}\s*=|let\s+{func_name}\s*=|var\s+{func_name}\s*=|{func_name}\s*:\s*function)'
                if not re.search(pattern, combined_js):
                    broken_handlers.append({'func': func_name, 'line': h['line'], 'code': code})

        if not broken_handlers:
            self.report.add_pass('Functional Handlers', 'All Inline Event Handlers Defined',
                                 f'All {len(parser.event_handlers)} HTML event calls map to verified functions.')
        else:
            for bh in broken_handlers:
                self.report.add_defect(
                    'Function Break',
                    f"Undefined HTML Event Function: {bh['func']}()",
                    f"index.html line {bh['line']} calls '{bh['code']}', but function '{bh['func']}' is not declared in JS.",
                    self.www / 'index.html',
                    line=bh['line'],
                    recommendation=f"Declare 'function {bh['func']}()' in app.js or export to 'window.{bh['func']}'."
                )

    # --------------------------------------------------------------------------
    # Check 5: Navigation Routes & View Section Mapping
    # --------------------------------------------------------------------------
    def check_navigation_routes(self, parser):
        print(f"{Colors.BOLD}[5/8] Checking Navigation Routes & Section Mapping...{Colors.RESET}")
        index_html = (self.www / 'index.html').read_text(encoding='utf-8', errors='ignore')
        
        # Search all navigateTo('route') in JS and HTML
        nav_routes = set()
        for js_file in self.www.glob('*.js'):
            if 'min.js' not in js_file.name:
                code = js_file.read_text(encoding='utf-8', errors='ignore')
                for m in re.finditer(r'navigateTo\s*\(\s*[\'"]([a-zA-Z0-9_\-]+)[\'"]\s*\)', code):
                    nav_routes.add(m.group(1))

        for m in re.finditer(r'navigateTo\s*\(\s*[\'"]([a-zA-Z0-9_\-]+)[\'"]\s*\)', index_html):
            nav_routes.add(m.group(1))

        if not nav_routes:
            self.report.add_pass('Navigation', 'Single Page View', 'No dynamic route controller detected.')
            return

        missing_sections = []
        for route in nav_routes:
            if route not in parser.sections and route not in parser.ids and f"section-{route}" not in parser.ids:
                missing_sections.append(route)

        if not missing_sections:
            self.report.add_pass('Navigation Route Integrity', 'All Navigation Targets Verified',
                                 f'All routes {sorted(list(nav_routes))} map to existing sections.')
        else:
            for ms in missing_sections:
                self.report.add_defect(
                    'Function Break',
                    f"Broken Navigation Route: '{ms}'",
                    f"App navigates to route '{ms}', but '<section id=\"section-{ms}\">' was not found in index.html.",
                    self.www / 'index.html',
                    recommendation=f"Add '<section id=\"section-{ms}\" class=\"view-section hidden\"></section>' to index.html."
                )

    # --------------------------------------------------------------------------
    # Check 6: Static Asset References (Images, Fonts, Scripts)
    # --------------------------------------------------------------------------
    def check_static_asset_references(self, parser):
        print(f"{Colors.BOLD}[6/8] Verifying Static Asset References (Images, Scripts, Styles)...{Colors.RESET}")
        broken_assets = []
        for asset in parser.asset_references:
            src = asset['src']
            if src.startswith(('http://', 'https://', 'data:', '//', '#')):
                continue
            clean_path = src.split('?')[0].split('#')[0]
            local_file = self.www / clean_path
            if not local_file.exists():
                broken_assets.append({'src': src, 'tag': asset['tag'], 'line': asset['line']})

        if not broken_assets:
            self.report.add_pass('Asset Integrity', 'All Static Assets Resolved on Disk',
                                 f'Verified {len(parser.asset_references)} local assets.')
        else:
            for ba in broken_assets:
                self.report.add_defect(
                    'Broken Asset',
                    f"Missing Asset: '{ba['src']}'",
                    f"index.html line {ba['line']} references '<{ba['tag']} src=\"{ba['src']}\">', but file does not exist on disk.",
                    self.www / 'index.html',
                    line=ba['line'],
                    recommendation=f"Place the missing asset at {self.www / ba['src']}."
                )

    # --------------------------------------------------------------------------
    # Check 7: CSS Variables & Design Tokens
    # --------------------------------------------------------------------------
    def check_css_variables_and_conflicts(self):
        print(f"{Colors.BOLD}[7/8] Auditing CSS Design Tokens & Variable Declarations...{Colors.RESET}")
        css_files = list(self.www.glob('*.css')) + list(self.www.glob('**/*.css'))
        combined_css = ""
        for cf in css_files:
            if 'node_modules' not in str(cf):
                combined_css += "\n" + cf.read_text(encoding='utf-8', errors='ignore')

        declared_vars = set(re.findall(r'(--[a-zA-Z0-9_\-]+)\s*:', combined_css))
        used_vars = set(re.findall(r'var\(\s*(--[a-zA-Z0-9_\-]+)', combined_css))

        undeclared = used_vars - declared_vars
        undeclared = {v for v in undeclared if not any(v.startswith(x) for x in ('--ion-', '--sat', '--sab', '--keyboard-'))}

        if not undeclared:
            self.report.add_pass('CSS Design Tokens', 'All CSS Variables Declared',
                                 f'Verified {len(used_vars)} CSS design variables.')
        else:
            for uv in sorted(list(undeclared))[:5]:
                self.report.add_warning(
                    'CSS Design Defect',
                    f"Undeclared CSS Variable: {uv}",
                    f"CSS utilizes var({uv}), but {uv} is never defined in :root or theme classes.",
                    recommendation=f"Declare '{uv}: <value>;' in :root."
                )

    # --------------------------------------------------------------------------
    # Check 8: Android & Jetpack Compose Native Bridge (If Android Folder Exists)
    # --------------------------------------------------------------------------
    def check_native_android_compose_bridge(self):
        print(f"{Colors.BOLD}[8/8] Checking Android & Jetpack Compose Native Bridge...{Colors.RESET}")
        if not self.android.is_dir():
            self.report.add_pass('Native Bridge', 'Pure Web / PWA Mode', 'No android/ directory present.')
            return

        main_activity = None
        for p in self.android.rglob('MainActivity.*'):
            main_activity = p
            break

        compose_shell = None
        for p in self.android.rglob('*ComposeShell.*'):
            compose_shell = p
            break

        manifest = self.android / 'app/src/main/AndroidManifest.xml'

        if main_activity and main_activity.exists():
            main_code = main_activity.read_text(encoding='utf-8', errors='ignore')
            if 'JinjuComposeShell' in main_code or 'setContent' in main_code:
                self.report.add_pass('Native Compose', 'Jetpack Compose UI Shell Active',
                                     f'Compose shell mounted in {main_activity.name}.')
            else:
                self.report.add_pass('Native Android', 'Standard Bridge Activity Active',
                                     f'{main_activity.name} active.')

            # Check status bar clash prevention
            if 'setDecorFitsSystemWindows(window, true)' in main_code:
                self.report.add_pass('Native Window', 'Status Bar Clash Protection Verified',
                                     'setDecorFitsSystemWindows(window, true) protects against notch/status bar overlap.')
            elif 'setDecorFitsSystemWindows(window, false)' in main_code:
                self.report.add_warning('Native Window', 'Edge-to-Edge Status Bar Overlap Risk',
                                        'setDecorFitsSystemWindows(window, false) may push content directly behind the device status bar.',
                                        main_activity)

        if manifest.exists():
            manifest_code = manifest.read_text(encoding='utf-8', errors='ignore')
            for perm in ('android.permission.INTERNET', 'android.permission.ACCESS_NETWORK_STATE'):
                if perm in manifest_code:
                    self.report.add_pass('Android Permissions', f"Permission {perm.split('.')[-1]} Verified")
                else:
                    self.report.add_defect('Android Permission Defect', f"Missing {perm}",
                                           f"AndroidManifest.xml does not declare {perm}.", manifest)

    # --------------------------------------------------------------------------
    # Optional Check: Critical Streaming & API Reachability
    # --------------------------------------------------------------------------
    def check_critical_api_endpoints(self):
        print(f"{Colors.BOLD}[*] Verifying External API Reachability...{Colors.RESET}")
        endpoints = [
            {
                'name': 'Animeku API (Miku Moe)',
                'url': 'https://animeku.my.id/nontonanime-x/phalcon/api/get_posts/',
                'method': 'POST',
                'data': b'isAPKvalid=true&page=1&count=5',
                'headers': {'Data-Agent': 'AnimeXNonton 2026.4.6/13', 'Content-Type': 'application/x-www-form-urlencoded'}
            },
            {
                'name': 'Manga Reader Catalog',
                'url': 'https://komiku.org/',
                'method': 'GET',
                'data': None,
                'headers': {}
            }
        ]

        for ep in endpoints:
            try:
                req = urllib.request.Request(
                    ep['url'],
                    data=ep.get('data'),
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Mobile) HybridDefectChecker/1.0',
                        **(ep.get('headers') or {})
                    }
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in (200, 201, 301, 302):
                        self.report.add_pass('API Reachability', f"{ep['name']} Online", f"HTTP {resp.status}")
                    else:
                        self.report.add_warning('API Status Warning', f"{ep['name']} Unexpected Status", f"HTTP {resp.status}")
            except Exception as e:
                self.report.add_warning('API Connectivity Warning', f"{ep['name']} Notice", str(e))


# ==============================================================================
# REPORT FORMATTERS
# ==============================================================================
def print_console_summary(report):
    print(f"\n{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.BOLD} AUDIT REPORT SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}══════════════════════════════════════════════════════════════════════════{Colors.RESET}")

    total_passed = len(report.passed_checks)
    total_warnings = len(report.warnings)
    total_defects = len(report.defects)

    print(f"  {Colors.GREEN}✔ Checks Passed:    {total_passed}{Colors.RESET}")
    print(f"  {Colors.YELLOW}⚠ Warnings:         {total_warnings}{Colors.RESET}")
    print(f"  {Colors.RED}✖ Critical Defects: {total_defects}{Colors.RESET}\n")

    if report.defects:
        print(f"{Colors.BOLD}{Colors.RED}❌ CRITICAL DEFECTS / FUNCTION BREAKAGES FOUND:{Colors.RESET}")
        for i, d in enumerate(report.defects, 1):
            print(f"\n  {Colors.RED}{Colors.BOLD}[{i}] {d['title']}{Colors.RESET} ({d['category']})")
            print(f"      {d['description']}")
            if d['file']:
                line_info = f":{d['line']}" if d['line'] else ""
                print(f"      {Colors.DIM}Location:{Colors.RESET} {d['file']}{line_info}")
            if d['recommendation']:
                print(f"      {Colors.CYAN}Fix Recommendation:{Colors.RESET} {d['recommendation']}")

    if report.warnings:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠️  WARNINGS & DESIGN ADVISORIES:{Colors.RESET}")
        for i, w in enumerate(report.warnings, 1):
            print(f"\n  {Colors.YELLOW}{Colors.BOLD}[{i}] {w['title']}{Colors.RESET} ({w['category']})")
            print(f"      {w['description']}")
            if w['file']:
                line_info = f":{w['line']}" if w['line'] else ""
                print(f"      {Colors.DIM}Location:{Colors.RESET} {w['file']}{line_info}")

    if not report.defects:
        print(f"\n{Colors.BOLD}{Colors.GREEN}✨ ALL CHECKS PASSED: 0 CRITICAL DEFECTS DETECTED!{Colors.RESET}")
        print(f"{Colors.GREEN}The application UI/UX and functional routes are completely intact.{Colors.RESET}\n")


def export_html_report(report, output_path):
    defects_html = "".join([f"""
    <div class="card defect">
        <div class="card-header"><span class="badge badge-defect">CRITICAL</span> <strong>{d['title']}</strong></div>
        <p class="desc">{d['description']}</p>
        {f'<p class="meta"><strong>Location:</strong> <code>{d["file"]}:{d.get("line","")}</code></p>' if d.get('file') else ''}
        {f'<div class="rec"><strong>Fix:</strong> {d["recommendation"]}</div>' if d.get('recommendation') else ''}
    </div>
    """ for d in report.defects]) or "<div class='card pass'><strong>No Critical Defects Found!</strong> All functional validations passed cleanly.</div>"

    warnings_html = "".join([f"""
    <div class="card warning">
        <div class="card-header"><span class="badge badge-warning">WARNING</span> <strong>{w['title']}</strong></div>
        <p class="desc">{w['description']}</p>
        {f'<p class="meta"><strong>Location:</strong> <code>{w["file"]}:{w.get("line","")}</code></p>' if w.get('file') else ''}
    </div>
    """ for w in report.warnings]) or "<div class='card pass'><strong>No Warnings!</strong></div>"

    passes_html = "".join([f"""
    <div class="pass-item">
        <span class="icon">✔</span>
        <div><strong>{p['title']}</strong> <span class="dim">({p['category']})</span> - {p['detail']}</div>
    </div>
    """ for p in report.passed_checks])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hybrid App UI/UX & Functional Defect Report</title>
    <style>
        :root {{
            --bg: #0B0F19;
            --surface: #141B29;
            --surface-container: #1E2638;
            --primary: #00B7E0;
            --text: #F1F5F9;
            --text-dim: #94A3B8;
            --danger: #EF4444;
            --warning: #F59E0B;
            --success: #10B981;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        h1 {{
            margin: 0 0 6px 0;
            font-size: 26px;
            color: #fff;
        }}
        h1 span {{ color: var(--primary); }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background: var(--surface);
            padding: 20px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.06);
            text-align: center;
        }}
        .stat-val {{ font-size: 32px; font-weight: 800; }}
        .stat-val.green {{ color: var(--success); }}
        .stat-val.yellow {{ color: var(--warning); }}
        .stat-val.red {{ color: var(--danger); }}
        .stat-label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; font-weight: 700; margin-top: 4px; }}
        .section-title {{ font-size: 18px; font-weight: 700; margin: 30px 0 16px 0; display: flex; align-items: center; gap: 8px; }}
        .card {{
            background: var(--surface);
            border-radius: 14px;
            padding: 16px 20px;
            margin-bottom: 12px;
            border: 1px solid rgba(255,255,255,0.06);
        }}
        .card.defect {{ border-left: 4px solid var(--danger); }}
        .card.warning {{ border-left: 4px solid var(--warning); }}
        .card.pass {{ border-left: 4px solid var(--success); }}
        .badge {{
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 6px;
            text-transform: uppercase;
        }}
        .badge-defect {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
        .desc {{ margin: 8px 0; font-size: 14px; color: #CBD5E1; }}
        .meta {{ font-size: 12px; color: var(--text-dim); margin: 6px 0; }}
        code {{ background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: var(--primary); }}
        .rec {{ margin-top: 10px; background: rgba(0, 183, 224, 0.1); border-left: 2px solid var(--primary); padding: 8px 12px; font-size: 12.5px; border-radius: 4px; }}
        .pass-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            background: var(--surface);
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 13px;
        }}
        .pass-item .icon {{ color: var(--success); font-weight: bold; }}
        .pass-item .dim {{ color: var(--text-dim); font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Hybrid App <span>Defect Checker</span></h1>
            <p style="color:var(--text-dim); margin:0;">Automated UI/UX Overlap, DOM Binding, and Function Validation</p>
        </div>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-val green">{len(report.passed_checks)}</div>
                <div class="stat-label">Checks Passed</div>
            </div>
            <div class="stat-box">
                <div class="stat-val yellow">{len(report.warnings)}</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat-box">
                <div class="stat-val red">{len(report.defects)}</div>
                <div class="stat-label">Critical Defects</div>
            </div>
        </div>

        <div class="section-title">Critical Defects & Function Breakages</div>
        {defects_html}

        <div class="section-title">Design & UX Warnings</div>
        {warnings_html}

        <div class="section-title">Verified Passed Checks</div>
        {passes_html}
    </div>
</body>
</html>
"""
    output_path.write_text(html, encoding='utf-8')
    print(f"{Colors.GREEN}✔ Exported Interactive HTML Report to:{Colors.RESET} {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid & Web App Automated UI/UX Defect and Function Break Checker"
    )
    parser.add_argument('--path', type=str, default='.', help='Target project root directory (default: current directory)')
    parser.add_argument('--output-dir', type=str, default=None, help='Directory to output report files (default: target project root)')
    parser.add_argument('--no-network', action='store_true', help='Skip live network/API connectivity checks')
    parser.add_argument('--strict', action='store_true', help='Fail (exit 1) on warnings as well as critical defects')

    args = parser.parse_args()

    target_dir = Path(args.path).resolve()
    suite = AuditSuite(target_dir, args.output_dir)
    report = suite.run_all(check_network=not args.no_network)

    print_console_summary(report)

    # Export reports
    out_dir = Path(args.output_dir).resolve() if args.output_dir else target_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    html_out = out_dir / 'defect_report.html'
    export_html_report(report, html_out)

    json_out = out_dir / 'defect_report.json'
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump({
            'passed': report.passed_checks,
            'warnings': report.warnings,
            'defects': report.defects
        }, f, indent=2)
    print(f"{Colors.GREEN}✔ Exported JSON Machine Report to:{Colors.RESET} {json_out}\n")

    if report.defects:
        sys.exit(1)
    if args.strict and report.warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
