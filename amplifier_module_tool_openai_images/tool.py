"""OpenAI Images tool implementation — wraps the OpenAI Images API.

Uses ``gpt-image-2`` for generation and editing (including inpainting via
masks), and ``gpt-image-1.5`` for background removal (transparent PNG output).
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any

from amplifier_core import ToolResult

logger = logging.getLogger(__name__)


class OpenAIImagesTool:
    """OpenAI Images tool for generation, editing, and background removal."""

    DEFAULT_GEN_MODEL = "gpt-image-2"
    DEFAULT_BG_REMOVAL_MODEL = "gpt-image-1.5"
    DEFAULT_BG_REMOVAL_PROMPT = (
        "Remove the background from this image, preserving the foreground "
        "subject with high fidelity"
    )

    def __init__(self, config: dict[str, Any], coordinator: Any) -> None:
        self.config = config
        self.coordinator = coordinator
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.working_dir = config.get("working_dir")
        self.gen_model = config.get("gen_model", self.DEFAULT_GEN_MODEL)
        self.bg_removal_model = config.get("bg_removal_model", self.DEFAULT_BG_REMOVAL_MODEL)

    @property
    def name(self) -> str:
        return "openai_images"

    @property
    def description(self) -> str:
        return (
            "OpenAI Images tool for image generation, editing, and background "
            "removal. Operations: generate (text-to-image, reference-image "
            "editing, and mask-based inpainting via gpt-image-2); "
            "remove_background (produce a transparent PNG via gpt-image-1.5). "
            "Supports flexible resolutions up to 4K, quality tiers "
            "(low/medium/high), output formats (png/jpeg/webp), and "
            "multi-image reference editing."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["generate", "remove_background"],
                    "description": (
                        "Operation: generate (create or edit images via "
                        "gpt-image-2) or remove_background (transparent PNG "
                        "via gpt-image-1.5)"
                    ),
                },
                "prompt": {
                    "type": "string",
                    "description": "Generation prompt (required for generate)",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output path for generated/edited image (required for generate)",
                },
                "image_path": {
                    "type": "string",
                    "description": "Input image for remove_background (required for that operation).",
                },
                "number_of_images": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                    "default": 1,
                    "description": "Number of images to generate (default: 1, max: 4)",
                },
                "reference_image_path": {
                    "type": "string",
                    "description": (
                        "Optional single reference image for generation (uses "
                        "edit endpoint). Merged with reference_image_paths if "
                        "both are provided."
                    ),
                },
                "reference_image_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional list of reference images for generation "
                        "(uses edit endpoint with multiple images)."
                    ),
                },
                "mask_path": {
                    "type": "string",
                    "description": (
                        "Optional mask image (PNG with alpha channel) for "
                        "inpainting. Transparent areas mark where the model "
                        "should edit. Must be same dimensions as the "
                        "reference image. Only used with reference_image_path."
                    ),
                },
                "size": {
                    "type": "string",
                    "default": "auto",
                    "description": (
                        "Image size: 'auto', '1024x1024', '1536x1024', "
                        "'1024x1536', '2048x2048', '3840x2160', etc. Max edge "
                        "3840px, ratio up to 3:1."
                    ),
                },
                "quality": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "auto"],
                    "default": "auto",
                    "description": (
                        "Image quality. 'low' for fast drafts, 'high' for final assets."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["png", "jpeg", "webp"],
                    "default": "png",
                    "description": (
                        "Output image format (maps to output_format in the OpenAI SDK)."
                    ),
                },
                "output_compression": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": (
                        "Compression level (0-100). Only applies when format is jpeg or webp."
                    ),
                },
            },
            "required": ["operation"],
        }

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path, making it absolute using working_dir if relative."""
        path = Path(path_str).expanduser()
        if not path.is_absolute() and self.working_dir:
            path = Path(self.working_dir) / path
        return path

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute an OpenAI Images operation."""
        from openai import OpenAI  # lazy import to avoid startup cost

        if not self.api_key:
            error_msg = (
                "OPENAI_API_KEY environment variable not set. "
                "Set it with: export OPENAI_API_KEY='your-key'"
            )
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        client = OpenAI(api_key=self.api_key)
        operation = input_data.get("operation")
        prompt = input_data.get("prompt", "")

        try:
            if operation == "generate":
                return await self._generate(client, input_data, prompt)
            if operation == "remove_background":
                return await self._remove_background(client, input_data, prompt)

            error_msg = (
                f"Unknown operation: {operation}. Use 'generate' or 'remove_background'."
            )
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})
        except FileNotFoundError as e:
            await self.coordinator.hooks.emit(
                "tool.openai_images.error", {"operation": operation, "error": str(e)}
            )
            return ToolResult(success=False, output=str(e), error={"message": str(e)})
        except Exception as e:
            await self.coordinator.hooks.emit(
                "tool.openai_images.error", {"operation": operation, "error": str(e)}
            )
            error_msg = f"OpenAI Images request failed: {e}"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

    async def _generate(self, client: Any, input_data: dict, prompt: str) -> ToolResult:
        """Generate (or edit) images using gpt-image-2."""
        if not prompt:
            error_msg = "prompt is required for generate operation"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        output_path_str = input_data.get("output_path")
        if not output_path_str:
            error_msg = "output_path is required for generate operation"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        output_path = self._resolve_path(output_path_str)
        number_of_images = input_data.get("number_of_images", 1)
        if not 1 <= number_of_images <= 4:
            error_msg = "number_of_images must be between 1 and 4"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        size = input_data.get("size", "auto")
        quality = input_data.get("quality", "auto")
        output_format = input_data.get("format", "png")
        output_compression = input_data.get("output_compression")

        # Merge singular + plural reference image params (backward compat)
        ref_path_strs: list[str] = []
        single_ref = input_data.get("reference_image_path")
        if single_ref:
            ref_path_strs.append(single_ref)
        multi_refs = input_data.get("reference_image_paths") or []
        ref_path_strs.extend(multi_refs)

        mask_path_str = input_data.get("mask_path")

        await self.coordinator.hooks.emit(
            "tool.openai_images.generate",
            {
                "output_path": str(output_path),
                "model": self.gen_model,
                "size": size,
                "quality": quality,
                "format": output_format,
                "number_of_images": number_of_images,
                "reference_count": len(ref_path_strs),
                "has_mask": bool(mask_path_str),
            },
        )

        common_kwargs: dict[str, Any] = {
            "model": self.gen_model,
            "prompt": prompt,
            "n": number_of_images,
            "quality": quality,
            "output_format": output_format,
        }
        if size != "auto":
            common_kwargs["size"] = size
        if output_compression is not None and output_format in ("jpeg", "webp"):
            common_kwargs["output_compression"] = output_compression

        if ref_path_strs:
            resolved_refs: list[Path] = []
            for p in ref_path_strs:
                rp = self._resolve_path(p)
                if not rp.exists():
                    raise FileNotFoundError(f"Reference image not found: {rp}")
                resolved_refs.append(rp)

            resolved_mask: Path | None = None
            if mask_path_str:
                resolved_mask = self._resolve_path(mask_path_str)
                if not resolved_mask.exists():
                    raise FileNotFoundError(f"Mask image not found: {resolved_mask}")

            open_files = [open(rp, "rb") for rp in resolved_refs]
            mask_file = open(resolved_mask, "rb") if resolved_mask else None
            try:
                edit_kwargs = dict(common_kwargs)
                edit_kwargs["image"] = open_files if len(open_files) > 1 else open_files[0]
                if mask_file is not None:
                    edit_kwargs["mask"] = mask_file
                result = client.images.edit(**edit_kwargs)
            finally:
                for f in open_files:
                    f.close()
                if mask_file is not None:
                    mask_file.close()
        else:
            result = client.images.generate(**common_kwargs)

        # Save generated images
        generated_paths: list[str] = []
        for i, image_item in enumerate(result.data):
            if number_of_images == 1:
                current_output = output_path
            else:
                stem = output_path.stem
                suffix = output_path.suffix or f".{output_format}"
                current_output = output_path.parent / f"{stem}_{i + 1}{suffix}"

            current_output.parent.mkdir(parents=True, exist_ok=True)

            if image_item.b64_json:
                image_bytes = base64.b64decode(image_item.b64_json)
                with open(current_output, "wb") as f:
                    f.write(image_bytes)
                generated_paths.append(str(current_output))
                logger.info("Generated image saved to: %s", current_output)
            elif image_item.url:
                import urllib.request

                urllib.request.urlretrieve(image_item.url, str(current_output))
                generated_paths.append(str(current_output))
                logger.info("Generated image downloaded to: %s", current_output)

        if not generated_paths:
            error_msg = "No images were generated in the response"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        return ToolResult(
            success=True,
            output={"generated_images": generated_paths, "count": len(generated_paths)},
        )

    async def _remove_background(self, client: Any, input_data: dict, prompt: str) -> ToolResult:
        """Remove the background from an image using gpt-image-1.5.

        gpt-image-1.5 supports background="transparent" which gpt-image-2 does
        not. Output is forced to PNG for alpha channel.
        """
        image_path_str = input_data.get("image_path")
        if not image_path_str:
            error_msg = "image_path is required for remove_background operation"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        output_path_str = input_data.get("output_path")
        if not output_path_str:
            error_msg = "output_path is required for remove_background operation"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        image_path = self._resolve_path(image_path_str)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        output_path = self._resolve_path(output_path_str)
        if output_path.suffix.lower() != ".png":
            output_path = output_path.with_suffix(".png")

        quality = input_data.get("quality", "auto")
        size = input_data.get("size", "auto")
        bg_prompt = prompt or self.DEFAULT_BG_REMOVAL_PROMPT

        await self.coordinator.hooks.emit(
            "tool.openai_images.remove_background",
            {
                "image_path": str(image_path),
                "output_path": str(output_path),
                "model": self.bg_removal_model,
            },
        )

        with open(image_path, "rb") as image_file:
            edit_kwargs: dict[str, Any] = {
                "model": self.bg_removal_model,
                "image": image_file,
                "prompt": bg_prompt,
                "background": "transparent",
                "quality": quality,
            }
            if size != "auto":
                edit_kwargs["size"] = size
            result = client.images.edit(**edit_kwargs)

        if not result.data:
            error_msg = "No image was returned in the response"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        image_item = result.data[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if image_item.b64_json:
            image_bytes = base64.b64decode(image_item.b64_json)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            logger.info("Background-removed image saved to: %s", output_path)
        elif image_item.url:
            import urllib.request
            urllib.request.urlretrieve(image_item.url, str(output_path))
            logger.info("Background-removed image downloaded to: %s", output_path)
        else:
            error_msg = "No image data (b64_json or url) in the response"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        return ToolResult(
            success=True,
            output={"output_path": str(output_path)},
        )
