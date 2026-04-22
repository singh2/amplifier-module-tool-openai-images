# amplifier-module-tool-openai-images

OpenAI [Images API](https://developers.openai.com/api/docs/guides/image-generation) tool for [Amplifier](https://github.com/microsoft/amplifier) — image generation, editing, and background removal.

> **Two models (April 2026):** `gpt-image-2` handles generation and editing. `gpt-image-1.5` handles background removal — `gpt-image-2` [does not support transparent backgrounds](https://developers.openai.com/api/docs/guides/image-generation#customize-image-output). Both defaults are configurable — see [Configuration](#configuration).

## What it does

| Operation | Model | Modes |
|-----------|-------|-------|
| `generate` | `gpt-image-2` | **Text to image** — `prompt` only. **Reference editing** — `prompt` + `reference_image_path(s)`. **Inpainting** — `prompt` + `reference_image_path` + `mask_path`. |
| `remove_background` | `gpt-image-1.5` | Remove the background from an image, producing a transparent PNG. |

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
| `gen_model` | `gpt-image-2` | Model for generate operation |
| `bg_removal_model` | `gpt-image-1.5` | Model for remove_background operation |

## Generate Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | — | **Required.** Text description of what to generate or how to edit. |
| `output_path` | — | **Required.** Where to save the result. |
| `size` | `auto` | Image dimensions. Any resolution up to 3840px, multiples of 16px, max 3:1 ratio. Popular: `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `3840x2160`. |
| `quality` | `auto` | `low` (fast drafts), `medium`, `high` (final assets), `auto`. |
| `format` | `png` | Output format: `png`, `jpeg`, `webp`. Use `jpeg` for faster iteration. |
| `output_compression` | — | Compression level 0–100%. Only applies to `jpeg` and `webp`. |
| `number_of_images` | `1` | Generate 1–4 images per call. |
| `reference_image_path` | — | Single reference image for editing (uses the [edits endpoint](https://developers.openai.com/api/docs/guides/image-generation#edit-images)). |
| `reference_image_paths` | — | List of reference images for compositing multiple sources into one scene. |
| `mask_path` | — | Mask image (PNG with alpha channel) for [inpainting](https://developers.openai.com/api/docs/guides/image-generation#edit-an-image-using-a-mask). Transparent areas mark where to edit. Must match the reference image dimensions. |

## Remove Background Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image_path` | — | **Required.** Input image to remove background from. |
| `output_path` | — | **Required.** Output path (forced to `.png` for alpha channel). |
| `quality` | `auto` | `low`, `medium`, `high`, `auto`. |
| `size` | `auto` | Output dimensions. |
| `prompt` | built-in | Override the default background removal prompt. |

## Supported input formats

Reference, mask, and background-removal images: **PNG**, **JPEG**, **WEBP** — under 50 MB each ([OpenAI requirements](https://developers.openai.com/api/docs/guides/images-vision#image-input-requirements)).

## Requirements

- Python >= 3.11
- `openai` >= 1.0.0
- `OPENAI_API_KEY` environment variable
- [Organization verification](https://platform.openai.com/settings/organization/general) may be required for GPT Image model access

## License

MIT
