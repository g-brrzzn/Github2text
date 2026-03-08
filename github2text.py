#!/usr/bin/env python3
"""
github_export.py

Collects repositories (public or public+private) from the authenticated GitHub account
or from a public user and generates:

 - data.json (raw structured repository data)
 - summary.txt (textual summary)
 - report.md (markdown report per repository)

Usage:

export GITHUB_TOKEN="ghp_xxx..."
python github_export.py --username my_user --output-dir ./out
"""

import requests
import time
import os
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone

API_ROOT = "https://api.github.com"


def get_auth_session(token):
    session = requests.Session()

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-export-script"
    }

    if token:
        headers["Authorization"] = f"token {token}"

    session.headers.update(headers)

    return session


def handle_rate_limit(resp):
    if resp.status_code == 403:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining == "0" and reset:
            reset_ts = int(reset)
            wait_seconds = max(0, reset_ts - int(time.time()) + 1)
            raise RuntimeError(f"Rate limit exceeded. Reset in {wait_seconds}s")
    resp.raise_for_status()


def fetch_all_repos(session, username=None):
    """
    Fetch all repositories accessible to the authenticated user.
    Includes public and private repositories when token permissions allow.
    """
    repos = []
    page = 1
    per_page = 100

    auth_token = session.headers.get("Authorization")

    if auth_token:
        url = f"{API_ROOT}/user/repos"
        params = {
            "per_page": per_page,
            "page": page,
            "sort": "pushed",
            "visibility": "all",
            "affiliation": "owner,collaborator,organization_member"
        }
    else:
        if not username:
            raise ValueError("Username required when no token is provided.")
        url = f"{API_ROOT}/users/{username}/repos"
        params = {
            "per_page": per_page,
            "page": page,
            "type": "all",
            "sort": "pushed"
        }

    while True:
        params["page"] = page
        resp = session.get(url, params=params)

        if resp.status_code == 401:
            raise RuntimeError("Authentication failed. Check token.")

        handle_rate_limit(resp)

        page_data = resp.json()

        if not isinstance(page_data, list):
            raise RuntimeError(f"Unexpected API response: {page_data}")

        repos.extend(page_data)

        if len(page_data) < per_page:
            break

        page += 1

    return repos


def fetch_repo_languages(session, languages_url):
    resp = session.get(languages_url)
    handle_rate_limit(resp)
    return resp.json()


def fetch_repo_topics(session, owner, repo):
    url = f"{API_ROOT}/repos/{owner}/{repo}/topics"
    headers = {"Accept": "application/vnd.github.mercy-preview+json"}
    resp = session.get(url, headers=headers)
    if resp.status_code == 404:
        return []
    handle_rate_limit(resp)
    data = resp.json()
    return data.get("names", [])


def generate_text_summary(repos):
    total = len(repos)
    public = sum(1 for r in repos if r.get("private") is False)
    private = total - public

    languages_agg = defaultdict(int)
    stars = []
    forks = []

    recent = sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True)

    for repo in repos:
        langs = repo.get("languages") or {}
        for lang, bytes_ in langs.items():
            languages_agg[lang] += bytes_
        stars.append((repo.get("stargazers_count", 0), repo["name"]))
        forks.append((repo.get("forks_count", 0), repo["name"]))

    top_languages = sorted(languages_agg.items(), key=lambda x: x[1], reverse=True)[:10]
    top_stars = sorted(stars, reverse=True)[:10]
    top_forks = sorted(forks, reverse=True)[:10]

    lines = []
    lines.append("GitHub Account Summary")
    lines.append("----------------------")
    lines.append(f"Total repositories: {total}")
    lines.append(f"Public repositories: {public}")
    lines.append(f"Private repositories: {private}")
    lines.append("")

    if top_languages:
        lang_list = ", ".join(f"{lang} ({size} bytes)" for lang, size in top_languages)
        lines.append(f"Top languages by code size: {lang_list}")
    else:
        lines.append("No language statistics available")

    lines.append("")

    if top_stars:
        lines.append("Top repositories by stars:")
        for star, name in top_stars[:6]:
            lines.append(f"- {name}: {star} stars")

    if top_forks:
        lines.append("")
        lines.append("Top repositories by forks:")
        for fork, name in top_forks[:6]:
            lines.append(f"- {name}: {fork} forks")

    lines.append("")
    lines.append("Most recently pushed repositories:")
    for r in recent[:6]:
        pushed = r.get("pushed_at") or "unknown"
        lines.append(f"- {r['name']} (pushed: {pushed})")

    lines.append("")
    lines.append("Repository details:")
    lines.append("")
    for r in repos:
        primary = r.get("primary_language") or "unknown"
        topics = ", ".join(r.get("topics") or [])
        lines.append(
            f"- {r['name']} | "
            f"lang={primary} | "
            f"stars={r.get('stargazers_count',0)} | "
            f"forks={r.get('forks_count',0)} | "
            f"private={r.get('private')} | "
            f"topics=[{topics}] | "
            f"{r.get('description') or 'no description'}"
        )

    lines.append("")
    return "\n".join(lines)


def format_repo_markdown(repo):
    md = []
    md.append(f"## {repo['name']}")
    md.append("")
    md.append(f"- URL: {repo.get('html_url')}")
    md.append(f"- Visibility: {repo.get('visibility')}")
    md.append(f"- Private: {repo.get('private')}")
    md.append(f"- Description: {repo.get('description') or '—'}")
    md.append(f"- Primary language: {repo.get('primary_language') or '—'}")
    md.append(f"- Languages breakdown: {json.dumps(repo.get('languages') or {}, ensure_ascii=False)}")
    md.append(f"- Stars: {repo.get('stargazers_count',0)}")
    md.append(f"- Forks: {repo.get('forks_count',0)}")
    md.append(f"- Watchers: {repo.get('watchers_count',0)}")
    md.append(f"- Open issues: {repo.get('open_issues_count',0)}")
    md.append(f"- Size (KB): {repo.get('size')}")
    md.append(f"- Created at: {repo.get('created_at')}")
    md.append(f"- Last pushed at: {repo.get('pushed_at')}")
    md.append(f"- Default branch: {repo.get('default_branch')}")
    md.append(f"- Topics: {', '.join(repo.get('topics') or []) or '—'}")
    md.append("")
    return "\n".join(md)


def main(args):
    token = args.token or os.environ.get("GITHUB_TOKEN")
    session = get_auth_session(token)

    if token:
        endpoint = "/user/repos"
        target_info = "authenticated account (via Token)"
    else:
        endpoint = f"/users/{args.username}/repos"
        target_info = f"user '{args.username}' (public)"

    # --- START OF LOADING FEEDBACK ---
    print("\n" + "="*40)
    print("🚀 Starting GitHub Exporter")
    print("="*40)
    print(f"📁 Output directory : {args.output_dir}")
    print(f"🔑 Using token      : {'YES' if token else 'NO'}")
    print(f"🎯 Target           : {target_info}")
    print(f"📡 API Endpoint     : {API_ROOT}{endpoint}")
    print("-" * 40)
    print("⏳ Fetching repositories from GitHub API...")
    print("⏳ Collecting languages and topics for each repository...")
    print("⚠️  This might take a few seconds depending on the number of repositories. Please wait...\n")
    # --- END OF LOADING FEEDBACK ---

    # fetch repos
    try:
        repos_raw = fetch_all_repos(session, username=args.username)
        print(f"✅ Success: {len(repos_raw)} repositories found! Processing data...")
    except Exception as e:
        print("❌ Error fetching repositories:", e)
        return

    cleaned = []
    for i, repo in enumerate(repos_raw, 1):
        owner = repo["owner"]["login"]
        name = repo["name"]
        
        # Optional terminal feedback to show progress
        print(f"  -> Processing [{i}/{len(repos_raw)}]: {name}", end="\r")

        languages = {}
        try:
            languages = fetch_repo_languages(session, repo["languages_url"])
        except Exception as e:
            pass # Silencing the warning print to not break the progress bar

        primary = None
        if languages:
            primary = max(languages.items(), key=lambda x: x[1])[0]
        else:
            primary = repo.get("language")

        topics = []
        try:
            topics = fetch_repo_topics(session, owner, name)
        except Exception:
            topics = []

        cleaned_repo = {
            "name": name,
            "full_name": repo.get("full_name"),
            "owner": owner,
            "private": repo.get("private", False),
            "is_public": not repo.get("private", False),
            "is_private": repo.get("private", False),
            "visibility": repo.get("visibility", "public"),
            "description": repo.get("description"),
            "html_url": repo.get("html_url"),
            "stargazers_count": repo.get("stargazers_count", 0),
            "forks_count": repo.get("forks_count", 0),
            "watchers_count": repo.get("watchers_count", 0),
            "open_issues_count": repo.get("open_issues_count", 0),
            "size": repo.get("size"),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
            "default_branch": repo.get("default_branch"),
            "language_hint": repo.get("language"),
            "primary_language": primary,
            "languages": languages,
            "topics": topics,
            "license": (repo.get("license") or {}).get("name"),
            "archived": repo.get("archived", False),
            "fork": repo.get("fork", False)
        }

        cleaned.append(cleaned_repo)

    print("\n\n💾 Saving files...")

    os.makedirs(args.output_dir, exist_ok=True)
    raw_path = os.path.join(args.output_dir, "data.json")

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    output = {
        "repo_count": len(cleaned),
        "generated_at": generated_at,
        "repositories": cleaned
    }

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"📄 Raw data saved to: {raw_path}")

    text_summary = generate_text_summary(cleaned)
    summary_path = os.path.join(args.output_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(text_summary)
    print(f"📄 Text summary saved to: {summary_path}")

    md_lines = []
    md_lines.append("# GitHub Repositories Report")
    md_lines.append("")
    md_lines.append(f"Generated at {generated_at}")
    md_lines.append(f"Total repositories: {len(cleaned)}")
    md_lines.append("")

    for repo in cleaned:
        md_lines.append(format_repo_markdown(repo))

    md_path = os.path.join(args.output_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"📄 Markdown report saved to: {md_path}")

    print("\n✨ Finished successfully!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export GitHub repos and generate a text summary")
    parser.add_argument("--username", "-u", help="GitHub username (used if no token)")
    parser.add_argument("--token", "-t", help="GitHub token (or use GITHUB_TOKEN env variable)")
    parser.add_argument("--output-dir", "-o", default="./github_export_out", help="Output directory")
    args = parser.parse_args()
    main(args)