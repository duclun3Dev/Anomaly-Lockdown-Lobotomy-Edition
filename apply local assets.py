import json
import os
from pathlib import Path
import urllib.parse
import msvcrt

def scan_and_replace(items_list, target_name, dynamic_path, collected_names=None):
    """
    Recursively digs through JSON nested folders/groups to find a name match.
    Also collects all profile names encountered to identify unmatched files later.
    """
    if collected_names is None:
        collected_names = set()
        
    modified_count = 0
    if not isinstance(items_list, list):
        return modified_count, collected_names

    for item in items_list:
        if not isinstance(item, dict):
            continue
            
        if "name" in item:
            current_name = str(item["name"]).strip().lower()
            collected_names.add(current_name)
            
            # If names match, switch mode to local and apply the directory path
            if current_name == target_name:
                item["mode"] = "local"
                item["enabled"] = True
                item["local_path"] = dynamic_path
                print(f" Linked profile item '{item['name']}' to local asset.")
                modified_count += 1
                
        if "children" in item and isinstance(item["children"], list):
            sub_count, _ = scan_and_replace(item["children"], target_name, dynamic_path, collected_names)
            modified_count += sub_count
            
    return modified_count, collected_names

def generate_universal_config():
    assets_folder = "local assets"
    
    # 1. SCAN FOR JSON FILES IN THE CURRENT FOLDER
    json_files = [f for f in os.listdir(".") if f.endswith(".json")]
    
    if len(json_files) == 0:
        print("Error: Could not find any configuration .json file in this folder.")
        print("\nPress any key to exit...")
        msvcrt.getch()
        return
    elif len(json_files) > 1:
        print("FAILSAFE ERROR: Multiple JSON files detected in this folder!")
        print("Please ensure only ONE configuration .json file exists here.")
        print("Detected files:")
        for jf in json_files:
            print(f" - {jf}")
        print("\nPress any key to exit...")
        msvcrt.getch()
        return
        
    config_name = json_files[0]
    print(f"Found configuration file: {config_name}")

    print(f"Reading {config_name}...")
    with open(config_name, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        
    mod_count = 0
    
    if isinstance(config_data, list):
        root_list = config_data
    elif isinstance(config_data, dict):
        root_list = config_data.get("items", [])
        if not root_list:
            for val in config_data.values():
                if isinstance(val, list):
                    root_list = val
                    break
    else:
        root_list = []

    # Track all profiles found and keep a raw list of local assets to check later
    all_profile_names = set()
    local_assets_found = []

    if os.path.exists(assets_folder) and root_list:
        for root, dirs, files in os.walk(assets_folder):
            for file in files:
                custom_asset_name = Path(file).stem.strip().lower() 
                
                absolute_local_path = os.path.abspath(os.path.join(root, file))
                clean_path = urllib.parse.unquote(absolute_local_path).replace("\\", "/")

                # Scan and link matches
                count, collected_names = scan_and_replace(root_list, custom_asset_name, clean_path)
                mod_count += count
                all_profile_names.update(collected_names)
                
                # Keep track of every asset file we looked at
                local_assets_found.append((custom_asset_name, clean_path))

        # ✅ FIXED: Only flag as unmatched if the name is completely missing from all profile names
        final_unmatched = [path for name, path in local_assets_found if name not in all_profile_names]

        # Print the directory of any files that didn't match existing profiles
        if final_unmatched:
            print("\n⚠️ The following local files did not match any existing profiles:")
            for file_path in final_unmatched:
                print(f" - {file_path}")

    with open(config_name, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    
    print(f"\n Success! Universally updated {mod_count} asset path(s) inside {config_name}.")
    print("\nPress any key to close...")
    msvcrt.getch()
    
if __name__ == "__main__":
    generate_universal_config()
