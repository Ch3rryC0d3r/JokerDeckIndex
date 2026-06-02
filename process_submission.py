import os
import sys
import json
import re

def main():
    # GitHub Actions passes the issue body as an environment variable or file
    issue_body_path = os.getenv("ISSUE_BODY_PATH")
    if not issue_body_path or not os.path.exists(issue_body_path):
        print("Error: Issue body data missing.")
        sys.exit(1)

    with open(issue_body_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Helper function to extract form responses parsed by GitHub
    def get_field(label):
        pattern = rf"### {label}\s*\n\s*(.+?)(?=\n\s*### |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    try:
        mod_id = get_field("Mod ID")
        mod_name = get_field("Display Name")
        author = get_field("Author\(s\)")
        description = get_field("Description")
        version = get_field("Current Version")
        git_url = get_field("GitHub Repository URL")

        if not (mod_id and mod_name and git_url):
            raise ValueError("Required fields are missing or broken.")

        new_mod = {
            "id": mod_id,
            "name": mod_name,
            "author": author,
            "description": description,
            "version": version,
            "git_url": git_url.rstrip("/")
        }

        # Load existing index file
        json_file = "mods.json"
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    mods_data = json.load(f)
                except json.JSONDecodeError:
                    mods_data = []
        else:
            mods_data = []

        # Check for duplication updates or additions
        existing_index = next((i for i, m in enumerate(mods_data) if m["id"].lower() == mod_id.lower()), None)
        if existing_index is not None:
            mods_data[existing_index] = new_mod
            print(f"Updating existing entry: {mod_name}")
        else:
            mods_data.append(new_mod)
            print(f"Adding new entry: {mod_name}")

        # Save back out beautifully formatted
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(mods_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"Execution Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()