#!/usr/bin/env python3
"""Keep the numbers in the profile README current.

Two figures come straight from GitHub on every run: commits made this year and
merged pull requests. Three figures only a human knows (projects built, live
apps, tests on one solo app) are read from stats.json so there is one place to
edit them.

Run by .github/workflows/update-stats.yml, and safe to run by hand:

    GITHUB_TOKEN=... python scripts/update_stats.py
"""

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

USER = "ShervinBabaei2007"
README_PATH = "README.md"
STATS_PATH = "stats.json"
START = "<!-- STATS:START -->"
END = "<!-- STATS:END -->"
API = "https://api.github.com"


def token():
    value = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not value:
        sys.exit("GITHUB_TOKEN is not set.")
    return value


def request(path, payload=None):
    headers = {
        "Authorization": f"bearer {token()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"{path} failed: {error.code} {error.reason}")


def commits_this_year():
    now = dt.datetime.now(dt.timezone.utc)
    start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
        }
      }
    }"""
    result = request(
        "/graphql",
        {
            "query": query,
            "variables": {
                "login": USER,
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": now.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    try:
        return result["data"]["user"]["contributionsCollection"][
            "totalCommitContributions"
        ]
    except (KeyError, TypeError):
        sys.exit(f"Unexpected GraphQL answer: {result}")


def merged_pull_requests():
    query = f"is:pr+author:{USER}+is:merged"
    return request(f"/search/issues?q={query}&per_page=1")["total_count"]


def render(numbers):
    cells = [
        (f'{numbers["commits"]:,}', "commits this year"),
        (f'{numbers["pull_requests"]:,}', "pull requests merged"),
        (f'{numbers["projects"]:,}', "projects built"),
        (f'{numbers["apps"]:,}', "live apps"),
        (f'{numbers["tests"]:,}', "tests on one solo app"),
    ]
    row = "\n".join(
        f'    <td align="center"><h3>{value}</h3><sub>{label}</sub></td>'
        for value, label in cells
    )
    return "\n".join(
        [
            START,
            '<div align="center">',
            '<table align="center">',
            "  <tr>",
            row,
            "  </tr>",
            "</table>",
            "</div>",
            END,
        ]
    )


def main():
    with open(STATS_PATH, encoding="utf-8") as handle:
        curated = json.load(handle)

    numbers = {
        "commits": commits_this_year(),
        "pull_requests": merged_pull_requests(),
        "projects": curated["projects_built"],
        "apps": curated["live_apps"],
        "tests": curated["tests_on_one_solo_app"],
    }

    with open(README_PATH, encoding="utf-8") as handle:
        readme = handle.read()

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(readme):
        sys.exit(f"Could not find {START} ... {END} in {README_PATH}.")

    updated = pattern.sub(render(numbers), readme)
    if updated == readme:
        print("Numbers are already current.")
        return

    with open(README_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    print(
        "Updated: {commits:,} commits, {pull_requests:,} merged pull requests, "
        "{projects} projects, {apps} live apps, {tests:,} tests.".format(**numbers)
    )


if __name__ == "__main__":
    main()
