import os
import warnings
from pathlib import Path
import argparse

# Import the new configuration-based system
from emoji_pack_generator import EmojiPackConfig, EmojiPackProcessor

# Legacy functions for backward compatibility
def download_repo_zip(repo_url, branch='main'):
    """Legacy function - now uses new configuration system."""
    warnings.warn("download_repo_zip is deprecated. Use EmojiPackProcessor instead.", 
                  DeprecationWarning, stacklevel=2)
    
    # Create a temporary config for the legacy call
    temp_config = {
        "source": {"repository": repo_url, "branch": branch, "folder": "assets"},
        "input_structure": {},
        "output": {},
        "file_processing": {}
    }
    config = type('Config', (), temp_config)()
    processor = EmojiPackProcessor(config)
    return processor.download_repo_zip(branch)

def extract_folder_from_zip(zip_content, folder_name, extract_to='.'):
    """Legacy function - now uses new configuration system."""
    warnings.warn("extract_folder_from_zip is deprecated. Use EmojiPackProcessor instead.", 
                  DeprecationWarning, stacklevel=2)
    
    # Extract using new system - simplified for legacy compatibility
    import zipfile
    import io
    from tqdm import tqdm
    
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
        members = [m for m in zip_file.namelist() if m.startswith(folder_name)]
        for member in tqdm(members, desc="Extracting"):
            member_path = os.path.relpath(member, folder_name)
            target_path = os.path.join(extract_to, member_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if not member.endswith('/'):
                with zip_file.open(member) as source, open(target_path, 'wb') as target:
                    target.write(source.read())

def process_metadata_and_images(extract_to, style, skin_tone):
    """Legacy function - now uses new configuration system."""
    warnings.warn("process_metadata_and_images is deprecated. Use EmojiPackProcessor instead.", 
                  DeprecationWarning, stacklevel=2)
    
    # Use the FluentUI configuration
    config_path = os.path.join(os.path.dirname(__file__), 'configs', 'fluentui-emoji.json')
    config = EmojiPackConfig(config_path)
    processor = EmojiPackProcessor(config)
    return processor.process_metadata_and_images(extract_to, style, skin_tone)

def save_json(data, file_path):
    """Legacy function - now uses new configuration system."""
    warnings.warn("save_json is deprecated. Use EmojiPackProcessor.save_json instead.", 
                  DeprecationWarning, stacklevel=2)
    
    file_path.parent.mkdir(exist_ok=True, parents=True)
    import json
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and process FluentUI Emoji (Legacy - use emoji_pack_generator.py for new features)')
    parser.add_argument('--repo-url', default='microsoft/fluentui-emoji', help='GitHub repository URL')
    parser.add_argument('--folder-name', default='fluentui-emoji-main/assets', help='Folder name in the repository')
    parser.add_argument('--extract-to', default='./cache/fluentui-emoji/assets/', help='Extraction directory')
    parser.add_argument('--skin-tone', default='Default', choices=["Default", "Dark", "Medium-Dark", "Medium-Light", "Light"], help='Skin tone')
    parser.add_argument('--style', default='3D', choices=['3D', 'Color', 'Flat'], help='Emoji style')
    parser.add_argument('--download', action='store_true', help='Force download of assets')
    parser.add_argument('--config', help='Use JSON configuration file (recommended - uses emoji_pack_generator.py)')
    args = parser.parse_args()

    # If config is specified, use the new system
    if args.config:
        print("Using new configuration-based system...")
        config = EmojiPackConfig(args.config)
        processor = EmojiPackProcessor(config)
        processor.generate_pack(args.style, args.skin_tone, args.extract_to, args.download)
        exit(0)

    # Legacy behavior with deprecation warning
    print("WARNING: Legacy mode is deprecated. Consider using --config with a JSON configuration file.")
    print("See configs/fluentui-emoji.json for an example configuration.")
    
    repo_url = args.repo_url
    folder_name = args.folder_name
    extract_to = args.extract_to
    skin_tone = args.skin_tone
    style = args.style

    if args.download:
        print(f"Downloading repository {repo_url}")
        zip_content = download_repo_zip(repo_url)
        if zip_content:
            print(f"Extracting folder {folder_name} to {extract_to}")
            extract_folder_from_zip(zip_content, folder_name, extract_to)
            print(f"Folder {folder_name} extracted successfully to {extract_to}")
        else:
            print("Failed to download or extract the repository")
    else:
        print("Skipping download, using existing files")

    providers = process_metadata_and_images(extract_to, style, skin_tone)

    jsonObj = {"providers": providers}
    save_json(jsonObj, Path(f"./packs/FluentUi-{style}-{skin_tone}-Emoji/assets/minecraft/font/default.json"))

    pack = {"description": f"FluentUi {style}-{skin_tone} Emoji Resource Pack", "pack_format": 15}
    packJsonObj = {"pack": pack}
    save_json(packJsonObj, Path(f"./packs/FluentUi-{style}-{skin_tone}-Emoji/pack.mcmeta"))