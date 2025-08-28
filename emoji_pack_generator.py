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
        
        # Validate source configuration
        source = self.config['source']
        required_source_fields = ['repository', 'folder']
        for field in required_source_fields:
            if field not in source:
                raise ValueError(f"Missing required source field: {field}")
        
        # Validate input structure
        input_struct = self.config['input_structure']
        required_input_fields = ['image_folders', 'image_extensions']
        for field in required_input_fields:
            if field not in input_struct:
                raise ValueError(f"Missing required input_structure field: {field}")
        
        # Check metadata configuration
        use_metadata = input_struct.get('use_metadata', True)
        if use_metadata and 'metadata_file' not in input_struct:
            raise ValueError("metadata_file is required when use_metadata is true")
        
        # Validate output configuration
        output = self.config['output']
        required_output_fields = ['output_directory', 'description_template']
        for field in required_output_fields:
            if field not in output:
                raise ValueError(f"Missing required output field: {field}")
        
        # Validate file processing
        file_proc = self.config['file_processing']
        use_metadata = self.config['input_structure'].get('use_metadata', True)
        
        if use_metadata:
            required_file_proc_fields = ['filename_from_metadata', 'character_from_metadata']
            for field in required_file_proc_fields:
                if field not in file_proc:
                    raise ValueError(f"Missing required file_processing field: {field}")
        else:
            if 'filename_from_file' not in file_proc:
                raise ValueError("filename_from_file is required when use_metadata is false")
        
        print(f"Configuration validation passed for {self.config.get('name', 'Unknown Pack')}")
    
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
    
    def download_repo_zip(self, branch: Optional[str] = None, commit: Optional[str] = None) -> Optional[bytes]:
        """Download repository as ZIP file."""
        if branch is None:
            branch = self.source_info.get('branch', 'main')
        
        repo_url = self.source_info['repository']
        
        # Support downloading specific commits
        if commit:
            zip_url = f"https://github.com/{repo_url}/archive/{commit}.zip"
        else:
            zip_url = f"https://github.com/{repo_url}/archive/refs/heads/{branch}.zip"
        
        print(f"Downloading from: {zip_url}")
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
    
    def extract_folder_from_zip(self, zip_content: bytes, extract_to: str = './cache', commit: Optional[str] = None):
        """Extract specified folder from ZIP file."""
        repo_name = self.source_info['repository'].split('/')[-1]
        
        if commit:
            # For commits, GitHub uses the commit hash as folder name
            folder_prefix = f"{repo_name}-{commit[:7]}"  # GitHub uses first 7 chars for short commit hash
        else:
            branch = self.source_info.get('branch', 'main')
            folder_prefix = f"{repo_name}-{branch}"
        
        source_folder = f"{folder_prefix}/{self.source_info['folder']}"
        
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            # Find the actual folder name in the ZIP (GitHub might use full commit hash)
            all_members = zip_file.namelist()
            actual_folder = None
            
            # Look for the folder pattern
            for member in all_members:
                if member.startswith(f"{repo_name}-") and f"/{self.source_info['folder']}/" in member:
                    parts = member.split('/')
                    if len(parts) >= 2:
                        actual_folder = f"{parts[0]}/{self.source_info['folder']}"
                        break
            
            if not actual_folder:
                # Fallback to the expected folder name
                actual_folder = source_folder
            
            print(f"Extracting from folder: {actual_folder}")
            members = [m for m in all_members if m.startswith(actual_folder)]
            
            if not members:
                raise ValueError(f"No files found in folder {actual_folder}. Available folders: {set(m.split('/')[0] for m in all_members[:10])}")
            
            for member in tqdm(members, desc="Extracting"):
                member_path = os.path.relpath(member, actual_folder)
                target_path = os.path.join(extract_to, member_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                if not member.endswith('/'):
                    with zip_file.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
    
    def _substitute_variables(self, template: str, **kwargs) -> str:
        """Substitute variables in template string."""
        return template.format(**kwargs)
    
    def _unicode_hex_to_char(self, hex_string: str, separator: str = "-") -> str:
        """Convert Unicode hex string to character."""
        # Split by separator and convert each part
        hex_parts = hex_string.split(separator)
        chars = []
        for hex_part in hex_parts:
            try:
                # Convert hex to integer, then to character
                code_point = int(hex_part, 16)
                chars.append(chr(code_point))
            except (ValueError, OverflowError) as e:
                print(f"Warning: Could not convert {hex_part} to character: {e}")
                return hex_string  # Return original if conversion fails
        
        return ''.join(chars)
    
    def _extract_unicode_from_template(self, filename: str, pattern_template: str) -> Optional[str]:
        """Extract unicode value from filename using a template pattern.
        
        Args:
            filename: The filename to parse (without extension)
            pattern_template: Template like "emoji_u{unicode}" where {unicode} marks the unicode part
            
        Returns:
            The extracted unicode hex string, or None if pattern doesn't match
        """
        import re
        
        # Escape special regex characters in the template, but keep {unicode} as a capture group
        escaped_template = re.escape(pattern_template)
        
        # Replace the escaped {unicode} placeholder with a capture group for hex characters
        regex_pattern = escaped_template.replace(r'\{unicode\}', r'([0-9a-fA-F_]+)')
        
        # Add start and end anchors to ensure full match
        regex_pattern = f'^{regex_pattern}$'
        
        match = re.match(regex_pattern, filename)
        if match:
            # Return the captured unicode part
            return match.group(1)
        else:
            return None
    
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
        use_metadata = self.input_structure.get('use_metadata', True)
        image_extensions = self.input_structure['image_extensions']
        
        if use_metadata:
            return self._process_with_metadata(extract_to, style, skin_tone)
        else:
            return self._process_without_metadata(extract_to, style, skin_tone)
    
    def _process_with_metadata(self, extract_to: str, style: str, skin_tone: str) -> List[Dict[str, Any]]:
        """Process with metadata.json files."""
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
    
    def _process_without_metadata(self, extract_to: str, style: str, skin_tone: str) -> List[Dict[str, Any]]:
        """Process without metadata files, using filename parsing."""
        providers = []
        image_extensions = self.input_structure['image_extensions']
        filename_config = self.file_processing.get('filename_from_file', {})
        
        if not filename_config.get('enabled', False):
            print("Error: filename_from_file is not enabled")
            return providers
        
        pattern = filename_config.get('pattern', 'unicode_hex')
        separator = filename_config.get('separator', '-')
        
        # Find image folder
        image_folder_path = self._find_image_folder(extract_to, style, skin_tone)
        if not image_folder_path:
            # If no specific folder found, use extract_to directly
            image_folder_path = extract_to
        
        print(f"Processing images from: {image_folder_path}")
        
        # Process all image files in the folder
        for filename in os.listdir(image_folder_path):
            file_path = os.path.join(image_folder_path, filename)
            
            # Check if it's an image file
            if not os.path.isfile(file_path):
                continue
            
            file_ext = filename.lower().split('.')[-1]
            if file_ext not in [ext.lower() for ext in image_extensions]:
                continue
            
            # Extract unicode from filename
            basename = '.'.join(filename.split('.')[:-1])  # Remove extension
            
            if pattern == 'unicode_hex':
                # Convert hex filename to unicode and character
                unicode_val = basename.upper()  # Keep as uppercase hex
                character = self._unicode_hex_to_char(basename, separator)
                
                print(f"Processing: {basename} -> {unicode_val} -> {character}")
                
            elif '{unicode}' in pattern:
                # Handle template-based patterns like "emoji_u{unicode}"
                unicode_val = self._extract_unicode_from_template(basename, pattern)
                if unicode_val is None:
                    continue
                    
                unicode_val = unicode_val.upper()  # Keep as uppercase hex
                character = self._unicode_hex_to_char(unicode_val, separator)
                
                print(f"Processing: {basename} -> {unicode_val} -> {character}")
                
            else:
                print(f"Unknown pattern: {pattern}")
                continue
                
            # Handle pack icon
            if unicode_val.lower() == self.output_config.get('pack_icon_source', '').lower():
                icon_dest = self._substitute_variables(
                    f"{self.output_config['output_directory']}/pack.png",
                    style=style, skin_tone=skin_tone
                )
                Path(icon_dest).parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(file_path, icon_dest)
            
            # Copy image to destination
            destination_image = self._substitute_variables(
                f"{self.output_config['output_directory']}/{self.output_config['textures_path']}/{unicode_val}.png",
                style=style, skin_tone=skin_tone
            )
            print(f"Copying {file_path} to {destination_image}")
            Path(destination_image).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(file_path, destination_image)
            
            # Create font provider entry
            file_template_path = self._substitute_variables(
                self.font_config['file_template'], 
                filename=unicode_val
            )
            
            providers.append({
                "type": self.font_config.get('provider_type', 'bitmap'),
                "file": file_template_path,
                "height": self.font_config.get('height', 7),
                "ascent": self.font_config.get('ascent', 7),
                "chars": [character]
            })
        
        return providers
    
    def save_json(self, data: Any, file_path: Path):
        """Save data as JSON file."""
        file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def generate_pack(self, style: str, skin_tone: str, extract_to: str, force_download: bool = False, commit: Optional[str] = None):
        """Generate emoji pack for specified style and skin tone."""
        # Validate inputs
        available_styles = self.input_structure.get('styles', [])
        available_skin_tones = self.input_structure.get('skin_tones', [])
        
        if available_styles and style not in available_styles:
            print(f"Warning: Style '{style}' not in configured styles: {available_styles}")
        
        if available_skin_tones and skin_tone not in available_skin_tones:
            print(f"Warning: Skin tone '{skin_tone}' not in configured skin tones: {available_skin_tones}")
        
        # Download if requested
        if force_download:
            print(f"Downloading repository {self.source_info['repository']}")
            zip_content = self.download_repo_zip(commit=commit)
            if zip_content:
                print(f"Extracting folder to {extract_to}")
                try:
                    self.extract_folder_from_zip(zip_content, extract_to, commit=commit)
                    print(f"Folder extracted successfully to {extract_to}")
                except Exception as e:
                    print(f"Failed to extract folder: {e}")
                    return
            else:
                print("Failed to download or extract the repository")
                return
        else:
            print("Skipping download, using existing files")
        
        # Check if extract directory exists
        if not os.path.exists(extract_to):
            print(f"Error: Extract directory {extract_to} does not exist. Use --download to download the repository.")
            return
        
        # Process metadata and images
        try:
            providers = self.process_metadata_and_images(extract_to, style, skin_tone)
            
            if not providers:
                print("Warning: No emoji providers were generated. Check your configuration and source data.")
                return
                
        except Exception as e:
            print(f"Error processing metadata and images: {e}")
            return
        
        # Generate font JSON
        font_json = {"providers": providers}
        font_path = self._substitute_variables(
            f"{self.output_config['output_directory']}/{self.output_config['font_path']}",
            style=style, skin_tone=skin_tone
        )
        
        try:
            self.save_json(font_json, Path(font_path))
            print(f"Generated font configuration: {font_path}")
        except Exception as e:
            print(f"Error saving font configuration: {e}")
            return
        
        # Generate pack.mcmeta
        description = self._substitute_variables(
            self.output_config['description_template'],
            style=style, skin_tone=skin_tone
        )
        pack_meta = {
            "pack": {
                "description": description,
                "pack_format": self.output_config.get('pack_format', 15)
            }
        }
        pack_meta_path = self._substitute_variables(
            f"{self.output_config['output_directory']}/{self.output_config['pack_meta_path']}",
            style=style, skin_tone=skin_tone
        )
        
        try:
            self.save_json(pack_meta, Path(pack_meta_path))
            print(f"Generated pack metadata: {pack_meta_path}")
        except Exception as e:
            print(f"Error saving pack metadata: {e}")
            return
        
        print(f"Successfully generated pack for {style}-{skin_tone} with {len(providers)} emojis")


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description='Generate emoji packs from JSON configuration')
    parser.add_argument('--config', required=True, help='Path to JSON configuration file')
    parser.add_argument('--extract-to', default='./cache/assets/', help='Extraction directory')
    parser.add_argument('--style', help='Emoji style (overrides config styles)')
    parser.add_argument('--skin-tone', help='Skin tone (overrides config skin_tones)')
    parser.add_argument('--download', action='store_true', help='Force download of assets')
    parser.add_argument('--commit', help='Specific commit hash to download (overrides branch)')
    args = parser.parse_args()
    
    try:
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
                processor.generate_pack(style, skin_tone, args.extract_to, args.download, args.commit)
                
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == '__main__':
    main()