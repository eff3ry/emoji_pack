# Emoji Pack Configuration Schema

This document describes the JSON configuration schema for the emoji pack generator.

## Configuration Structure

```json
{
  "name": "Pack Name",
  "version": "1.0.0",
  "source": {
    "type": "github",
    "repository": "owner/repository-name",
    "branch": "main",
    "folder": "path/to/assets/folder"
  },
  "input_structure": {
    "metadata_file": "metadata.json",
    "use_metadata": true,
    "image_folders": [
      "{style}",
      "{skin_tone}/{style}"
    ],
    "image_extensions": ["png"],
    "styles": ["3D", "Color", "Flat"],
    "skin_tones": ["Default", "Dark", "Medium-Dark", "Medium-Light", "Light"]
  },
  "output": {
    "type": "minecraft_resource_pack",
    "pack_format": 15,
    "description_template": "Pack Description with {style} and {skin_tone}",
    "output_directory": "./packs/{name}-{style}-{skin_tone}",
    "textures_path": "assets/minecraft/textures/font",
    "font_path": "assets/minecraft/font/default.json",
    "pack_meta_path": "pack.mcmeta",
    "pack_icon_source": "1f603"
  },
  "file_processing": {
    "filename_from_metadata": "unicode",
    "character_from_metadata": "glyph",
    "filename_from_file": {
      "enabled": true,
      "pattern": "unicode_hex",
      "separator": "-"
    },
    "unicode_processing": {
      "skip_if_contains_space": true,
      "handle_variation_selector": {
        "enabled": true,
        "pattern": " fe0f",
        "action": "remove_and_convert"
      }
    }
  },
  "font_config": {
    "provider_type": "bitmap",
    "height": 7,
    "ascent": 7,
    "file_template": "minecraft:font/{filename}.png"
  }
}
```

## Field Descriptions

### Root Level
- `name`: Human-readable name of the emoji pack
- `version`: Version of this configuration
- `source`: Configuration for where to download emoji assets from
- `input_structure`: Describes the expected structure of the input data
- `output`: Configuration for the generated output format
- `file_processing`: Rules for processing individual files
- `font_config`: Font-specific configuration for Minecraft resource packs

### Source Configuration
- `type`: Type of source ("github" currently supported)
- `repository`: GitHub repository in "owner/repo" format
- `branch`: Git branch to download from
- `folder`: Folder within the repository to extract

### Input Structure
- `metadata_file`: Name of the metadata file in each emoji folder (optional if use_metadata is false)
- `use_metadata`: Whether to use metadata.json files or parse from filenames
- `image_folders`: Array of folder patterns to search for images (supports {style}, {skin_tone} variables)
- `image_extensions`: Supported image file extensions
- `styles`: Available styles for this emoji set
- `skin_tones`: Available skin tones for this emoji set

### Output Configuration
- `type`: Output format type
- `pack_format`: Minecraft pack format version
- `description_template`: Template for pack description (supports variables)
- `output_directory`: Where to generate the pack (supports variables)
- `textures_path`: Path within pack for texture files
- `font_path`: Path for font configuration JSON
- `pack_meta_path`: Path for pack metadata file
- `pack_icon_source`: Unicode value to use as pack icon

### File Processing
- `filename_from_metadata`: Metadata field to use for filename (when use_metadata is true)
- `character_from_metadata`: Metadata field to use for character mapping (when use_metadata is true)
- `filename_from_file`: Configuration for parsing filenames directly (when use_metadata is false)
  - `enabled`: Whether to parse filenames
  - `pattern`: Pattern template for filename parsing:
    - `"unicode_hex"`: Direct hex-encoded unicode (e.g., "1f600.png" for 😀)
    - `"emoji_u{unicode}"`: Noto Emoji format with prefix (e.g., "emoji_u1f600.png" for 😀)
    - `"{unicode}_custom"`: Any custom template using {unicode} placeholder
  - `separator`: Character that separates unicode sequences (e.g., "-" for multi-part emojis)
- `unicode_processing`: Rules for processing unicode values

### Font Configuration
- `provider_type`: Minecraft font provider type
- `height`: Font height in pixels
- `ascent`: Font ascent in pixels
- `file_template`: Template for texture file references

## Variable Substitution

The following variables can be used in templates:
- `{style}`: Current style being processed
- `{skin_tone}`: Current skin tone being processed
- `{filename}`: Processed filename from metadata
- `{name}`: Pack name from root configuration

## Wildcard Support

The system supports wildcards in the `image_folders` configuration:
- `{style}`: Matches any style from the styles array
- `{skin_tone}`: Matches any skin tone from the skin_tones array

This allows flexible folder structure matching without hardcoding paths.