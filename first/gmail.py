#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   EmailOSINT Pro v2.0 — полный OSINT-анализ email            ║
║   Только открытые источники. Только в законных целях.        ║
╚══════════════════════════════════════════════════════════════╝
"""

import argparse
import csv
import hashlib
import json
import re
import shutil
import smtplib
import socket
import ssl
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional
from urllib.parse import quote, quote_plus

import dns.resolver
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ══════════════════════════ КОНФИГУРАЦИЯ ══════════════════════════

CONFIG = {
    "timeout": 15,
    "max_workers": 6,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "proxy": None,             # "http://127.0.0.1:8080" или "socks5://127.0.0.1:9050"
    "hibp_api_key": None,      # https://haveibeenpwned.com/API/Key
    "hunter_api_key": None,    # https://hunter.io/api-keys
    "emailrep_api_key": None,  # https://emailrep.io/key
    "github_token": None,      # https://github.com/settings/tokens
    "smtp_verify": False,
    "smtp_from": "probe@example.com",
}

VERBOSE = True

# ── Справочники ──────────────────────────────────────────────────

DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
    "temp-mail.org", "yopmail.com", "trashmail.com", "getnada.com",
    "dropmail.me", "sharklasers.com", "dispostable.com", "fakeinbox.com",
    "maildrop.cc", "mytemp.email", "emailondeck.com", "moakt.com",
}

ROLE_ACCOUNTS = {
    "admin", "info", "support", "sales", "contact", "help", "billing",
    "noreply", "no-reply", "postmaster", "webmaster", "office", "hr",
    "security", "abuse", "ceo", "jobs", "career", "media",
}

POPULAR_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "mail.ru",
    "yandex.ru", "icloud.com", "proton.me", "protonmail.com", "gmx.com",
    "zoho.com", "live.com",
]

DKIM_SELECTORS = ("google", "default", "selector1", "selector2",
                  "k1", "dkim", "s1", "s2", "mail", "smtp")

SOCIAL_PLATFORMS = {
    "VK":        "https://vk.com/search?c[q]={q}",
    "Facebook":  "https://www.facebook.com/search/top?q={q}",
    "Twitter/X": "https://twitter.com/search?q={q}",
    "Instagram": "https://www.instagram.com/{u}/",
    "Telegram":  "https://t.me/{u}",
    "Reddit":    "https://www.reddit.com/user/{u}",
    "GitHub":    "https://github.com/{u}",
    "TikTok":    "https://www.tiktok.com/@{u}",
    "Steam":     "https://steamcommunity.com/id/{u}",
    "Medium":    "https://medium.com/@{u}",
    "Pinterest": "https://www.pinterest.com/{u}/",
    "LinkedIn":  "https://www.linkedin.com/search/results/all/?keywords={q}",
}

GOOGLE_DORKS = [
    '"{email}"',
    '"{email}" (site:vk.com OR site:ok.ru)',
    '"{email}" (site:facebook.com OR site:instagram.com)',
    '"{email}" (site:twitter.com OR site:x.com)',
    '"{email}" site:linkedin.com',
    '"{email}" site:github.com',
    '"{email}" (site:pastebin.com OR site:justpaste.it)',
    '"{email}" site:reddit.com',
    '"{email}" site:t.me',
    '"{email}" (filetype:pdf OR filetype:doc OR filetype:xlsx)',
    '"{email}" intitle:"index.of"',
    '"{email}" ("пароль" OR "password")',
    '"{email}" ("телефон" OR "phone")',
    '"{u}" "@{d}"',
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>OSINT-отчёт: {email}</title>
<style>
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:2rem; }}
  h1 {{ color:#38bdf8; }}
  h2 {{ color:#7dd3fc; border-bottom:1px solid #334155; padding-bottom:.3rem; margin-top:2rem; }}
  table {{ border-collapse:collapse; margin:.5rem 0; }}
  th,td {{ border:1px solid #334155; padding:.35rem .7rem; text-align:left; vertical-align:top; }}
  th {{ background:#1e293b; color:#94a3b8; font-weight:600; white-space:nowrap; }}
  ul {{ margin:.3rem 0; padding-left:1.2rem; }}
  a {{ color:#38bdf8; }}
  .meta {{ color:#94a3b8; }}
</style></head><body>
<h1>OSINT-отчёт</h1>
<p class="meta">Email: <b>{email}</b><br>Дата: {date}</p>
{body}
<p class="meta">Сгенерировано EmailOSINT Pro v2.0. Только законное использование.</p>
</body></html>"""

# ══════════════════════════ ИНФРАСТРУКТУРА ══════════════════════════

_resolver = dns.resolver.Resolver()
_resolver.lifetime = 5
_resolver.timeout = 5

CHECKS: dict = {}


def check(name: str):
    """Регистрация проверки в реестре."""
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


class C:
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
    CYAN = "\033[96m"; BOLD = "\033[1m"; END = "\033[0m"

    @classmethod
    def disable(cls):
        for a in ("GREEN", "YELLOW", "RED", "CYAN", "BOLD"):
            setattr(cls, a, "")


def ok(msg):   print(f"{C.GREEN}[+]{C.END} {msg}")
def info(msg):
    if VERBOSE: print(f"{C.CYAN}[*]{C.END} {msg}")
def warn(msg): print(f"{C.YELLOW}[!]{C.END} {msg}")
def err(msg):  print(f"{C.RED}[-]{C.END} {msg}")


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=1.0,
                  status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": CONFIG["user_agent"]})
    if CONFIG["proxy"]:
        s.proxies.update({"http": CONFIG["proxy"], "https": CONFIG["proxy"]})
    return s


# ── Хелперы ──────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def get_local(email): return email.split("@", 1)[0].lower()
def get_domain(email): return email.split("@", 1)[1].lower()
def md5(t):    return hashlib.md5(t.strip().lower().encode()).hexdigest()


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def suggest_domain(domain: str) -> Optional[str]:
    best, dist = None, 99
    for cand in POPULAR_DOMAINS:
        d = levenshtein(domain, cand)
        if d < dist:
            best, dist = cand, d
    return best if 0 < dist <= 2 else None


def _dns_q(name: str, rtype: str) -> list:
    try:
        return [str(r) for r in _resolver.resolve(name, rtype)]
    except Exception:
        return []

# ══════════════════════════ ПРОВЕРКИ ══════════════════════════


@check("format")
def format_check(email, s) -> dict:
    """Синтаксис, одноразовость, роль, опечатки домена"""
    domain = get_domain(email)
    return {
        "valid_syntax": bool(EMAIL_RE.match(email)),
        "disposable": domain in DISPOSABLE_DOMAINS,
        "role_account": get_local(email) in ROLE_ACCOUNTS,
        "domain_typo_suggestion": suggest_domain(domain),
    }


@check("dns")
def dns_check(email, s) -> dict:
    """MX / SPF / DMARC / DKIM — почтовая инфраструктура домена"""
    d = get_domain(email)
    out = {"domain": d, "a": _dns_q(d, "A")}
    out["mx"] = sorted(_dns_q(d, "MX"))
    txt = _dns_q(d, "TXT")
    out["spf"] = [t for t in txt if t.lower().startswith("v=spf1")]
    out["dmarc"] = [t for t in _dns_q(f"_dmarc.{d}", "TXT") if "v=dmarc1" in t.lower()]
    dkim = {sel: recs for sel in DKIM_SELECTORS
            if (recs := _dns_q(f"{sel}._domainkey.{d}", "TXT"))}
    out["dkim_selectors_found"] = list(dkim.keys()) or "не найдено"
    out["has_mx"] = bool(out["mx"])
    return out


@check("smtp")
def smtp_check(email, s) -> dict:
    """SMTP RCPT TO — существует ли ящик (порт 25; крупные провайдеры лгут)"""
    d = get_domain(email)
    try:
        answers = _resolver.resolve(d, "MX")
        host = str(sorted(answers, key=lambda r: r.preference)[0].exchange).rstrip(".")
    except Exception as e:
        return {"verifiable": False, "reason": f"MX не найдены: {e}"}
    result = {"mx_host": host, "verifiable": True}
    try:
        with smtplib.SMTP(host, 25, timeout=20) as srv:
            srv.ehlo("osint.local")
            try:
                srv.starttls(context=ssl._create_unverified_context())
                srv.ehlo("osint.local")
            except smtplib.SMTPException:
                pass
            code, _ = srv.docmd("MAIL", f"FROM:<{CONFIG['smtp_from']}>")
            if code != 250:
                result["result"] = f"отклонён MAIL FROM (код {code})"
                return result
            code, _ = srv.docmd("RCPT", f"TO:<{email}>")
            result["rcpt_code"] = code
            if code in (250, 251):
                result["mailbox_exists"] = True
            elif code in (550, 551, 553):
                result["mailbox_exists"] = False
            else:
                result["result"] = f"неоднозначный ответ (код {code})"
    except (OSError, smtplib.SMTPException) as e:
        result["verifiable"] = False
        result["reason"] = f"{type(e).__name__}: {e}"
    return result


@check("hibp_breaches")
def hibp_breaches(email, s) -> dict:
    """Утечки через HaveIBeenPwned (нужен ключ)"""
    if not CONFIG["hibp_api_key"]:
        return {"skipped": "нет API-ключа HIBP — haveibeenpwned.com/API/Key"}
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email, safe='')}"
    r = s.get(url, headers={"hibp-api-key": CONFIG["hibp_api_key"]},
              params={"truncateResponse": "false"}, timeout=CONFIG["timeout"])
    if r.status_code == 404:
        return {"breached": False, "breaches": []}
    if r.status_code == 401:
        return {"error": "неверный API-ключ HIBP"}
    r.raise_for_status()
    data = r.json()
    return {
        "breached": True, "count": len(data),
        "breaches": [{
            "name": b.get("Title"), "date": b.get("BreachDate"),
            "domain": b.get("Domain"), "pwned_accounts": b.get("PwnCount"),
            "data_exposed": b.get("DataClasses"), "verified": b.get("IsVerified"),
        } for b in data],
    }


@check("hibp_pastes")
def hibp_pastes(email, s) -> dict:
    """Упоминания в paste-сайтах через HIBP (нужен ключ)"""
    if not CONFIG["hibp_api_key"]:
        return {"skipped": "нет API-ключа HIBP"}
    url = f"https://haveibeenpwned.com/api/v3/pasteaccount/{quote(email, safe='')}"
    r = s.get(url, headers={"hibp-api-key": CONFIG["hibp_api_key"]},
              timeout=CONFIG["timeout"])
    if r.status_code == 404:
        return {"found": False, "pastes": []}
    if r.status_code == 401:
        return {"error": "неверный API-ключ HIBP"}
    r.raise_for_status()
    pastes = r.json()
    return {"found": bool(pastes), "count": len(pastes), "pastes": pastes}


@check("xposedornot")
def xposedornot(email, s) -> dict:
    """Утечки через XposedOrNot — БЕСПЛАТНО, без ключа"""
    out = {}
    try:
        r = s.get(f"https://api.xposedornot.com/v1/check-email/{quote_plus(email)}",
                  timeout=CONFIG["timeout"])
        if r.status_code == 200:
            d = r.json()
            out["exposed"] = bool(d.get("breaches_compromised"))
            out["reputation"] = d.get("EmailReputation")
            out["breaches"] = d.get("breaches_compromised", [])
        elif r.status_code == 404:
            out["exposed"] = False
        else:
            out["error"] = f"HTTP {r.status_code}"
        r2 = s.get("https://api.xposedornot.com/v1/breach-analytics",
                   params={"email": email}, timeout=CONFIG["timeout"])
        if r2.status_code == 200:
            m = r2.json().get("BreachMetrics", {})
            out["exposure_score"] = m.get("exposure_score")
            out["pastes_count"] = (m.get("pastees") or {}).get("count", 0)
            out["details"] = [{
                "breach": b.get("breach"), "date": b.get("xposed_date"),
                "data": b.get("xposed_types"),
            } for b in (m.get("breaches_details") or [])[:20]]
    except (requests.RequestException, ValueError) as e:
        out["error"] = str(e)
    return out


@check("gravatar")
def gravatar(email, s) -> dict:
    """Gravatar: аватар, имя, bio, привязанные аккаунты"""
    h = md5(email)
    out = {"md5": h, "avatar": f"https://www.gravatar.com/avatar/{h}?s=400"}
    try:
        r = s.get(f"https://www.gravatar.com/avatar/{h}?d=404&s=1",
                  timeout=CONFIG["timeout"])
        out["avatar_exists"] = (r.status_code == 200)
        if out["avatar_exists"]:
            r = s.get(f"https://www.gravatar.com/{h}.json", timeout=CONFIG["timeout"])
            if r.status_code == 200:
                entry = (r.json().get("entry") or [{}])[0]
                out["profile"] = {
                    "display_name": entry.get("displayName"),
                    "about": entry.get("aboutMe"),
                    "location": entry.get("currentLocation"),
                    "accounts": [a.get("shortname") for a in entry.get("accounts", [])],
                    "urls": [u.get("value") for u in entry.get("urls", [])],
                }
    except (requests.RequestException, ValueError) as e:
        out["error"] = str(e)
    return out


@check("github")
def github(email, s) -> dict:
    """GitHub: профили + коммиты с этим email (часто раскрывают владельца)"""
    out = {"users": [], "commits": []}
    headers = {"Accept": "application/vnd.github+json"}
    if CONFIG["github_token"]:
        headers["Authorization"] = f"Bearer {CONFIG['github_token']}"
    try:
        r = s.get("https://api.github.com/search/users",
                  params={"q": f'"{email}" in:email'},
                  headers=headers, timeout=CONFIG["timeout"])
        if r.status_code == 200:
            out["users"] = [{"login": u["login"], "url": u["html_url"]}
                            for u in r.json().get("items", [])[:5]]
        elif r.status_code == 403:
            out["note"] = "лимит GitHub API — добавьте --github-token"
        r = s.get("https://api.github.com/search/commits",
                  params={"q": f'author-email:"{email}"'},
                  headers=headers, timeout=CONFIG["timeout"])
        if r.status_code == 200:
            for c in r.json().get("items", [])[:10]:
                repo = (c.get("repository") or {}).get("full_name")
                sha = c.get("sha", "")
                out["commits"].append({
                    "repo": repo,
                    "author_name": (c.get("commit") or {}).get("author", {}).get("name"),
                    "date": (c.get("commit") or {}).get("author", {}).get("date"),
                    "url": f"https://github.com/{repo}/commit/{sha}" if repo else None,
                })
    except requests.RequestException as e:
        out["error"] = str(e)
    return out


@check("emailrep")
def emailrep(email, s) -> dict:
    """Репутация email + соцсети, где он используется (emailrep.io, без ключа)"""
    headers = {}
    if CONFIG["emailrep_api_key"]:
        headers["Key"] = CONFIG["emailrep_api_key"]
    try:
        r = s.get(f"https://emailrep.io/{quote_plus(email)}",
                  headers=headers, timeout=CONFIG["timeout"])
        if r.status_code == 429:
            return {"skipped": "лимит emailrep.io исчерпан"}
        if r.status_code != 200:
            return {"skipped": f"emailrep: HTTP {r.status_code}"}
        d = r.json()
        return {
            "reputation": d.get("reputation"),
            "suspicious": d.get("suspicious"),
            "deliverable": d.get("deliverable"),
            "references": d.get("references"),
            "profiles": d.get("profiles", []),   # соцсети с этим email!
        }
    except (requests.RequestException, ValueError) as e:
        return {"error": str(e)}


@check("hunter")
def hunter(email, s) -> dict:
    """Hunter.io email-verifier (нужен ключ)"""
    if not CONFIG["hunter_api_key"]:
        return {"skipped": "нет ключа hunter.io"}
    try:
        r = s.get("https://api.hunter.io/v2/email-verifier",
                  params={"email": email, "api_key": CONFIG["hunter_api_key"]},
                  timeout=CONFIG["timeout"])
        r.raise_for_status()
        d = r.json().get("data", {})
        return {
            "result": d.get("result"),
            "score": d.get("score"),
            "disposable": d.get("disposable"),
            "webmail": d.get("webmail"),
            "sources": [x.get("uri") for x in (d.get("sources") or [])][:10],
        }
    except requests.RequestException as e:
        return {"error": str(e)}


@check("whois")
def whois_check(email, s) -> dict:
    """WHOIS домена"""
    try:
        import whois
    except ImportError:
        return {"skipped": "pip install python-whois"}
    try:
        w = whois.whois(get_domain(email))

        def fmt(x):
            if isinstance(x, list):
                x = x[0]
            return str(x)[:10] if x else None

        return {
            "registrar": w.get("registrar"),
            "created": fmt(w.get("creation_date")),
            "expires": fmt(w.get("expiration_date")),
            "org": w.get("org") or w.get("organization"),
            "country": w.get("country"),
            "name_servers": w.get("name_servers"),
        }
    except Exception as e:
        return {"error": str(e)[:200]}

# ══════════════════════════ ГЕНЕРАТОРЫ ══════════════════════════


def build_social_links(email) -> dict:
    u, q = get_local(email), quote_plus(email)
    return {name: url.format(u=u, q=q) for name, url in SOCIAL_PLATFORMS.items()}


def build_dorks(email) -> list:
    u, d = get_local(email), get_domain(email)
    out = []
    for t in GOOGLE_DORKS:
        query = t.format(email=email, u=u, d=d)
        out.append({"dork": query,
                    "url": f"https://www.google.com/search?q={quote_plus(query)}"})
    return out


def run_holehe(email) -> str:
    """Интеграция с holehe — проверка регистрации на 120+ сайтах"""
    if shutil.which("holehe") is None:
        return "holehe не установлен: pip install holehe"
    try:
        out = subprocess.run(["holehe", email, "--only-used", "--no-color"],
                             capture_output=True, text=True, timeout=600)
        return out.stdout or "(нет данных)"
    except subprocess.TimeoutExpired:
        return "holehe: превышен таймаут"


def build_summary(r: dict) -> dict:
    hibp = r.get("hibp_breaches") or {}
    xon = r.get("xposedornot") or {}
    rep = r.get("emailrep") or {}
    gh = r.get("github") or {}
    fmt = r.get("format") or {}
    total = len(hibp.get("breaches") or []) + len(xon.get("breaches") or [])
    score = 0
    if total:
        score += min(total * 10, 40)
    if rep.get("suspicious"):
        score += 25
    if rep.get("reputation") == "low":
        score += 20
    if fmt.get("disposable"):
        score += 30
    if fmt.get("role_account"):
        score += 5
    if gh.get("users") or gh.get("commits"):
        score += 5
    level = "низкий" if score < 25 else "средний" if score < 55 else "высокий"
    return {
        "total_breaches": total,
        "reputation": rep.get("reputation"),
        "suspicious": rep.get("suspicious"),
        "risk_score": f"{min(score, 100)}/100",
        "risk_level": level,
    }

# ══════════════════════════ ОРКЕСТРАТОР ══════════════════════════


def run_osint(email: str, selected: Optional[list] = None) -> dict:
    report = {
        "tool": "EmailOSINT Pro v2.0",
        "email": email,
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
    }
    session = make_session()

    todo = dict(CHECKS)
    if selected:
        todo = {k: v for k, v in todo.items() if k in selected}
    if not CONFIG["smtp_verify"]:
        todo.pop("smtp", None)

    total, done = len(todo), 0
    with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as pool:
        futures = {pool.submit(fn, email, session): name for name, fn in todo.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            done += 1
            try:
                report[name] = fut.result()
            except Exception as e:
                report[name] = {"error": f"{type(e).__name__}: {e}"}
            info(f"[{done}/{total}] {name} — готово")

    report["social_links"] = build_social_links(email)
    report["google_dorks"] = build_dorks(email)
    report["summary"] = build_summary(report)
    return report

# ══════════════════════════ ЭКСПОРТ ══════════════════════════


def save_json(report, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)


def save_txt(report, path):
    W = 72
    lines = ["=" * W,
             f"  OSINT-ОТЧЁТ: {report.get('email')}",
             f"  Дата: {report.get('scanned_at')}",
             "=" * W]

    def emit(obj, indent=0):
        pad = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)) and v:
                    lines.append(f"{pad}{k}:")
                    emit(v, indent + 1)
                else:
                    lines.append(f"{pad}{k}: {v if v is not None else '—'}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)) and item:
                    emit(item, indent)
                    lines.append("")
                else:
                    lines.append(f"{pad}- {item}")
        else:
            lines.append(f"{pad}{obj}")

    for section, val in report.items():
        lines += ["", f"[{section.upper()}]", "-" * W]
        emit(val)
    lines += ["", "=" * W]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def save_csv(report, path):
    rows = []

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(f"{prefix}[{i}]", v)
        else:
            rows.append({"field": prefix, "value": obj})

    walk("", report)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["field", "value"])
        w.writeheader()
        w.writerows(rows)


def save_html(report, path):
    def render(v):
        if isinstance(v, dict):
            rows = "".join(f"<tr><th>{k}</th><td>{render(x)}</td></tr>"
                           for k, x in v.items())
            return f"<table>{rows}</table>"
        if isinstance(v, list):
            return "<ul>" + "".join(f"<li>{render(i)}</li>" for i in v) + "</ul>"
        return str(v)

    sections = []
    for name, val in report.items():
        if name == "social_links" and isinstance(val, dict):
            body = "<ul>" + "".join(
                f'<li><a href="{u}" target="_blank">{k}</a></li>'
                for k, u in val.items()) + "</ul>"
        elif name == "google_dorks" and isinstance(val, list):
            body = "<ul>" + "".join(
                f'<li><a href="{d["url"]}" target="_blank">{d["dork"]}</a></li>'
                for d in val) + "</ul>"
        else:
            body = render(val)
        sections.append(f"<h2>{name}</h2>{body}")

    html = HTML_TEMPLATE.format(email=report.get("email"),
                                date=report.get("scanned_at"),
                                body="".join(sections))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

# ══════════════════════════ CLI ══════════════════════════


def parse_args():
    p = argparse.ArgumentParser(
        description="EmailOSINT Pro — анализ email по открытым источникам",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры:
  python email_osint.py user@example.com
  python email_osint.py user@example.com --hibp-key XXX -f json,html
  python email_osint.py user@example.com --smtp --proxy socks5://127.0.0.1:9050
  python email_osint.py user@example.com --only dns,gravatar,github --holehe""")
    p.add_argument("email", nargs="?", help="email для анализа")
    p.add_argument("-o", "--out", default="osint_report", help="базовое имя отчёта")
    p.add_argument("-f", "--formats", default="json,txt",
                   help="форматы: json,csv,html,txt (через запятую)")
    p.add_argument("--hibp-key", help="API-ключ haveibeenpwned.com")
    p.add_argument("--hunter-key", help="API-ключ hunter.io")
    p.add_argument("--emailrep-key", help="API-ключ emailrep.io")
    p.add_argument("--github-token", help="GitHub personal access token")
    p.add_argument("--proxy", help="прокси: socks5://127.0.0.1:9050")
    p.add_argument("--smtp", action="store_true",
                   help="SMTP-проверка ящика (порт 25, результат не гарантирован)")
    p.add_argument("--smtp-from", default=CONFIG["smtp_from"],
                   help="адрес MAIL FROM для SMTP-проверки")
    p.add_argument("--holehe", action="store_true",
                   help="запустить holehe (pip install holehe)")
    p.add_argument("--only", help="только эти проверки, через запятую")
    p.add_argument("-w", "--workers", type=int, default=6)
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--list", action="store_true", help="показать список проверок")
    return p.parse_args()


def main():
    global VERBOSE
    args = parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()
    if args.quiet:
        VERBOSE = False

    if args.list:
        print("Доступные проверки:")
        for name, fn in CHECKS.items():
            doc = (fn.__doc__ or "").strip().split("\n")[0]
            print(f"  {name:<16} {doc}")
        return

    email = (args.email or input("Введите email для анализа: ")).strip().lower()
    if not re.match(EMAIL_RE, email):
        err(f"Невалидный формат email: {email}")
        sys.exit(1)

    CONFIG.update(
        hibp_api_key=args.hibp_key, hunter_api_key=args.hunter_key,
        emailrep_api_key=args.emailrep_key, github_token=args.github_token,
        proxy=args.proxy, smtp_verify=args.smtp, smtp_from=args.smtp_from,
        max_workers=args.workers,
    )

    print(f"\n{C.CYAN}{'═' * 60}")
    print(f"  EmailOSINT Pro v2.0  |  цель: {email}")
    print(f"{'═' * 60}{C.END}\n")
    if args.smtp:
        warn("SMTP-проверка включена: порт 25 часто закрыт, крупные "
             "провайдеры отвечают 250 на любой адрес\n")

    report = run_osint(email, selected=args.only.split(",") if args.only else None)

    if args.holehe:
        info("Запуск holehe (это долго, до 10 минут)...")
        report["holehe"] = run_holehe(email)

    writers = {"json": save_json, "txt": save_txt,
               "csv": save_csv, "html": save_html}
    for fmt in [x.strip() for x in args.formats.split(",") if x.strip()]:
        w = writers.get(fmt)
        if not w:
            warn(f"неизвестный формат: {fmt}")
            continue
        path = f"{args.out}.{fmt}"
        w(report, path)
        ok(f"сохранено: {path}")

    s = report["summary"]
    print(f"\n{C.BOLD}ИТОГ:{C.END} утечек — {s['total_breaches']} | "
          f"репутация — {s['reputation']} | "
          f"риск — {s['risk_level']} ({s['risk_score']})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Прервано пользователем")
        sys.exit(130)