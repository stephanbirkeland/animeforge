"""ComfyUI backend - local generation via REST + WebSocket."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from animeforge.backend.base import GenerationRequest, GenerationResult

if TYPE_CHECKING:
    from animeforge.backend.base import ProgressCallback
    from animeforge.config import ComfyUISettings


class ComfyUIBackend:
    """ComfyUI generation backend using REST API and WebSocket for progress."""

    def __init__(
        self,
        settings: ComfyUISettings,
        output_dir: Path | None = None,
        checkpoint: str = "ponyDiffusionV6XL.safetensors",
    ) -> None:
        self.settings = settings
        self.output_dir = output_dir or Path.home() / ".animeforge" / "generated"
        self.checkpoint = checkpoint
        self._client: httpx.AsyncClient | None = None
        self._client_id = str(uuid.uuid4())

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        try:
            client = self._ensure_client()
            resp = await client.get("/system_stats")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        client = self._ensure_client()
        workflow = self._build_workflow(request)

        # Queue the prompt
        resp = await client.post(
            "/prompt",
            json={"prompt": workflow, "client_id": self._client_id},
        )
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]

        # Poll for completion
        images = await self._wait_for_result(prompt_id, progress_callback)

        return GenerationResult(
            images=images,
            seed=request.seed,
            prompt=request.prompt,
            metadata={"prompt_id": prompt_id},
        )

    async def get_models(self) -> list[str]:
        client = self._ensure_client()
        resp = await client.get("/object_info/CheckpointLoaderSimple")
        resp.raise_for_status()
        data = resp.json()
        return data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            msg = "Not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._client

    def _build_workflow(self, request: GenerationRequest) -> dict:
        """Build a ComfyUI workflow graph for the generation request."""
        workflow: dict[str, dict] = {}
        node_id = 1

        # Checkpoint loader
        ckpt_id = str(node_id)
        workflow[ckpt_id] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": self.checkpoint},
        }
        node_id += 1

        # Positive prompt
        pos_id = str(node_id)
        workflow[pos_id] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": request.prompt,
                "clip": [ckpt_id, 1],
            },
        }
        node_id += 1

        # Negative prompt
        neg_id = str(node_id)
        workflow[neg_id] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": request.negative_prompt or "low quality, blurry, deformed",
                "clip": [ckpt_id, 1],
            },
        }
        node_id += 1

        # Latent image or img2img
        if request.init_image:
            load_img_id = str(node_id)
            workflow[load_img_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": str(request.init_image)},
            }
            node_id += 1
            latent_id = str(node_id)
            workflow[latent_id] = {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": [load_img_id, 0],
                    "vae": [ckpt_id, 2],
                },
            }
        else:
            latent_id = str(node_id)
            workflow[latent_id] = {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": request.width,
                    "height": request.height,
                    "batch_size": request.batch_size,
                },
            }
        node_id += 1

        # KSampler
        sampler_id = str(node_id)
        workflow[sampler_id] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [ckpt_id, 0],
                "positive": [pos_id, 0],
                "negative": [neg_id, 0],
                "latent_image": [latent_id, 0],
                "seed": request.seed if request.seed >= 0 else 0,
                "steps": request.steps,
                "cfg": request.cfg_scale,
                "sampler_name": request.sampler,
                "scheduler": request.scheduler,
                "denoise": request.denoise_strength if request.init_image else 1.0,
            },
        }
        node_id += 1

        # VAE Decode
        decode_id = str(node_id)
        workflow[decode_id] = {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": [sampler_id, 0],
                "vae": [ckpt_id, 2],
            },
        }
        node_id += 1

        # Save image
        save_id = str(node_id)
        workflow[save_id] = {
            "class_type": "SaveImage",
            "inputs": {
                "images": [decode_id, 0],
                "filename_prefix": "animeforge",
            },
        }

        # Add ControlNet if specified
        if request.controlnet_image and request.controlnet_model:
            self._add_controlnet(
                workflow, request, ckpt_id, pos_id, neg_id, sampler_id, node_id
            )

        return workflow

    def _add_controlnet(
        self,
        workflow: dict,
        request: GenerationRequest,
        ckpt_id: str,
        pos_id: str,
        neg_id: str,
        sampler_id: str,
        node_id: int,
    ) -> None:
        """Insert ControlNet nodes into the workflow."""
        node_id += 1

        cn_load_id = str(node_id)
        workflow[cn_load_id] = {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": request.controlnet_model},
        }
        node_id += 1

        cn_img_id = str(node_id)
        workflow[cn_img_id] = {
            "class_type": "LoadImage",
            "inputs": {"image": str(request.controlnet_image)},
        }
        node_id += 1

        cn_apply_id = str(node_id)
        workflow[cn_apply_id] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": [pos_id, 0],
                "negative": [neg_id, 0],
                "control_net": [cn_load_id, 0],
                "image": [cn_img_id, 0],
                "strength": request.controlnet_strength,
            },
        }

        # Rewire sampler to use ControlNet-applied conditioning
        workflow[sampler_id]["inputs"]["positive"] = [cn_apply_id, 0]
        workflow[sampler_id]["inputs"]["negative"] = [cn_apply_id, 1]

    async def _wait_for_result(
        self,
        prompt_id: str,
        progress_callback: ProgressCallback | None,
        timeout: float = 600.0,
    ) -> list[Path]:
        """Poll ComfyUI history endpoint until generation is complete.

        Parameters
        ----------
        prompt_id:
            The ComfyUI prompt ID to poll for.
        progress_callback:
            Optional callback for progress updates.
        timeout:
            Maximum seconds to wait before raising ``TimeoutError``.
            Defaults to 600 (10 minutes).
        """
        import asyncio
        import time as _time

        client = self._ensure_client()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        deadline = _time.monotonic() + timeout
        while True:
            if _time.monotonic() > deadline:
                msg = (
                    f"Generation timed out after {timeout}s "
                    f"waiting for prompt {prompt_id}"
                )
                raise TimeoutError(msg)
            resp = await client.get(f"/history/{prompt_id}")
            resp.raise_for_status()
            history = resp.json()

            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                images: list[Path] = []
                for _node_id, node_output in outputs.items():
                    for img_data in node_output.get("images", []):
                        filename = img_data["filename"]
                        subfolder = img_data.get("subfolder", "")
                        img_resp = await client.get(
                            "/view",
                            params={
                                "filename": filename,
                                "subfolder": subfolder,
                                "type": "output",
                            },
                        )
                        img_resp.raise_for_status()
                        out_path = self.output_dir / filename
                        out_path.write_bytes(img_resp.content)
                        images.append(out_path)
                return images

            if progress_callback:
                progress_callback(0, 0, "Generating...")

            await asyncio.sleep(1.0)

    def _build_workflow_json(self, request: GenerationRequest) -> str:
        return json.dumps(self._build_workflow(request), indent=2)
