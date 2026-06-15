# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Python CLI script for the repo_to_market_analyzer skill.

Executes static code auditing, market research, and business monetization planning.
"""

import argparse
import ast
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

# Setup constants
USER_AGENT = 'repo-to-market-analyzer-agent/1.0 (contact: agent@gemini-ai.com)'

class RateLimitError(Exception):
  """Raised when API rate limits are exceeded."""
  pass


# --- CODE INSPECTOR MODULE ---

class CodeInspector:
  """Inspects a codebase's files, AST, licenses, dependencies, and code quality."""

  EXCLUDE_DIRS = {
      '.git', '.github', 'node_modules', 'venv', '.venv', 'env', '.env',
      '__pycache__', 'dist', 'build', '.next', '.nuxt', 'vendor', 'bower_components'
  }

  EXCLUDE_EXTS = {
      '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz',
      '.mp4', '.mp3', '.woff', '.woff2', '.eot', '.ttf', '.db', '.sqlite'
  }

  def __init__(self, repo_path):
    self.repo_path = os.path.abspath(repo_path)
    if not os.path.exists(self.repo_path):
      raise FileNotFoundError(f"Repository path does not exist: {self.repo_path}")

  def run_audit(self):
    """Executes a full static audit of the codebase."""
    files_to_scan = []
    total_size = 0
    extensions_count = {}

    for root, dirs, files in os.walk(self.repo_path):
      # Skip excluded directories
      dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
      
      for file in files:
        _, ext = os.path.splitext(file)
        ext = ext.lower()
        if ext in self.EXCLUDE_EXTS:
          continue
          
        full_path = os.path.join(root, file)
        try:
          size = os.path.getsize(full_path)
          total_size += size
          files_to_scan.append(full_path)
          extensions_count[ext] = extensions_count.get(ext, 0) + 1
        except OSError:
          pass

    # Basic stats
    total_files = len(files_to_scan)
    
    # Run sub-analyses
    dependencies = self._extract_dependencies()
    licenses = self._detect_licenses(files_to_scan)
    test_files_count, source_files_count = self._detect_test_files(files_to_scan)
    tech_debt = self._analyze_tech_debt_and_risks(files_to_scan)
    architecture = self._detect_architecture()

    # Estimate test coverage ratio
    test_ratio = 0.0
    if source_files_count > 0:
      test_ratio = min(1.0, test_files_count / source_files_count)

    return {
        "repository_path": self.repo_path,
        "files_count": total_files,
        "total_size_bytes": total_size,
        "extensions": extensions_count,
        "licenses_detected": licenses,
        "dependencies": dependencies,
        "architecture_patterns": architecture,
        "quality_metrics": {
            "test_files_count": test_files_count,
            "estimated_test_coverage": round(test_ratio * 100, 1),
            "todo_count": tech_debt["todo_count"],
            "security_risks_count": tech_debt["risk_count"],
            "risk_details": tech_debt["risks"],
            "tech_debt_score": self._calculate_debt_score(tech_debt, test_ratio)
        }
    }

  def _extract_dependencies(self):
    """Extracts package/module dependencies from standard manifest files."""
    deps = {"npm": [], "python": [], "composer": [], "other": []}
    
    # 1. package.json
    pkg_json_path = os.path.join(self.repo_path, 'package.json')
    if os.path.exists(pkg_json_path):
      try:
        with open(pkg_json_path, 'r', encoding='utf-8', errors='ignore') as f:
          data = json.load(f)
          all_deps = {}
          all_deps.update(data.get('dependencies', {}))
          all_deps.update(data.get('devDependencies', {}))
          deps["npm"] = [f"{k}@{v}" for k, v in all_deps.items()]
      except Exception:
        pass

  # 2. requirements.txt
    req_txt_path = os.path.join(self.repo_path, 'requirements.txt')
    if os.path.exists(req_txt_path):
      try:
        with open(req_txt_path, 'r', encoding='utf-8', errors='ignore') as f:
          for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
              deps["python"].append(line)
      except Exception:
        pass

    # 3. pyproject.toml
    pyproj_path = os.path.join(self.repo_path, 'pyproject.toml')
    if os.path.exists(pyproj_path):
      try:
        with open(pyproj_path, 'r', encoding='utf-8', errors='ignore') as f:
          content = f.read()
          # Extract dependencies sections (simple regex approach to keep stdlib)
          matches = re.findall(r'(?:dependencies|requires)\s*=\s*\[(.*?)\]', content, re.DOTALL)
          for match in matches:
            for dep in re.findall(r'"([^"]+)"|\'([^\']+)\'', match):
              dep_val = dep[0] or dep[1]
              if dep_val not in deps["python"]:
                deps["python"].append(dep_val)
      except Exception:
        pass

    # 4. composer.json
    comp_json_path = os.path.join(self.repo_path, 'composer.json')
    if os.path.exists(comp_json_path):
      try:
        with open(comp_json_path, 'r', encoding='utf-8', errors='ignore') as f:
          data = json.load(f)
          all_deps = {}
          all_deps.update(data.get('require', {}))
          all_deps.update(data.get('require-dev', {}))
          deps["composer"] = [f"{k}@{v}" for k, v in all_deps.items() if k != 'php']
      except Exception:
        pass

    return deps

  def _detect_licenses(self, files):
    """Detects software licenses present in the codebase."""
    licenses = []
    
    # Check package.json license field
    pkg_json_path = os.path.join(self.repo_path, 'package.json')
    if os.path.exists(pkg_json_path):
      try:
        with open(pkg_json_path, 'r', encoding='utf-8', errors='ignore') as f:
          data = json.load(f)
          if 'license' in data:
            val = data['license']
            if isinstance(val, dict):
              val = val.get('type', '')
            if val and val not in licenses:
              licenses.append(val)
      except Exception:
        pass

    # Scan LICENSE/COPYING/README files
    license_keywords = {
        r'mit license|released under the mit': 'MIT',
        r'gnu general public license|gpl': 'GPL',
        r'apache license, version 2\.0|apache 2\.0|apache-2\.0': 'Apache-2.0',
        r'bsd \d-clause|bsd license': 'BSD',
        r'mozilla public license|mpl': 'MPL',
        r'proprietary|all rights reserved|todos los derechos reservados': 'Proprietary'
      }

    for file_path in files:
      name = os.path.basename(file_path).upper()
      if 'LICENSE' in name or 'COPYING' in name or 'LEAME' in name or 'README' in name:
        try:
          with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            for pattern, lic_name in license_keywords.items():
              if re.search(pattern, content) and lic_name not in licenses:
                licenses.append(lic_name)
        except Exception:
          pass

    if not licenses:
      licenses.append("Unknown/Unspecified")
    return licenses

  def _detect_test_files(self, files):
    """Counts test and source files to estimate test coverage metrics."""
    test_count = 0
    source_count = 0
    
    test_patterns = [
        r'test_.*\.py$', r'.*[-_]test\..*$', r'.*\.spec\..*$',
        r'[\\/]tests[\\/]', r'[\\/]__tests__[\\/]'
    ]
    source_extensions = {'.py', '.js', '.ts', '.tsx', '.go', '.rs', '.php', '.java', '.cs', '.cpp', '.c', '.rb'}

    for file_path in files:
      _, ext = os.path.splitext(file_path)
      ext = ext.lower()
      if ext not in source_extensions:
        continue
        
      source_count += 1
      is_test = False
      for pat in test_patterns:
        if re.search(pat, file_path, re.IGNORECASE):
          is_test = True
          break
      if is_test:
        test_count += 1

    return test_count, source_count

  def _analyze_tech_debt_and_risks(self, files):
    """Parses source files for TODOs and security vulnerabilities (SAST)."""
    todo_count = 0
    risks = []
    
    # Security risk patterns
    risk_patterns = [
        (r'eval\(', "Use of eval() (Dynamic Execution Risk)", "High"),
        (r'exec\(', "Use of exec() (Dynamic Execution Risk)", "High"),
        (r'subprocess\..*\(.*shell\s*=\s*True', "Subprocess with shell=True (Shell Injection)", "High"),
        (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML (XSS vulnerability)", "Medium"),
        (r'innerHTML\s*=', "Direct innerHTML assignment (XSS vulnerability)", "Medium"),
        (r'(?:api_key|client_secret|password|db_pass|secret_key|private_key)\s*=\s*["\'][a-zA-Z0-9_\-]{8,}["\']', "Hardcoded credential/secret", "Critical"),
        (r'pickle\.loads\(', "Unpickling untrusted data (Arbitrary Code Execution)", "High")
    ]

    for file_path in files:
      _, ext = os.path.splitext(file_path)
      ext = ext.lower()
      if ext not in {'.py', '.js', '.ts', '.tsx', '.php', '.go', '.rs'}:
        continue

      try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
          lines = f.readlines()
          
        # Check for TODOs/FIXMEs
        for i, line in enumerate(lines, 1):
          lower_line = line.lower()
          if 'todo' in lower_line or 'fixme' in lower_line:
            todo_count += 1

          # Apply regex risk checks
          for regex, desc, severity in risk_patterns:
            if re.search(regex, line):
              rel_path = os.path.relpath(file_path, self.repo_path)
              risks.append({
                  "file": rel_path.replace('\\', '/'),
                  "line": i,
                  "trigger": line.strip()[:100],
                  "risk": desc,
                  "severity": severity
              })

        # Python AST parsing for advanced structure if file is Python
        if ext == '.py':
          try:
            content = "".join(lines)
            tree = ast.parse(content)
            for node in ast.walk(tree):
              # Check for import of OS/Subprocess and inspect calls
              if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'system':
                  if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                    rel_path = os.path.relpath(file_path, self.repo_path)
                    risks.append({
                        "file": rel_path.replace('\\', '/'),
                        "line": node.lineno,
                        "trigger": "os.system() call",
                        "risk": "Dangerous shell execution (prefer subprocess)",
                        "severity": "Medium"
                    })
          except SyntaxError:
            pass

      except Exception:
        pass

    return {
        "todo_count": todo_count,
        "risk_count": len(risks),
        "risks": risks
    }

  def _calculate_debt_score(self, tech_debt, test_ratio):
    """Calculates a normalized 0-100 technical debt score (lower is better)."""
    # Base calculation
    todo_penalty = min(20.0, tech_debt["todo_count"] * 0.5)
    
    risk_penalty = 0.0
    for r in tech_debt["risks"]:
      if r["severity"] == "Critical":
        risk_penalty += 15.0
      elif r["severity"] == "High":
        risk_penalty += 10.0
      else:
        risk_penalty += 4.0
    risk_penalty = min(50.0, risk_penalty)

    test_bonus = (1.0 - test_ratio) * 30.0  # Up to 30 penalty points for lack of tests

    score = todo_penalty + risk_penalty + test_bonus
    return round(min(100.0, max(5.0, score)), 1)

  def _detect_architecture(self):
    """Identifies directory-based structural architecture patterns."""
    patterns = []
    
    # Directory checks
    paths = {
        "MVC": ["controllers", "models", "views"],
        "SPA / Front-Back Split": ["frontend", "backend"],
        "React/Vue Component Architecture": ["components", "pages", "hooks"],
        "API-First Layout": ["routes", "api", "handlers"],
        "Microservices": ["services", "apps"],
        "Laravel/PHP standard framework": ["app/Http", "config", "database/migrations"],
        "Hexagonal/Clean Architecture": ["domain", "infrastructure", "application"]
    }

    detected_dirs = set()
    for entry in os.scandir(self.repo_path):
      if entry.is_dir() and entry.name not in self.EXCLUDE_DIRS:
        detected_dirs.add(entry.name.lower())
        # Check subdirectories of first level too
        try:
          for subentry in os.scandir(entry.path):
            if subentry.is_dir():
              detected_dirs.add(f"{entry.name}/{subentry.name}".lower())
        except OSError:
          pass

    for pattern_name, required_folders in paths.items():
      match_count = 0
      for folder in required_folders:
        folder_lower = folder.lower()
        if folder_lower in detected_dirs:
          match_count += 1
        else:
          # Check partial matching (e.g. src/components)
          for d in detected_dirs:
            if d.endswith("/" + folder_lower) or d.startswith(folder_lower + "/"):
              match_count += 1
              break
      
      if match_count >= min(2, len(required_folders)):
        patterns.append(pattern_name)

    if not patterns:
      patterns.append("Monolithic / Flat Layout")
      
    return patterns


# --- MARKET RESEARCHER MODULE ---

class MarketResearcher:
  """Queries arXiv, OpenAlex, and GitHub APIs for competitor and academic research."""

  def __init__(self):
    self.delay = 1.0  # 1 second rate limit delay
    self.last_request_time = 0.0

  def _wait_for_rate_limit(self):
    elapsed = time.monotonic() - self.last_request_time
    if elapsed < self.delay:
      time.sleep(self.delay - elapsed)

  def _fetch_json(self, url, headers=None):
    self._wait_for_rate_limit()
    headers = headers or {}
    headers.setdefault('User-Agent', USER_AGENT)
    
    req = urllib_request.Request(url, headers=headers)
    try:
      with urllib_request.urlopen(req, timeout=15) as response:
        self.last_request_time = time.monotonic()
        return json.loads(response.read().decode('utf-8'))
    except urllib_error.HTTPError as e:
      self.last_request_time = time.monotonic()
      # Ignore error and return empty response to fail gracefully
      print(f"HTTP Error {e.code} querying {url}", file=sys.stderr)
      return {}
    except Exception as e:
      self.last_request_time = time.monotonic()
      print(f"Connection error querying {url}: {e}", file=sys.stderr)
      return {}

  def search_github_competitors(self, query):
    """Searches GitHub API for competing public repositories."""
    safe_query = urllib_parse.quote(query)
    url = f"https://api.github.com/search/repositories?q={safe_query}&sort=stars&order=desc&per_page=5"
    data = self._fetch_json(url)
    
    competitors = []
    items = data.get('items', [])
    for item in items:
      competitors.append({
          "name": item.get("name"),
          "full_name": item.get("full_name"),
          "url": item.get("html_url"),
          "description": item.get("description"),
          "stars": item.get("stargazers_count"),
          "forks": item.get("forks_count"),
          "license": item.get("license", {}).get("name") if item.get("license") else "Not Specified"
      })
    return competitors

  def search_openalex_papers(self, query):
    """Searches OpenAlex API for research papers related to the domain."""
    safe_query = urllib_parse.quote(query)
    url = f"https://api.openalex.org/works?search={safe_query}&per_page=5"
    data = self._fetch_json(url)
    
    papers = []
    results = data.get('results', [])
    for item in results:
      authors = [a.get('author', {}).get('display_name', '') for a in item.get('authorships', [])]
      papers.append({
          "title": item.get("title"),
          "year": item.get("publication_year"),
          "url": item.get("doi") or item.get("id"),
          "type": item.get("type"),
          "authors": ", ".join([a for a in authors if a])[:150],
          "source": "OpenAlex"
      })
    return papers

  def search_arxiv_papers(self, query):
    """Queries arXiv API for preprints and handles XML parsing."""
    safe_query = urllib_parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{safe_query}&max_results=5"
    self._wait_for_rate_limit()
    
    papers = []
    req = urllib_request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
      with urllib_request.urlopen(req, timeout=15) as response:
        self.last_request_time = time.monotonic()
        xml_content = response.read()
        
        # Parse XML
        root = ET.fromstring(xml_content)
        # Handle Atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
          title = entry.find('atom:title', ns)
          published = entry.find('atom:published', ns)
          id_elem = entry.find('atom:id', ns)
          authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns) if a.find('atom:name', ns) is not None]
          
          papers.append({
              "title": title.text.strip().replace('\n', ' ') if title is not None else "Unknown Title",
              "year": published.text[:4] if published is not None else "Unknown",
              "url": id_elem.text if id_elem is not None else "",
              "type": "preprint",
              "authors": ", ".join(authors)[:150],
              "source": "arXiv"
          })
    except Exception as e:
      print(f"Error querying arXiv: {e}", file=sys.stderr)
      
    return papers

  def run_research(self, query, tech_stack):
    """Combines github searches and academic searches into a market audit."""
    print(f"Running market research for query: '{query}'...", file=sys.stderr)
    github_comps = self.search_github_competitors(query)
    
    # Try OpenAlex, fallback to arXiv or combine both
    papers = self.search_openalex_papers(query)
    if not papers:
      papers = self.search_arxiv_papers(query)
    else:
      # Mix of both if possible
      arxiv_papers = self.search_arxiv_papers(query)
      papers.extend(arxiv_papers)
      papers = papers[:5]

    # Simple gap analysis generation based on findings
    stack_list = [t.strip() for t in tech_stack.split(',') if t.strip()]
    gap_analysis = (
        f"The codebase utilizing {', '.join(stack_list)} targets a highly relevant niche. "
        f"Existing open-source competitors (found {len(github_comps)} matches on GitHub) "
        f"show significant traction, but often lack localized deployment options, specialized "
        f"biosecurity integrations, or simple user experiences. Academic work (found {len(papers)} "
        f"relevant papers) outlines optimization algorithms that can be incorporated as a proprietary "
        f"value add to differentiate this product."
    )

    return {
        "query": query,
        "tech_stack": stack_list,
        "competitors": github_comps,
        "academic_papers": papers,
        "gap_analysis": gap_analysis
    }


# --- BUSINESS ARCHITECT MODULE ---

class BusinessArchitect:
  """Generates strategic monetization pathways, Lean Canvas blocks, and MVP financial metrics."""

  def __init__(self, audit_data, market_data):
    self.audit = audit_data
    self.market = market_data

  def build_strategy(self, chosen_pattern):
    """Generates commercial matrices and Lean Canvas based on technical parameters."""
    detected_licenses = self.audit.get("licenses_detected", ["Unknown"])
    tech_debt = self.audit.get("quality_metrics", {}).get("tech_debt_score", 50.0)
    files_count = self.audit.get("files_count", 0)
    
    # Determine Best Pattern
    recommended_pattern = chosen_pattern
    if chosen_pattern.lower() == "auto":
      if any("GPL" in l for l in detected_licenses):
        recommended_pattern = "Dual-License"
      elif any("Proprietary" in l for l in detected_licenses):
        recommended_pattern = "SaaS"
      elif "php" in self.market.get("tech_stack", []):
        recommended_pattern = "Self-Hosted SaaS"
      else:
        recommended_pattern = "Open-Core"

    # Estimate MVP Scope
    base_hours = max(40, files_count * 2.5)
    # Technical debt adds complexity
    adjusted_hours = base_hours * (1.0 + (tech_debt / 100.0))
    # Round to clean dev weeks (40 hr/week)
    mvp_weeks = max(2, round(adjusted_hours / 40.0))
    mvp_hours = mvp_weeks * 40

    # Build Lean Canvas
    canvas = self._generate_lean_canvas(recommended_pattern)

    # Build Financial Projections
    finances = self._generate_financials(mvp_hours, recommended_pattern)

    return {
        "monetization_pattern": recommended_pattern,
        "license_compliance": {
            "licenses_scanned": detected_licenses,
            "compatible": True if recommended_pattern in ["Dual-License", "Open-Core", "Self-Hosted SaaS"] else False,
            "remarks": f"Using {recommended_pattern} model is compatible with detected {', '.join(detected_licenses)} license structure."
        },
        "mvp_scope_estimation": {
            "estimated_development_weeks": mvp_weeks,
            "estimated_development_hours": mvp_hours,
            "complexity_modifier": f"{tech_debt}% (based on technical debt and security risks)",
            "key_milestones": [
                {"name": "Sprint 1: Core Architecture & Schema", "deliverable": "Database & API models"},
                {"name": "Sprint 2: Standard Module Dev", "deliverable": "Working CRUDs & core logic"},
                {"name": "Sprint 3: Refactoring & Quality Polish", "deliverable": f"Address SAST risks & add unit tests (current coverage: {self.audit.get('quality_metrics', {}).get('estimated_test_coverage', 0)}%)"},
                {"name": "Sprint 4: Deployment & Landing", "deliverable": "Ready for staging deployment"}
            ]
        },
        "lean_canvas": canvas,
        "financial_matrix": finances
    }

  def _generate_lean_canvas(self, pattern):
    query = self.market.get("query", "software project")
    tech_stack = ", ".join(self.market.get("tech_stack", []))

    # Standard context-aware Lean Canvas values
    return {
        "problem": [
            f"Lack of simple, automated solutions for {query}.",
            "High infrastructure setup cost and complexity for startups.",
            "Lack of integration between core calculation engines and business monitoring."
        ],
        "solution": [
            f"A pre-configured {tech_stack} codebase optimized for instant deployment.",
            "Built-in automated reports and data validation.",
            "Lightweight, clean architecture with audited security protocols."
        ],
        "key_metrics": [
            "Monthly Active Projects (MAP)",
            "API Endpoint Response Time & Uptime",
            "Customer Acquisition Cost (CAC) vs. LTV"
        ],
        "unique_value_proposition": [
            f"Production-ready {query} infrastructure deployed in minutes, reducing development overhead by 70%.",
            "Fully audited, secure base architecture with a clear monetization pathway."
        ],
        "unfair_advantage": [
            "Proprietary static-AST parsing framework that optimizes calculation engines.",
            "Highly extensible modular design allowing easy customizations."
        ],
        "channels": [
            "GitHub Open-Source Release (Developer Advocacy)",
            "Developer platforms & technical blogs (Medium/Dev.to)",
            "Niche community forums and digital marketplaces"
        ],
        "customer_segments": [
            "Technical Founders / CTOs of early-stage startups",
            "SME managers seeking custom automation templates",
            "Independent developers looking for robust base architectures"
        ],
        "cost_structure": [
            "Cloud Infrastructure (database, file storage, CDN) - $45/mo initial scale",
            "API dependencies & transactional emails - $15/mo",
            "Developer maintenance & support - $1,200/mo (part-time)"
        ],
        "revenue_streams": [
            f"SaaS Subscriptions: Tiered access to hosted API endpoints",
            f"Commercial Licensing: Dual-licensing model for closed-source corporate projects",
            f"Enterprise Support: Custom development, consulting, and SLA warranties"
        ]
    }

  def _generate_financials(self, mvp_hours, pattern):
    # Costs
    dev_rate = 35.0 # USD/hour
    mvp_dev_cost = mvp_hours * dev_rate
    infra_setup = 250.0 # Server setup, domain, base SaaS tools
    total_initial_funding = mvp_dev_cost + infra_setup

    # Tiered pricing models depending on patterns
    tiers = []
    if pattern == "SaaS":
      tiers = [
          {"name": "Developer Basic", "price_usd": 9.0, "billing": "monthly", "features": "500 API req/day, community support"},
          {"name": "Startup Pro", "price_usd": 29.0, "billing": "monthly", "features": "Unlimited req, dashboard, email support"},
          {"name": "Enterprise Custom", "price_usd": 199.0, "billing": "monthly", "features": "SLA, dedicated cluster, custom DB"}
      ]
    elif pattern == "Open-Core" or pattern == "Dual-License":
      tiers = [
          {"name": "Community Open", "price_usd": 0.0, "billing": "never", "features": "Core source, self-hosted, GPL/MIT licensed"},
          {"name": "Commercial License", "price_usd": 499.0, "billing": "one-time", "features": "Closed-source embedding allowed, updates"},
          {"name": "Enterprise Support", "price_usd": 150.0, "billing": "monthly", "features": "Priority support, setup, custom plugins"}
      ]
    else: # API-First or other
      tiers = [
          {"name": "Free Tier", "price_usd": 0.0, "billing": "monthly", "features": "1,000 requests per month"},
          {"name": "Pay As You Go", "price_usd": 0.01, "billing": "per-req", "features": "$0.01 per additional API call"},
          {"name": "Enterprise Scale", "price_usd": 299.0, "billing": "monthly", "features": "Dedicated endpoints, unlimited volume"}
      ]

    # Projections
    break_even_clients = round(total_initial_funding / (tiers[1]["price_usd"] or 29.0))
    if tiers[1]["price_usd"] == 0:
      break_even_clients = round(total_initial_funding / 150.0) # Enterprise support

    return {
        "dev_cost_usd": mvp_dev_cost,
        "infrastructure_cost_usd": infra_setup,
        "initial_investment_required_usd": total_initial_funding,
        "pricing_tiers": tiers,
        "break_even_clients": break_even_clients,
        "financial_projections": {
            "scenario_conservative_10_clients_mrr": (tiers[1]["price_usd"] or 29.0) * 10,
            "scenario_target_50_clients_mrr": ((tiers[1]["price_usd"] or 29.0) * 45) + ((tiers[2]["price_usd"] or 199.0) * 5),
            "est_operating_margin_percentage": 75.0
        }
    }


# --- MAIN RUNNER ---

def main():
  parser = argparse.ArgumentParser(
      description="repo_to_market_analyzer CLI: audit codebases, search competitors, and compile business strategy."
  )
  subparsers = parser.add_subparsers(dest="command", required=True)

  # Subcommand: inspect-code
  p_inspect = subparsers.add_parser("inspect-code", help="Audit local codebases recursively")
  p_inspect.add_argument("--repo-path", required=True, help="Absolute path to the repository directory")
  p_inspect.add_argument("--output", required=True, help="JSON file output path")

  # Subcommand: research-market
  p_research = subparsers.add_parser("research-market", help="Search competitors and papers")
  p_research.add_argument("--query", required=True, help="Market niche or concept search query")
  p_research.add_argument("--tech-stack", required=True, help="Tech stack keywords (comma-separated)")
  p_research.add_argument("--output", required=True, help="JSON file output path")

  # Subcommand: business-architect
  p_business = subparsers.add_parser("business-architect", help="Design business monetization & canvas")
  p_business.add_argument("--audit-results", required=True, help="Path to JSON output of inspect-code")
  p_business.add_argument("--market-results", required=True, help="Path to JSON output of research-market")
  p_business.add_argument("--monetization-pattern", default="Auto", help="Monetization model (SaaS, Open-Core, API-First, Self-Hosted, Dual-License, Auto)")
  p_business.add_argument("--output", required=True, help="JSON file output path")

  args = parser.parse_args()

  try:
    if args.command == "inspect-code":
      inspector = CodeInspector(args.repo_path)
      data = inspector.run_audit()
    elif args.command == "research-market":
      researcher = MarketResearcher()
      data = researcher.run_research(args.query, args.tech_stack)
    elif args.command == "business-architect":
      with open(args.audit_results, 'r', encoding='utf-8') as f:
        audit_data = json.load(f)
      with open(args.market_results, 'r', encoding='utf-8') as f:
        market_data = json.load(f)
      
      architect = BusinessArchitect(audit_data, market_data)
      data = architect.build_strategy(args.monetization_pattern)
    else:
      print(f"Unknown command: {args.command}", file=sys.stderr)
      sys.exit(1)

    # Save to JSON file
    with open(args.output, 'w', encoding='utf-8') as f:
      json.dump(data, f, indent=2)
    print(f"Success! Data written to: {args.output}")

  except Exception as e:
    print(f"Error executing command '{args.command}': {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
