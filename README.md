# amplifier-module-tool-openai-images

OpenAI Images API tool for [Amplifier](https://github.com/microsoft/amplifier) — generation, editing, and background removal.

> **Two models, two jobs:** This module uses `gpt-image-2` for **image generation and editing** (text-to-image and multi-reference image editing via the [Images API](https://developers.openai.com/api/docs/guides/images-vision#generate-images)) and `gpt-image-1.5` for **background removal** (transparent alpha channel via `images.edit` with `background="transparent"` — a capability `gpt-image-2` does not support). Both defaults are configurable — see [Configuration](#configuration).

## Operations

| Operation | Model | Description |
|-----------|-------|-------------|
| `generate` | `gpt-image-2` | Create images from text prompts, or edit/combine up to N reference images. Supports flexible resolutions up to 4K (3840×2160), quality tiers (low/medium/high), and output formats (png/jpeg/webp). |
| `remove_background` | `gpt-image-1.5` | Remove the background from an image and return a transparent PNG. Uses the `images.edit` endpoint with `background="transparent"`. |

## Install

```bash
pip install git+https://github.com/singh2/amplifier-module-tool-openai-images@main
```

## Usage in Amplifier

Add to a behavior YAML:

```yaml
tools:
  - module: tool-openai-images
    source: git+https://github.com/singh2/amplifier-module-tool-openai-images@main
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
| `gen_model` | `gpt-image-2` | Model for image generation and edit-with-references |
| `bg_removal_model` | `gpt-image-1.5` | Model for background removal (requires `background="transparent"` support) |

## Generate Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | — | **Required.** Text prompt driving generation or edit. |
| `output_path` | — | **Required.** Where to save the generated image. |
| `size` | `auto` | Image dimensions. Any resolution up to 3840px, multiples of 16px, max 3:1 ratio. Popular: `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `3840x2160`. |
| `quality` | `auto` | `low` (fast drafts), `medium`, `high` (final assets), `auto` |
| `format` | `png` | Output format: `png`, `jpeg`, or `webp`. Maps to `output_format` in the OpenAI SDK. |
| `output_compression` | — | Integer 0–100. Only applies when `format` is `jpeg` or `webp`. |
| `number_of_images` | `1` | Generate 1–4 images per call |
| `reference_image_path` | — | Single reference image for style-guided generation (uses edit endpoint). Merged with `reference_image_paths` when both are provided. |
| `reference_image_paths` | — | **List** of reference images (uses edit endpoint with multiple images). |

When any reference image is supplied the tool routes through `client.images.edit(...)` with the image(s) attached; otherwise it uses `client.images.generate(...)`.

## Remove Background Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image_path` | — | **Required.** Input image to remove background from. |
| `output_path` | — | **Required.** Where to save the transparent PNG. The suffix is forced to `.png` (alpha channel requires PNG). |
| `quality` | `auto` | `low`, `medium`, `high`, or `auto`. |
| `size` | `auto` | Output size — same options as `generate`. |
| `prompt` | `"Remove the background from this image, preserving the foreground subject with high fidelity"` | Optional override for the bg-removal prompt. |

## Requirements

- Python >= 3.11
- `openai` >= 1.0.0
- `OPENAI_API_KEY` environment variable
- [Organization verification](https://platform.openai.com/settings/organization/general) may be required for GPT Image model access

## License

MIT
