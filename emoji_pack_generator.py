import os
import requests
import zipfile
import io
import json
import shutil
from tqdm import tqdm
from pathlib import Path
import argparse
import fnmatch
from typing import Dict, List, Optional, Any


class EmojiPackConfig:
    """Configuration loader and validator for emoji pack generation."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _validate_config(self):
        """Validate that required configuration fields are present."""
        required_fields = ['source', 'input_structure', 'output', 'file_processing']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required configuration field: {field}")
    
    def get_source_info(self) -> Dict[str, str]:
        """Get source repository information."""
        return self.config['source']
    
    def get_input_structure(self) -> Dict[str, Any]:
        """Get input structure configuration."""
        return self.config['input_structure']
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.config['output']
    
    def get_file_processing_config(self) -> Dict[str, Any]:
        """Get file processing configuration."""
        return self.config['file_processing']
    
    def get_font_config(self) -> Dict[str, Any]:
        """Get font configuration."""
        return self.config.get('font_config', {})


class EmojiPackProcessor:
    """Main processor for generating emoji packs from configuration."""
    
    def __init__(self, config: EmojiPackConfig):
        self.config = config
        self.source_info = config.get_source_info()
        self.input_structure = config.get_input_structure()
        self.output_config = config.get_output_config()
        self.file_processing = config.get_file_processing_config()
        self.font_config = config.get_font_config()
    
    def download_repo_zip(self, branch: Optional[str] = None) -> Optional[bytes]:
        """Download repository as ZIP file."""
        if branch is None:
            branch = self.source_info.get('branch', 'main')
        
        repo_url = self.source_info['repository']
        zip_url = f"https://github.com/{repo_url}/archive/refs/heads/{branch}.zip"
        
        response = requests.get(zip_url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
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
    
    def extract_folder_from_zip(self, zip_content: bytes, extract_to: str = './cache'):
        """Extract specified folder from ZIP file."""
        repo_name = self.source_info['repository'].split('/')[-1]
        branch = self.source_info.get('branch', 'main')
        folder_name = f"{repo_name}-{branch}/{self.source_info['folder']}"
        
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            members = [m for m in zip_file.namelist() if m.startswith(folder_name)]
            for member in tqdm(members, desc="Extracting"):
                member_path = os.path.relpath(member, folder_name)
                target_path = os.path.join(extract_to, member_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                if not member.endswith('/'):
                    with zip_file.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
    
    def _substitute_variables(self, template: str, **kwargs) -> str:
        """Substitute variables in template string."""
        return template.format(**kwargs)
    
    def _find_image_folder(self, subfolder_path: str, style: str, skin_tone: str) -> Optional[str]:
        """Find image folder based on configured patterns."""
        for pattern in self.input_structure['image_folders']:
            folder_path = os.path.join(
                subfolder_path, 
                self._substitute_variables(pattern, style=style, skin_tone=skin_tone)
            ).replace("\\", "/")
            
            if os.path.exists(folder_path):
                return folder_path
        return None
    
    def _process_unicode_value(self, unicode_val: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Process unicode value according to configuration rules."""
        unicode_config = self.file_processing.get('unicode_processing', {})
        
        # Check if we should skip values containing spaces
        if unicode_config.get('skip_if_contains_space', False) and " " in unicode_val:
            # Handle variation selector case
            if (unicode_config.get('handle_variation_selector', {}).get('enabled', False) and
                unicode_val.count(" ") == 1):
                
                pattern = unicode_config['handle_variation_selector']['pattern']
                action = unicode_config['handle_variation_selector']['action']
                
                if pattern in unicode_val and action == "remove_and_convert":
                    print("Special case Variation Selector 16 Found")
                    unicode_val = unicode_val.replace(pattern, "", 1)
                    metadata["glyph"] = chr(int(unicode_val, 16))
                    return unicode_val
            else:
                print(f"Skipping {unicode_val} because it contains a space")
                return None
        
        return unicode_val
    
    def process_metadata_and_images(self, extract_to: str, style: str, skin_tone: str) -> List[Dict[str, Any]]:
        """Process metadata and images according to configuration."""
        providers = []
        metadata_filename = self.input_structure['metadata_file']
        image_extensions = self.input_structure['image_extensions']
        
        for dir_name in os.listdir(extract_to):
            subfolder_path = os.path.join(extract_to, dir_name).replace("\\", "/")
            if os.path.isdir(subfolder_path):
                metadata_file_path = os.path.join(subfolder_path, metadata_filename).replace("\\", "/")
                
                if not os.path.exists(metadata_file_path):
                    continue
                
                print(f"Found metadata file: {metadata_file_path}")
                image_folder_path = self._find_image_folder(subfolder_path, style, skin_tone)
                
                if not image_folder_path:
                    continue
                
                print(f"Found {style} folder in {image_folder_path}")
                
                # Find image files
                image_files = []
                for ext in image_extensions:
                    image_files.extend([f for f in os.listdir(image_folder_path) 
                                      if f.lower().endswith(f'.{ext.lower()}')])
                
                if not image_files:
                    continue
                
                image_path = os.path.join(image_folder_path, image_files[0]).replace("\\", "/")
                print(f"Found image file: {image_path}")
                
                # Load and process metadata
                with open(metadata_file_path, 'r', encoding='utf-8') as metadata_file:
                    metadata = json.load(metadata_file)
                    print(f"{metadata['cldr']}: metadata loaded")
                
                # Get filename and character from metadata
                filename_field = self.file_processing['filename_from_metadata']
                character_field = self.file_processing['character_from_metadata']
                
                unicode_val = metadata[filename_field]
                processed_unicode = self._process_unicode_value(unicode_val, metadata)
                
                if processed_unicode is None:
                    continue
                
                # Handle pack icon
                if processed_unicode == self.output_config.get('pack_icon_source'):
                    icon_dest = self._substitute_variables(
                        f"{self.output_config['output_directory']}/pack.png",
                        style=style, skin_tone=skin_tone
                    )
                    Path(icon_dest).parent.mkdir(exist_ok=True, parents=True)
                    shutil.copy2(image_path, icon_dest)
                
                print(f"{processed_unicode} {metadata[character_field]}")
                
                # Copy image to destination
                destination_image = self._substitute_variables(
                    f"{self.output_config['output_directory']}/{self.output_config['textures_path']}/{processed_unicode}.png",
                    style=style, skin_tone=skin_tone
                )
                print(f"Copying {image_path} to {destination_image}")
                Path(destination_image).parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(image_path, destination_image)
                
                # Create font provider entry
                file_path = self._substitute_variables(
                    self.font_config['file_template'], 
                    filename=processed_unicode
                )
                
                providers.append({
                    "type": self.font_config.get('provider_type', 'bitmap'),
                    "file": file_path,
                    "height": self.font_config.get('height', 7),
                    "ascent": self.font_config.get('ascent', 7),
                    "chars": [metadata[character_field]]
                })
        
        return providers
    
    def save_json(self, data: Any, file_path: Path):
        """Save data as JSON file."""
        file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def generate_pack(self, style: str, skin_tone: str, extract_to: str, force_download: bool = False):
        """Generate emoji pack for specified style and skin tone."""
        # Download if requested
        if force_download:
            print(f"Downloading repository {self.source_info['repository']}")
            zip_content = self.download_repo_zip()
            if zip_content:
                print(f"Extracting folder to {extract_to}")
                self.extract_folder_from_zip(zip_content, extract_to)
                print(f"Folder extracted successfully to {extract_to}")
            else:
                print("Failed to download or extract the repository")
                return
        else:
            print("Skipping download, using existing files")
        
        # Process metadata and images
        providers = self.process_metadata_and_images(extract_to, style, skin_tone)
        
        # Generate font JSON
        font_json = {"providers": providers}
        font_path = self._substitute_variables(
            f"{self.output_config['output_directory']}/{self.output_config['font_path']}",
            style=style, skin_tone=skin_tone
        )
        self.save_json(font_json, Path(font_path))
        
        # Generate pack.mcmeta
        description = self._substitute_variables(
            self.output_config['description_template'],
            style=style, skin_tone=skin_tone
        )
        pack_meta = {
            "pack": {
                "description": description,
                "pack_format": self.output_config['pack_format']
            }
        }
        pack_meta_path = self._substitute_variables(
            f"{self.output_config['output_directory']}/{self.output_config['pack_meta_path']}",
            style=style, skin_tone=skin_tone
        )
        self.save_json(pack_meta, Path(pack_meta_path))
        
        print(f"Generated pack for {style}-{skin_tone}")


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description='Generate emoji packs from JSON configuration')
    parser.add_argument('--config', required=True, help='Path to JSON configuration file')
    parser.add_argument('--extract-to', default='./cache/assets/', help='Extraction directory')
    parser.add_argument('--style', help='Emoji style (overrides config styles)')
    parser.add_argument('--skin-tone', help='Skin tone (overrides config skin_tones)')
    parser.add_argument('--download', action='store_true', help='Force download of assets')
    args = parser.parse_args()
    
    # Load configuration
    config = EmojiPackConfig(args.config)
    processor = EmojiPackProcessor(config)
    
    # Determine styles and skin tones to process
    input_structure = config.get_input_structure()
    styles = [args.style] if args.style else input_structure.get('styles', ['Default'])
    skin_tones = [args.skin_tone] if args.skin_tone else input_structure.get('skin_tones', ['Default'])
    
    # Generate packs for all combinations
    for style in styles:
        for skin_tone in skin_tones:
            processor.generate_pack(style, skin_tone, args.extract_to, args.download)


if __name__ == '__main__':
    main()