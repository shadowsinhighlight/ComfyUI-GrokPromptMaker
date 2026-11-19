"""ComfyUI-GrokPromptMaker

One node: describe what you want, Grok (xAI API) writes the prompt, shaped by a
template (universal / text to image / text to video / image to video / image edit)
and a target model (universal / MiniMax H3 / Krea 2 / Krea 3 / FLUX 3 Klein).

FLUX 3 Klein uses Black Forest Labs' own prompt-upsampler system prompts
(guides/full_flux_3_klein_*.md) instead of the generic guides, so Grok can stand
in for BFL's upsampler.

The guidance Grok is given lives in guides/*.md and is read on every run, so it
can be edited without restarting ComfyUI.

No dependencies beyond what ComfyUI already has. numpy and PIL are imported
only when an image is attached.
"""

import base64
import io
import json
import os
import urllib.error
import urllib.request

TAG = "[GrokPromptMaker]"
HERE = os.path.dirname(os.path.abspath(__file__))
GUIDES = os.path.join(HERE, "guides")
KEY_FILE = os.path.join(HERE, "xai_api_key.txt")
API_URL = "https://api.x.ai/v1/chat/completions"

# Append only: saved workflows store these strings.
TEMPLATES = ["universal", "text to image", "text to video", "image to video", "image edit"]
TARGETS = ["universal", "minimax h3", "krea 2", "krea 3", "flux 3 klein"]
IMAGE_ONLY_TARGETS = {"krea 2", "krea 3", "flux 3 klein"}

# Targets with a complete system prompt of their own: (text-to-image guide, edit guide).
# They replace _base/template/model guides entirely.
FULL_GUIDES = {"flux 3 klein": ("full_flux_3_klein_t2i.md", "full_flux_3_klein_edit.md")}
VIDEO_TEMPLATES = {"text to video", "image to video"}

# Model IDs from docs.x.ai/developers/models (checked 2026-11-18). xAI retires
# models on a schedule, so custom_grok_model overrides this list.
GROK_MODELS = [
    "grok-4.7",
    "grok-4.6",
    "grok-4.5",
    "grok-4.3",
    "grok-4.20-0309-reasoning",
    "grok-4.20-0309-non-reasoning",
]


def _slug(name):
    return name.replace(" ", "_")


def _read_guide(filename):
    path = os.path.join(GUIDES, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError as e:
        raise RuntimeError(f"{TAG} guide file missing or unreadable: {path} ({e})")


def _strip_comment(text):
    if text.startswith("<!--"):
        end = text.find("-->")
        if end != -1:
            text = text[end + 3:].strip()
    return text


def wants_edit_prompt(template, has_image):
    return template == "image edit" or (template == "universal" and has_image)


def build_system_prompt(template, target_model, has_image=False):
    if target_model in FULL_GUIDES:
        t2i, edit = FULL_GUIDES[target_model]
        text = _strip_comment(_read_guide(edit if wants_edit_prompt(template, has_image) else t2i))
        if template in VIDEO_TEMPLATES:
            text += ("\n\nNOTE: the target model makes still images, not video. Caption the single "
                     "key frame of the scene (for a video workflow, the start frame). No motion over "
                     "time, no camera moves, no sound.")
        return text
    parts = [
        _read_guide("_base.md"),
        _read_guide(f"template_{_slug(template)}.md"),
        _read_guide(f"model_{_slug(target_model)}.md"),
    ]
    if target_model in IMAGE_ONLY_TARGETS and template in VIDEO_TEMPLATES:
        parts.append(
            f"NOTE: {target_model} makes still images, not video. Write the prompt "
            "for the single key frame of the scene (for a video workflow, the "
            "start frame), following the model rules above. No motion over time, "
            "no camera moves, no sound."
        )
    return "\n\n".join(parts)


def build_user_message(idea, template, duration_seconds, extra_instructions, has_image):
    lines = ["What I want:", idea.strip()]
    if template in VIDEO_TEMPLATES or template == "universal":
        if duration_seconds > 0:
            lines += ["", f"Clip length, if this is a video: {duration_seconds:g} seconds."]
    if has_image:
        if template == "image edit":
            lines += ["", "The attached image is the image to edit (the first image)."]
        else:
            lines += ["", "The attached image is the start frame / reference image."]
    if extra_instructions.strip():
        lines += ["", "Extra instructions:", extra_instructions.strip()]
    return "\n".join(lines)


def resolve_api_key(widget_value):
    key = (widget_value or "").strip()
    if key:
        return key
    key = os.environ.get("XAI_API_KEY", "").strip()
    if key:
        return key
    if os.path.isfile(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key
    raise RuntimeError(
        f"{TAG} no xAI API key. Set the XAI_API_KEY environment variable, or put "
        f"the key in {KEY_FILE}, or paste it into the api_key field (that last "
        "option saves the key inside the workflow and in the metadata of images "
        "made with it). Keys come from https://console.x.ai"
    )


def image_to_data_url(image, max_side=1024):
    """First frame of a ComfyUI IMAGE batch [B,H,W,C] float 0..1 -> JPEG data URL."""
    import numpy as np
    from PIL import Image

    frame = image[0] if len(image.shape) == 4 else image
    arr = (frame.detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr[..., :3])
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_payload(model, system_prompt, user_text, image_url, temperature, max_tokens):
    if image_url:
        user_content = [
            {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
            {"type": "text", "text": user_text},
        ]
    else:
        user_content = user_text
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }


def call_grok(api_key, payload, timeout=180):
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ComfyUI-GrokPromptMaker/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:800]
        hint = ""
        if e.code in (401, 403):
            hint = (" Check the API key. Note that a Grok / X Premium subscription "
                    "does not include API access: the API is billed separately at "
                    "https://console.x.ai")
        elif e.code == 404:
            hint = " The model ID may have been retired: try another, or set custom_grok_model."
        elif e.code == 429:
            hint = " Rate limit or no API credits left."
        raise RuntimeError(f"{TAG} xAI API returned HTTP {e.code}.{hint}\n{detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"{TAG} could not reach api.x.ai: {e.reason}")

    try:
        data = json.loads(body)
        text = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError(f"{TAG} unexpected response from xAI API:\n{body[:800]}")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(
            f"{TAG} Grok returned an empty prompt (finish_reason: "
            f"{data['choices'][0].get('finish_reason')}). A reasoning model can "
            "spend the whole max_tokens budget thinking: raise max_tokens.")
    return text


def clean_output(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'" and text.count(text[0]) == 2:
        text = text[1:-1].strip()
    return text


class GrokPromptMaker:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "idea": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": "What you want to happen, in plain words."}),
                "template": (TEMPLATES, {"default": "universal"}),
                "target_model": (TARGETS, {"default": "universal"}),
                "grok_model": (GROK_MODELS, {"default": GROK_MODELS[0]}),
                "duration_seconds": ("FLOAT", {
                    "default": 8.0, "min": 0.0, "max": 60.0, "step": 0.5,
                    "tooltip": "Clip length for video prompts. 0 = let Grok decide. "
                               "Ignored for image prompts."}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {
                    "default": 4000, "min": 256, "max": 32000, "step": 64,
                    "tooltip": "Includes reasoning tokens on reasoning models."}),
                "seed": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF,
                    "tooltip": "Not sent to Grok. Change it (or set it to randomize) "
                               "to get a new prompt for the same idea; leave it fixed "
                               "and ComfyUI reuses the last prompt without a new API call."}),
            },
            "optional": {
                "image": ("IMAGE", {
                    "tooltip": "Start frame or reference image. Grok looks at it, so "
                               "the prompt matches what is actually in the picture."}),
                "extra_instructions": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": "Anything else Grok should follow, e.g. 'one continuous "
                               "take', 'no dialogue', 'under 80 words'."}),
                "custom_grok_model": ("STRING", {
                    "default": "",
                    "tooltip": "A model ID to use instead of the list, for models "
                               "newer than this node."}),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "Leave empty to use the XAI_API_KEY environment variable "
                               "or xai_api_key.txt in this node's folder. A key typed "
                               "here is saved in the workflow and in image metadata."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "system_prompt")
    FUNCTION = "make"
    CATEGORY = "prompt/Grok"
    OUTPUT_NODE = True
    DESCRIPTION = ("Describe what you want; Grok writes the prompt for the chosen "
                   "template and target model.")

    def make(self, idea, template, target_model, grok_model, duration_seconds,
             temperature, max_tokens, seed, image=None, extra_instructions="",
             custom_grok_model="", api_key=""):
        if not idea.strip():
            raise RuntimeError(f"{TAG} the idea field is empty.")

        model = custom_grok_model.strip() or grok_model
        image_url = image_to_data_url(image) if image is not None else None
        system_prompt = build_system_prompt(template, target_model, image_url is not None)
        if target_model in IMAGE_ONLY_TARGETS and template in VIDEO_TEMPLATES:
            print(f"{TAG} {target_model} is an image model: writing a still-frame "
                  f"prompt although the template is '{template}'.")
        user_text = build_user_message(idea, template, duration_seconds,
                                       extra_instructions, image_url is not None)
        payload = build_payload(model, system_prompt, user_text, image_url,
                                temperature, max_tokens)
        key = resolve_api_key(api_key)

        print(f"{TAG} asking {model} ({template} / {target_model})...")
        prompt = clean_output(call_grok(key, payload))
        print(f"{TAG} got {len(prompt.split())} words.")
        return {"ui": {"text": [prompt]}, "result": (prompt, system_prompt)}


NODE_CLASS_MAPPINGS = {"GrokPromptMaker": GrokPromptMaker}
NODE_DISPLAY_NAME_MAPPINGS = {"GrokPromptMaker": "Grok Prompt Maker"}
WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
