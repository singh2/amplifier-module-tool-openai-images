# amplifier-module-tool-openai-images

OpenAI [ChatGPT Images 2.0](https://openai.com/index/introducing-chatgpt-images-2-0/) tool for [Amplifier](https://github.com/microsoft/amplifier) — image generation, analysis, and comparison via `gpt-image-2`.

> **Two models, two jobs (April 2026):** This module uses `gpt-image-2` for **image generation** (the [Images API](https://developers.openai.com/api/docs/guides/images-vision#generate-images)) and `gpt-5.4` for **image understanding** — analyze and compare operations go through the [Chat Completions vision API](https://developers.openai.com/api/docs/guides/images-vision#analyze-images). Both defaults are configurable — see [Configuration](#configuration).

## Operations

| Operation | Model | Description |
|-----------|-------|-------------|
| `generate` | `gpt-image-2` | Create images from text prompts. Supports flexible resolutions up to 4K (3840×2160), quality tiers (low/medium/high), and reference image editing. |
| `analyze` | `gpt-5.4` (vision) | Analyze a single image — UI structure, component identification, typography, color palette. |
| `compare` | `gpt-5.4` (vision) | Side-by-side visual diff of two images — fidelity checks, before/after change detection. |

## Install

```bash
pip install git+https://github.com/gurksing_microsoft/amplifier-module-tool-openai-images@main
```

## Usage in Amplifier

Add to a behavior YAML:

```yaml
tools:
  - module: tool-openai-images
    source: git+https://github.com/gurksing_microsoft/amplifier-module-tool-openai-images@main
```

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-key"
```

Optional mount config:

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | `$OPENAI_API_KEY` | OpenAI API key (env var fallback) |
| `gen_model` | `gpt-image-2` | Model for image generation |
| `vision_model` | `gpt-5.4` | Model for analyze/compare operations |

## Generate Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `size` | `auto` | Image dimensions. Any resolution up to 3840px, multiples of 16px, max 3:1 ratio. Popular: `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `3840x2160`. |
| `quality` | `auto` | `low` (fast drafts), `medium`, `high` (final assets), `auto` |
| `number_of_images` | `1` | Generate 1–4 images per call |
| `reference_image_path` | — | Reference image for style-guided generation (uses edit endpoint) |

## Requirements

- Python >= 3.11
- `openai` >= 1.0.0
- `OPENAI_API_KEY` environment variable
- [Organization verification](https://platform.openai.com/settings/organization/general) may be required for GPT Image model access

## License

MIT
