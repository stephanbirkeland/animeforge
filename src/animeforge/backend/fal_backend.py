"""fal.ai cloud backend for image generation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from animeforge.backend.base import GenerationRequest, GenerationResult

if TYPE_CHECKING:
    from animeforge.backend.base import ProgressCallback
    from animeforge.config import FalSettings

logger = logging.getLogger(__name__)


class FalBackend:
    """Cloud generation backend using fal.ai API.

    Supports SDXL generation including Pony V7, ControlNet, and IP-Adapter
    via simple API calls — no local GPU needed.
    """

    def __init__(self, settings: FalSettings, output_dir: Path | None = None) -> None:
        self._settings = settings
        self.output_dir = output_dir or Path.home() / ".animeforge" / "fal_output"
        self._api_key: str = ""

    async def connect(self) -> None:
        """Resolve API key and prepare output directory."""
        self._api_key = self._settings.api_key or os.environ.get("FAL_KEY", "")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def disconnect(self) -> None:
        """No persistent connection to close."""

    async def is_available(self) -> bool:
        """Check if fal.ai is reachable and API key is set."""
        if not self._api_key:
            logger.warning("fal.ai API key not configured (set FAL_KEY or config.fal.api_key)")
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://queue.fal.run/fal-ai/pony-v7",
                    headers={"Authorization": f"Key {self._api_key}"},
                )
                # 401/403 means key is invalid, but the service is up
                # 200/422 means the service is up and key works
                return resp.status_code != 401
        except (httpx.HTTPError, OSError):
            return False

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Generate images via fal.ai API."""
        import fal_client

        endpoint = self._select_endpoint(request)
        params = await self._build_params(request)

        if progress_callback:
            progress_callback(1, 10, f"Submitting to {endpoint}")

        def on_queue_update(update: Any) -> None:
            if progress_callback is None:
                return
            status_type = getattr(update, "status", "")
            if status_type == "IN_QUEUE":
                progress_callback(2, 10, "Queued...")
            elif status_type == "IN_PROGRESS":
                logs = getattr(update, "logs", [])
                step = min(3 + len(logs), 8)
                last_log = logs[-1].get("message", "Generating...") if logs else "Generating..."
                progress_callback(step, 10, last_log)

        result = fal_client.subscribe(
            endpoint,
            arguments=params,
            with_logs=True,
            on_queue_update=on_queue_update,
        )

        if progress_callback:
            progress_callback(9, 10, "Downloading images...")

        images = await self._download_images(result, request)

        if progress_callback:
            progress_callback(10, 10, "Complete")

        seed = result.get("seed", request.seed)
        return GenerationResult(
            images=images,
            seed=seed if isinstance(seed, int) else -1,
            prompt=request.prompt,
            metadata={"backend": "fal", "endpoint": endpoint},
        )

    async def get_models(self) -> list[str]:
        """Return the configured fal.ai model endpoints."""
        return [
            self._settings.default_model,
            self._settings.controlnet_model,
            self._settings.ip_adapter_model,
        ]

    def _select_endpoint(self, request: GenerationRequest) -> str:
        """Select the appropriate fal.ai endpoint based on request type."""
        if request.controlnet_image and request.controlnet_model:
            return self._settings.controlnet_model
        if request.ip_adapter_image:
            return self._settings.ip_adapter_model
        return self._settings.default_model

    async def _build_params(self, request: GenerationRequest) -> dict[str, Any]:
        """Map GenerationRequest fields to fal.ai API parameters."""
        params: dict[str, Any] = {
            "prompt": request.prompt,
            "image_size": {
                "width": request.width,
                "height": request.height,
            },
            "num_inference_steps": request.steps,
            "guidance_scale": request.cfg_scale,
            "num_images": request.batch_size,
        }

        if request.negative_prompt:
            params["negative_prompt"] = request.negative_prompt

        if request.seed >= 0:
            params["seed"] = request.seed

        # ControlNet params
        if request.controlnet_image:
            image_url = await self._prepare_image_url(request.controlnet_image)
            params["control_image"] = image_url
            params["controlnet_conditioning_scale"] = request.controlnet_strength

        # IP-Adapter params
        if request.ip_adapter_image:
            image_url = await self._prepare_image_url(request.ip_adapter_image)
            params["face_image"] = image_url
            params["ip_adapter_scale"] = request.ip_adapter_weight

        # img2img params
        if request.init_image:
            image_url = await self._prepare_image_url(request.init_image)
            params["image"] = image_url
            params["strength"] = request.denoise_strength

        return params

    async def _prepare_image_url(self, image_path: Path) -> str:
        """Upload a local image to fal CDN and return the URL."""
        import fal_client

        url: str = fal_client.upload_file(image_path)
        return url

    async def _download_images(
        self, result: dict[str, Any], request: GenerationRequest,
    ) -> list[Path]:
        """Download generated images from fal CDN to local output directory."""
        images_data = result.get("images", [])
        if not images_data:
            logger.warning("fal.ai returned no images")
            return []

        downloaded: list[Path] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, img_data in enumerate(images_data):
                url = img_data.get("url", "")
                if not url:
                    continue

                resp = await client.get(url)
                resp.raise_for_status()

                seed = result.get("seed", request.seed)
                filename = f"fal_{seed}_{request.width}x{request.height}_{i}.png"
                out_path = self.output_dir / filename
                out_path.write_bytes(resp.content)
                downloaded.append(out_path)
                logger.info("Downloaded: %s", out_path)

        return downloaded
