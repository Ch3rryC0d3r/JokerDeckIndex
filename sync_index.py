import os
import json
import urllib.request
import time

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JokerDeck-Indexer"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

def main():
    json_file = "mod.json"
    if not os.path.exists(json_file):
        print("Error: mod.json database file not found.")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        try:
            mods_data = json.load(f)
        except json.JSONDecodeError:
            print("Error: mod.json is empty or corrupted.")
            return

    updated_count = 0
    print(f"Starting background check for {len(mods_data)} mods...")

    for mod in mods_data:
        git_url = mod.get("git_url", "").strip().rstrip("/")
        if not git_url:
            continue

        manifest_data = None

        # Route 1: Alternative Git host tracking (git.gay, codeberg, etc.)
        if "github.com" not in git_url.lower():
            possible_urls = [
                f"{git_url}/raw/branch/main/metadata.json",
                f"{git_url}/raw/branch/master/metadata.json",
                f"{git_url}/raw/branch/main/mod.json",
                f"{git_url}/raw/branch/master/mod.json"
            ]
            for url in possible_urls:
                test_data = fetch_json(url)
                if test_data and any(k in test_data for k in ["id", "name", "display_name"]):
                    manifest_data = test_data
                    break

        # Route 2: GitHub Raw handling (Bypasses API limits completely!)
        else:
            # Changes https://github.com/owner/repo to owner/repo
            repo_path = git_url.replace("https://github.com/", "")
            possible_urls = [
                f"https://raw.githubusercontent.com/{repo_path}/main/metadata.json",
                f"https://raw.githubusercontent.com/{repo_path}/master/metadata.json",
                f"https://raw.githubusercontent.com/{repo_path}/main/mod.json",
                f"https://raw.githubusercontent.com/{repo_path}/master/mod.json"
            ]
            for url in possible_urls:
                test_data = fetch_json(url)
                if test_data and any(k in test_data for k in ["id", "name", "display_name"]):
                    manifest_data = test_data
                    break

        # If we successfully parsed their remote repo file, look for updates
        if manifest_data:
            new_version = str(manifest_data.get("version", mod.get("version", "1.0.0"))).strip()
            new_desc = str(manifest_data.get("description", mod.get("description", ""))).strip()
            
            # Check if fields changed
            if new_version != mod.get("version") or new_desc != mod.get("description"):
                print(f"Update found for {mod['name']}: v{mod.get('version')} -> v{new_version}")
                mod["version"] = new_version
                mod["description"] = new_desc
                updated_count += 1
        
        # Slower parsing intervals to respect target servers
        time.sleep(1)

    # Save changes back to the index database if entries were modified
    if updated_count > 0:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(mods_data, f, indent=2, ensure_ascii=False)
        print(f"Sync complete! Updated {updated_count} profiles.")
    else:
        print("Sync complete! All mods are completely up to date.")

if __name__ == "__main__":
    main()
