# Emoji Pack Generator

A flexible, configuration-driven system for generating emoji resource packs from various sources.

## Features

- **JSON Configuration**: Define emoji pack sources, structure, and output formats via JSON
- **Multiple Source Support**: Currently supports GitHub repositories
- **Flexible Input Structure**: Support for wildcard patterns in folder structures
- **Multiple Output Formats**: Currently supports Minecraft resource packs
- **Skin Tone & Style Support**: Generate packs for different styles and skin tones
- **Backward Compatibility**: Legacy FluentUI script still works

## Quick Start

### Using the New Configuration System

1. **Generate a pack using an existing configuration:**
   ```bash
   python emoji_pack_generator.py --config configs/fluentui-3d-only.json --download
   ```

2. **Generate for specific style/skin tone:**
   ```bash
   python emoji_pack_generator.py --config configs/fluentui-3d-only.json --style 3D --skin-tone Dark --download
   ```

3. **Use existing downloaded files:**
   ```bash
   python emoji_pack_generator.py --config configs/fluentui-3d-only.json --extract-to ./cache/assets/
   ```

### Using the Legacy System

The original fluentui-emoji.py still works for backward compatibility:

```bash
# Legacy mode (deprecated)
python fluentui-emoji.py --download --style 3D --skin-tone Default

# Legacy mode with new configuration
python fluentui-emoji.py --config configs/fluentui-3d-only.json --style 3D --skin-tone Default
```

## Configuration

### Example Configuration Files

- `configs/fluentui-3d-only.json` - FluentUI emojis, 3D style only
- `configs/fluentui-emoji.json` - FluentUI emojis, all styles (includes SVG)
- `configs/twemoji-example.json` - Example Twemoji configuration

### Configuration Schema

See [CONFIG_SCHEMA.md](CONFIG_SCHEMA.md) for detailed documentation of the JSON schema.

### Basic Configuration Structure

```json
{
  "name": "Pack Name",
  "source": {
    "type": "github",
    "repository": "owner/repo-name",
    "branch": "main",
    "folder": "assets"
  },
  "input_structure": {
    "metadata_file": "metadata.json",
    "image_folders": ["{style}", "{skin_tone}/{style}"],
    "image_extensions": ["png"],
    "styles": ["3D", "Color", "Flat"],
    "skin_tones": ["Default", "Dark", "Light"]
  },
  "output": {
    "type": "minecraft_resource_pack",
    "pack_format": 15,
    "description_template": "{name} {style}-{skin_tone} Pack",
    "output_directory": "./packs/{name}-{style}-{skin_tone}"
  },
  "file_processing": {
    "filename_from_metadata": "unicode",
    "character_from_metadata": "glyph"
  },
  "font_config": {
    "provider_type": "bitmap",
    "height": 7,
    "ascent": 7
  }
}
```

## Command Line Options

### emoji_pack_generator.py

```
--config CONFIG        Path to JSON configuration file (required)
--extract-to DIR       Extraction directory (default: ./cache/assets/)
--style STYLE          Emoji style (overrides config)
--skin-tone TONE       Skin tone (overrides config)
--download             Force download of assets
--commit HASH          Specific commit hash to download
```

### fluentui-emoji.py (Legacy)

```
--repo-url URL         GitHub repository URL
--folder-name NAME     Folder name in repository
--extract-to DIR       Extraction directory
--skin-tone TONE       Skin tone
--style STYLE          Emoji style
--download             Force download of assets
--config CONFIG        Use JSON configuration (recommended)
```

## Creating Custom Configurations

1. **Create a new JSON configuration file** based on the schema
2. **Define your source repository** and folder structure
3. **Configure input patterns** with wildcard support
4. **Set up output format** and naming conventions
5. **Test with a small subset** before full generation

### Wildcard Support

The system supports these wildcards in folder patterns:
- `{style}` - Matches any style from the configuration
- `{skin_tone}` - Matches any skin tone from the configuration

Example: `["{style}", "{skin_tone}/{style}"]` will match both:
- `3D/` and `Default/3D/`
- `Color/` and `Dark/Color/`

## File Structure

```
emoji_pack/
├── emoji_pack_generator.py    # New configuration-based generator
├── fluentui-emoji.py          # Legacy script with backward compatibility
├── configs/                   # Configuration files
│   ├── fluentui-3d-only.json  # FluentUI 3D only (recommended)
│   ├── fluentui-emoji.json    # FluentUI all styles
│   └── twemoji-example.json   # Example Twemoji config
├── CONFIG_SCHEMA.md           # Configuration schema documentation
├── cache/                     # Downloaded assets cache
└── packs/                     # Generated resource packs
```

## Supported Input Formats

- **PNG images** - Ready for Minecraft resource packs
- **SVG images** - Requires conversion to PNG (not implemented yet)
- **Metadata JSON** - For emoji information and mapping

## Supported Output Formats

- **Minecraft Resource Pack** - Complete pack with textures and font JSON

## Known Limitations

1. **SVG Support**: SVG files are detected but not converted to PNG automatically
2. **Single Source Type**: Only GitHub repositories supported currently
3. **Minecraft Format Only**: Only Minecraft resource pack output implemented

## Contributing

To add support for new source types or output formats:

1. Extend the `EmojiPackProcessor` class
2. Add new configuration options to the schema
3. Update validation in `EmojiPackConfig`
4. Test with example configurations

## Examples

### Generate FluentUI 3D Pack
```bash
python emoji_pack_generator.py --config configs/fluentui-3d-only.json --download
```

### Generate for Specific Skin Tone
```bash
python emoji_pack_generator.py --config configs/fluentui-3d-only.json --skin-tone Dark
```

### Use Specific Commit
```bash
python emoji_pack_generator.py --config configs/fluentui-3d-only.json --commit abc123 --download
```

The generated packs will be in the `packs/` directory and can be installed as Minecraft resource packs.