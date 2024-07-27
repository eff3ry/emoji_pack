import os
import requests
import zipfile
import io
import json
import shutil
from tqdm import tqdm
from pathlib import Path

def download_repo_zip(repo_url, branch='main'):
    zip_url = f"https://github.com/{repo_url}/archive/refs/heads/{branch}.zip"
    response = requests.get(zip_url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        t = tqdm(total=total_size, unit='iB', unit_scale=True)
        zip_content = io.BytesIO()
        for data in response.iter_content(block_size):
            t.update(len(data))
            zip_content.write(data)
        t.close()
        actual_size = zip_content.tell()
        if total_size != 0 and actual_size != total_size:
            print(f"ERROR, something went wrong: expected {total_size} bytes, got {actual_size} bytes")
        return zip_content.getvalue()
    else:
        print(f"Failed to download repository zip from: {zip_url}\nResponse code: {response.status_code}")
        return None

def extract_folder_from_zip(zip_content, folder_name, extract_to='.'):
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
    providers = []
    for dir_name in os.listdir(extract_to):
        subfolder_path = os.path.join(extract_to, dir_name).replace("\\", "/")
        if os.path.isdir(subfolder_path):
            metadata_file_path = os.path.join(subfolder_path, 'metadata.json').replace("\\", "/")
            image_folder_path = None

            if os.path.exists(metadata_file_path):
                print(f"Found metadata file: {metadata_file_path}")

            if os.path.exists(os.path.join(subfolder_path, style).replace("\\", "/")):
                image_folder_path = os.path.join(subfolder_path, style).replace("\\", "/")
                print(f"Found {style} folder in {subfolder_path}")
            elif os.path.exists(os.path.join(subfolder_path, skin_tone, style).replace("\\", "/")):
                image_folder_path = os.path.join(subfolder_path, skin_tone, style).replace("\\", "/")
                print(f"Found {style} folder in {subfolder_path}/{skin_tone}")

            if image_folder_path:
                png_files = [f for f in os.listdir(image_folder_path) if f.lower().endswith('.png')]
                if png_files:
                    png_path = os.path.join(image_folder_path, png_files[0]).replace("\\", "/")
                    print(f"Found PNG file: {png_path}")

                    if png_path and metadata_file_path:
                        with open(metadata_file_path, 'r', encoding='utf-8') as metadata_file:
                            metadata = json.load(metadata_file)
                            #print(f"Metadata content: {json.dumps(metadata, indent=4)}")
                            print(f"{metadata['cldr']}: metadata loaded")

                        if metadata and " " not in metadata["unicode"]:
                            print(metadata["unicode"] + metadata["glyph"])

                            destination_image = f'./packs/FluentUi-{style}-{skin_tone}-Emoji/assets/minecraft/textures/font/{metadata["unicode"]}.png'
                            print(f"Copying {png_path} to {destination_image}")
                            Path(destination_image).parent.mkdir(exist_ok=True, parents=True)
                            shutil.copy2(png_path, destination_image)

                            provider = {
                                "type": "bitmap",
                                "file": f"minecraft:font/{metadata['unicode']}.png",
                                "height": 7,
                                "ascent": 7,
                                "chars": [metadata["glyph"]]
                            }
                            providers.append(provider)
                        else:
                            print(f"Skipping {metadata['unicode']} because it contains a space")
    return providers

def save_json(data, file_path):
    file_path.parent.mkdir(exist_ok=True, parents=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    repo_url = 'microsoft/fluentui-emoji'
    folder_name = 'fluentui-emoji-main/assets'
    extract_to = './cache/fluentui-emoji/assets/'

    skin_tone = "Default"
    valid_skin_tones = ["Default", "Dark", "Medium-Dark", "Medium-Light", "Light"]
    if skin_tone not in valid_skin_tones:
        print(f"Invalid skin tone: {skin_tone}. Please choose from: {', '.join(valid_skin_tones)}")
        exit(1)
    style = "3D"
    #style options: #ToDo add svg handling for Color and Flat options
    #3D, Color, Flat

    downloadQ = input(f"Fetch assets from '{'/'.join([repo_url, folder_name])}'? y/n: ").strip().lower()

    if downloadQ == 'y':
        print(f"Downloading repository {repo_url}")
        zip_content = download_repo_zip(repo_url)
        if zip_content:
            print(f"Extracting folder {folder_name} to {extract_to}")
            extract_folder_from_zip(zip_content, folder_name, extract_to)
            print(f"Folder {folder_name} extracted successfully to {extract_to}")
        else:
            print("Failed to download or extract the repository")

    providers = process_metadata_and_images(extract_to, style, skin_tone)

    jsonObj = {"providers": providers}
    save_json(jsonObj, Path(f"./packs/FluentUi-{style}-{skin_tone}-Emoji/assets/minecraft/font/default.json"))

    pack = {"description": f"FluentUi {style}-{skin_tone} Emoji Resource Pack", "pack_format": 15}
    packJsonObj = {"pack": pack}
    save_json(packJsonObj, Path(f"./packs/FluentUi-{style}-{skin_tone}-Emoji/pack.mcmeta"))