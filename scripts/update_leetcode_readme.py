#!/usr/bin/env python3
import os
import sys
import json
import datetime
import requests
import re

LEETCODE_USER = os.environ.get("LEETCODE_USERNAME") or "Vishnukant-Bajpai"
README_PATH = os.environ.get("README_PATH") or "README.md"

START_MARKER = "<!-- LEETCODE_ROADMAP:START -->"
END_MARKER = "<!-- LEETCODE_ROADMAP:END -->"

GRAPHQL_URL = "https://leetcode.com/graphql"
GRAPHQL_QUERY = """
query userProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submitStats {
      acSubmissionNum {
        difficulty
        count
        submissions
      }
      totalSubmissionNum
    }
    profile {
      realName
      userSlug
      ranking
    }
  }
  userProfileCalendar(username: $username) {
    streak
  }
  allQuestionsCount {
    difficulty
    count
  }
}
"""

def fetch_stats(username):
    try:
        resp = requests.post(GRAPHQL_URL, json={"query": GRAPHQL_QUERY, "variables": {"username": username}},
                             headers={"Content-Type": "application/json"}, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("GraphQL request failed:", e, file=sys.stderr)
        return None

def parse_stats(data):
    result = {}
    try:
        d = data.get("data", {})
        matched = d.get("matchedUser") or {}
        submit_stats = matched.get("submitStats", {}) or {}
        ac_list = submit_stats.get("acSubmissionNum", []) or []

        # Find counts
        counts = {}
        total_solved = 0
        for item in ac_list:
            diff = item.get("difficulty")
            cnt = item.get("count", 0)
            if diff is None:
                continue
            counts[diff] = cnt
            if diff.lower() == "all":
                total_solved = cnt

        # fallback: sum difficulties if 'All' missing
        if total_solved == 0:
            total_solved = sum([v for k, v in counts.items() if k.lower() != "all"])

        # allQuestionsCount for total questions per difficulty
        all_q = {it.get("difficulty"): it.get("count") for it in (d.get("allQuestionsCount") or [])}

        streak = None
        calendar = d.get("userProfileCalendar")
        if calendar and isinstance(calendar, dict):
            streak = calendar.get("streak")
        # fallback: try deeper nested
        try:
            if streak is None and calendar and isinstance(calendar, list) and len(calendar) > 0:
                streak = calendar[0].get("streak")
        except Exception:
            pass

        result = {
            "username": matched.get("username"),
            "total_solved": total_solved,
            "difficulty_counts": {
                "Easy": counts.get("Easy", counts.get("easy", 0)),
                "Medium": counts.get("Medium", counts.get("medium", 0)),
                "Hard": counts.get("Hard", counts.get("hard", 0)),
            },
            "all_questions": {
                "Easy": all_q.get("Easy", all_q.get("easy", 0)),
                "Medium": all_q.get("Medium", all_q.get("medium", 0)),
                "Hard": all_q.get("Hard", all_q.get("hard", 0)),
            },
            "streak": streak
        }
    except Exception as e:
        print("Failed to parse stats:", e, file=sys.stderr)
    return result

def build_block(stats):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total = stats.get("total_solved", 0)
    streak = stats.get("streak")
    if streak is None:
        streak_display = "N/A"
    else:
        streak_display = f"{streak} day(s)"
    easy = stats["difficulty_counts"].get("Easy", 0)
    medium = stats["difficulty_counts"].get("Medium", 0)
    hard = stats["difficulty_counts"].get("Hard", 0)
    all_easy = stats["all_questions"].get("Easy", "—")
    all_med = stats["all_questions"].get("Medium", "—")
    all_hard = stats["all_questions"].get("Hard", "—")

    block = []
    block.append(START_MARKER)
    block.append("")
    block.append("## LeetCode Roadmap")
    block.append("")
    block.append(f"- Username: **{LEETCODE_USER}**")
    block.append(f"- Solved: **{total}**")
    block.append(f"- Current streak: **{streak_display}**")
    block.append("")
    block.append("Difficulty breakdown (solved / total):")
    block.append("")
    block.append(f"- Easy: **{easy}** / {all_easy}")
    block.append(f"- Medium: **{medium}** / {all_med}")
    block.append(f"- Hard: **{hard}** / {all_hard}")
    block.append("")
    block.append(f"_Last updated: {now}_")
    block.append("")
    block.append(END_MARKER)

    return "\n".join(block)

def update_readme(path, new_block):
    if not os.path.exists(path):
        # create README with the block if not exist
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_block + "\n")
        print("README created with LeetCode block.")
        return True

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER in content and END_MARKER in content:
        pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
        new_content = pattern.sub(new_block, content)
    else:
        # append block at end
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README updated.")
        return True
    else:
        print("No changes were necessary.")
        return False

def main():
    print("Fetching stats for", LEETCODE_USER)
    data = fetch_stats(LEETCODE_USER)
    if not data:
        print("Failed to fetch data.", file=sys.stderr)
        sys.exit(1)

    stats = parse_stats(data)
    block = build_block(stats)
    changed = update_readme(README_PATH, block)
    if changed:
        sys.exit(0)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
