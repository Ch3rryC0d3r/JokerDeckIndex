import os
import sys
import json
import re
import urllib.request

def fetch_json_api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "JokerDeck-Indexer"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))

def main():
    issue_body_path = os.getenv("ISSUE_BODY_PATH")
    if not issue_body_path or not os.path.exists(issue_body_path):
        print("Error: Issue body data missing.")
        sys.exit(1)

    with open(issue_body_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match URLs for GitHub or other Git platforms (like git.gay, codeberg, etc.)
    url_match = re.search(rf"### GitHub Repository URL\s*\n\s*(https?://[^\s\n\r]+)", content)
    if not url_match:
        print("Error: Could not extract a valid repository URL from submission.")
        sys.exit(1)
    
    git_url = url_match.group(1).strip().rstrip("/")
    
    manifest_data = None
    chosen_file = "Direct Web Fetch"

    if "github.com" not in git_url.lower():
        print(f"Detected alternative Git host target: {git_url}")
        possible_raw_urls = [
            f"{git_url}/raw/branch/main/metadata.json",
            f"{git_url}/raw/branch/master/metadata.json",
            f"{git_url}/raw/branch/main/mod.json",
            f"{git_url}/raw/branch/master/mod.json"
        ]
        
        for raw_url in possible_raw_urls:
            try:
                test_data = fetch_json_api(raw_url)
                if any(k in test_data for k in ["id", "name", "display_name"]):
                    manifest_data = test_data
                    chosen_file = raw_url.split("/")[-1]
                    print(f"Successfully harvested manifest from raw URL: {raw_url}")
                    break
            except Exception:
                continue

    else:
        path_parts = git_url.replace("https://github.com/", "").split("/")
        if len(path_parts) < 2:
            print(f"Error: Invalid GitHub layout format: {git_url}")
            sys.exit(1)
            
        owner, repo = path_parts[0], path_parts[1]

        try:
            # ask GitHub API for repository details to find the true default branch
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_info = fetch_json_api(repo_api_url)
            default_branch = repo_info.get("default_branch", "main")
            
            # grab the directory structure tree of the root folder
            tree_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents?ref={default_branch}"
            directory_contents = fetch_json_api(tree_api_url)
            
            # filter down to find any JSON files living in the root directory
            json_files = [item["name"] for item in directory_contents if item["type"] == "file" and item["name"].lower().endswith(".json")]
            
            if not json_files:
                raise Exception("No JSON files found in the root of the repository folder.")

            for file_name in json_files:
                raw_json_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{file_name}"
                try:
                    test_data = fetch_json_api(raw_json_url)
                    if any(k in test_data for k in ["id", "name", "display_name"]):
                        manifest_data = test_data
                        chosen_file = file_name
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"GitHub API Scraper Endpoint Failure: {e}")

    # Verify if any data was successfully captured across both tracking routes
    if not manifest_data:
        print("Error: Failed to extract a valid mod manifest structure from the target destination.")
        sys.exit(1)

    print(f"Successfully located manifest matching target: {chosen_file}")

    # Extract fields matching your fallback criteria normalization mapping rules
    mod_id = manifest_data.get("id") or manifest_data.get("name") or manifest_data.get("display_name")
    mod_name = manifest_data.get("name") or manifest_data.get("display_name") or manifest_data.get("id")
    
    # Format author if it's an array/list versus a flat string
    author_raw = manifest_data.get("author", "Unknown")
    author = ", ".join(author_raw) if isinstance(author_raw, list) else str(author_raw)

    # Build the final entry for your master layout index file
    new_mod = {
        "id": str(mod_id).strip(),
        "name": str(mod_name).strip(),
        "author": author.strip(),
        "description": str(manifest_data.get("description", "")).strip(),
        "version": str(manifest_data.get("version", "1.0.0")).strip(),
        "git_url": git_url
    }

    json_file = "mod.json"
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                mods_data = json.load(f)
            except json.JSONDecodeError:
                mods_data = []
    else:
        mods_data = []

    existing_idx = next((i for i, m in enumerate(mods_data) if m["id"].lower() == new_mod["id"].lower()), None)
    if existing_idx is not None:
        mods_data[existing_idx] = new_mod
        print(f"Overwriting database profile: {new_mod['name']}")
    else:
        mods_data.append(new_mod)
        print(f"Injecting brand new database entry: {new_mod['name']}")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(mods_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
