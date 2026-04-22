"""ChatGPT Images tool implementation — wraps OpenAI Image and Vision APIs.

Uses gpt-image-2 for generation and GPT-5.4 for vision (analyze/compare).
"""

import base64
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

from amplifier_core import ToolResult

logger = logging.getLogger(__name__)


class ChatGPTImagesTool:
    """OpenAI ChatGPT Images tool for image analysis, comparison, and generation."""

    DEFAULT_GEN_MODEL = "gpt-image-2"
    DEFAULT_VISION_MODEL = "gpt-5.4"

    def __init__(self, config: dict[str, Any], coordinator: Any) -> None:
        self.config = config
        self.coordinator = coordinator
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.working_dir = config.get("working_dir")
        self.gen_model = config.get("gen_model", self.DEFAULT_GEN_MODEL)
        self.vision_model = config.get("vision_model", self.DEFAULT_VISION_MODEL)

    @property
    def name(self) -> str:
        return "openai_images"

    @property
    def description(self) -> str:
        return (
            "OpenAI ChatGPT Images tool for visual analysis, comparison, and image generation. "
            "Operations: analyze (single image via GPT vision), compare (two images), "
            "generate (create images via gpt-image-2). Supports flexible resolutions up to 4K, "
            "quality tiers (low/medium/high), and reference image editing."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["analyze", "compare", "generate"],
                    "description": (
                        "Operation: analyze (single image), compare (two images), "
                        "or generate (create image)"
                    ),
                },
                "prompt": {
                    "type": "string",
                    "description": "Analysis, comparison, or generation prompt/question",
                },
                "image_path": {
                    "type": "string",
                    "description": "Image path (required for analyze operation)",
                },
                "image1_path": {
                    "type": "string",
                    "description": "First image path (required for compare)",
                },
                "image2_path": {
                    "type": "string",
                    "description": "Second image path (required for compare)",
                },
                "image1_label": {
                    "type": "string",
                    "default": "IMAGE 1",
                    "description": "Label for first image (default: 'IMAGE 1')",
                },
                "image2_label": {
                    "type": "string",
                    "default": "IMAGE 2",
                    "description": "Label for second image (default: 'IMAGE 2')",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output path for generated image (required for generate)",
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
                    "description": ("Optional reference image for generation (uses edit endpoint)"),
                },
                "size": {
                    "type": "string",
                    "default": "auto",
                    "description": (
                        "Image size: 'auto', '1024x1024', '1536x1024', '1024x1536', "
                        "'2048x2048', '3840x2160', etc. Max edge 3840px, ratio up to 3:1."
                    ),
                },
                "quality": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "auto"],
                    "default": "auto",
                    "description": "Image quality. 'low' for fast drafts, 'high' for final assets.",
                },
            },
            "required": ["operation", "prompt"],
        }

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path, making it absolute using working_dir if relative."""
        path = Path(path_str).expanduser()
        if not path.is_absolute() and self.working_dir:
            path = Path(self.working_dir) / path
        return path

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file extension."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "image/png"

    def _encode_image_base64(self, file_path: Path) -> str:
        """Read and base64-encode an image file."""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute a GPT Image operation."""
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
            if operation == "analyze":
                return await self._analyze(client, input_data, prompt)
            elif operation == "compare":
                return await self._compare(client, input_data, prompt)
            elif operation == "generate":
                return await self._generate(client, input_data, prompt)
            else:
                error_msg = (
                    f"Unknown operation: {operation}. Use 'analyze', 'compare', or 'generate'."
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
            error_msg = f"ChatGPT Images request failed: {e}"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

    async def _analyze(self, client: Any, input_data: dict, prompt: str) -> ToolResult:
        """Analyze a single image using GPT vision."""
        image_path_str = input_data.get("image_path")
        if not image_path_str:
            error_msg = "image_path is required for analyze operation"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        image_path = self._resolve_path(image_path_str)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        await self.coordinator.hooks.emit(
            "tool.openai_images.analyze",
            {"image_path": str(image_path), "model": self.vision_model},
        )

        mime_type = self._get_mime_type(image_path)
        image_b64 = self._encode_image_base64(image_path)

        response = client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )

        return ToolResult(
            success=True,
            output={"analysis": response.choices[0].message.content},
        )

    async def _compare(self, client: Any, input_data: dict, prompt: str) -> ToolResult:
        """Compare two images using GPT vision."""
        image1_path_str = input_data.get("image1_path")
        image2_path_str = input_data.get("image2_path")
        if not image1_path_str or not image2_path_str:
            error_msg = "image1_path and image2_path are required for compare operation"
            return ToolResult(success=False, output=error_msg, error={"message": error_msg})

        image1_path = self._resolve_path(image1_path_str)
        image2_path = self._resolve_path(image2_path_str)
        if not image1_path.exists():
            raise FileNotFoundError(f"Image not found: {image1_path}")
        if not image2_path.exists():
            raise FileNotFoundError(f"Image not found: {image2_path}")

        label1 = input_data.get("image1_label", "IMAGE 1")
        label2 = input_data.get("image2_label", "IMAGE 2")

        await self.coordinator.hooks.emit(
            "tool.openai_images.compare",
            {"image1_path": str(image1_path), "image2_path": str(image2_path)},
        )

        mime1 = self._get_mime_type(image1_path)
        mime2 = self._get_mime_type(image2_path)
        img1_b64 = self._encode_image_base64(image1_path)
        img2_b64 = self._encode_image_base64(image2_path)

        response = client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime1};base64,{img1_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": f"^ {label1}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime2};base64,{img2_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": f"^ {label2}"},
                    ],
                }
            ],
            max_tokens=4096,
        )

        return ToolResult(
            success=True,
            output={"comparison": response.choices[0].message.content},
        )

    async def _generate(self, client: Any, input_data: dict, prompt: str) -> ToolResult:
        """Generate images using gpt-image-2."""
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
        reference_path_str = input_data.get("reference_image_path")

        await self.coordinator.hooks.emit(
            "tool.openai_images.generate",
            {
                "output_path": str(output_path),
                "model": self.gen_model,
                "size": size,
                "quality": quality,
                "number_of_images": number_of_images,
                "has_reference": reference_path_str is not None,
            },
        )

        if reference_path_str:
            # Use the edit endpoint with reference image
            ref_path = self._resolve_path(reference_path_str)
            if not ref_path.exists():
                raise FileNotFoundError(f"Reference image not found: {ref_path}")

            with open(ref_path, "rb") as ref_file:
                edit_kwargs: dict[str, Any] = {
                    "model": self.gen_model,
                    "image": ref_file,
                    "prompt": prompt,
                    "n": number_of_images,
                    "quality": quality,
                }
                if size != "auto":
                    edit_kwargs["size"] = size
                result = client.images.edit(**edit_kwargs)
        else:
            # Standard generation
            gen_kwargs: dict[str, Any] = {
                "model": self.gen_model,
                "prompt": prompt,
                "n": number_of_images,
                "quality": quality,
            }
            if size != "auto":
                gen_kwargs["size"] = size
            result = client.images.generate(**gen_kwargs)

        # Save generated images
        generated_paths: list[str] = []
        for i, image_item in enumerate(result.data):
            if number_of_images == 1:
                current_output = output_path
            else:
                stem = output_path.stem
                suffix = output_path.suffix or ".png"
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