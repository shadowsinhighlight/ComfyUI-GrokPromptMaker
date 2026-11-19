# ComfyUI-GrokPromptMaker

One node, **Grok Prompt Maker** (category `prompt/Grok`). Type what you want to
happen; Grok writes the prompt.

## Setup

1. Get an API key at https://console.x.ai. The API is billed separately from a
   Grok / X Premium subscription: the subscription alone does not give API access.
2. Give the node the key, one of:
   - environment variable `XAI_API_KEY` (set before starting ComfyUI), or
   - a file `xai_api_key.txt` in this folder holding only the key, or
   - the `api_key` field on the node. This saves the key in the workflow and in
     the metadata of images made with it, so avoid it for anything you share.
3. Restart ComfyUI.

## Inputs

| Input | What it does |
|---|---|
| `idea` | What you want, in plain words |
| `template` | universal, text to image, text to video, image to video, image edit |
| `target_model` | universal, minimax h3, krea 2, krea 3, flux 3 klein |
| `grok_model` | Which Grok model writes the prompt |
| `duration_seconds` | Clip length for video prompts (0 = Grok decides) |
| `seed` | Not sent to Grok. Change it to get a new prompt; fixed = no new API call |
| `image` (optional) | Start frame or reference. Grok looks at it |
| `extra_instructions` (optional) | Anything else to follow |
| `custom_grok_model` (optional) | A model ID not in the list |

Outputs: `prompt` (wire into your text encoder) and `system_prompt` (what Grok
was told, for checking).

## Changing the guidance

What Grok is told is in `guides/`: `_base.md`, one `template_*.md` and one
`model_*.md` per choice. They are read on every run, so edits take effect on
the next queue, no restart.

Krea 2, Krea 3 and FLUX 3 Klein are image models. With a video template they get a
still-frame prompt (the start frame of the scene).

## FLUX 3 Klein

Klein is trained on full scene captions and expects a prompt upsampler in front of it.
The `flux 3 klein` target makes Grok that upsampler: it sends Black Forest Labs' own
upsampler system prompts (`guides/full_flux_3_klein_t2i.md` and
`full_flux_3_klein_edit.md`, verbatim from BFL's official ComfyUI workflows) instead
of the generic guides.

- `text to image` (or `universal` with no image): a full scene caption.
- `image edit` (or `universal` with an image attached): an edit instruction for the
  attached image, written by Grok while looking at it.
- Wire `prompt` into Klein's prompt input with Klein's own upsampler switched off.
- Grok sees one image. For multi-reference edits, attach the main image and describe
  the others in `idea` by order ("image 2", "image 3").

The `image edit` template works with the other targets too, with a generic edit guide.

The MiniMax H3 guide writes the base-mode format (`integrated_multimodal_description`,
`overall_soundscape`, `non_diegetic_music`). For reference-driven H3 work with
subjects and pictures, use ComfyUI-H3-PromptBuilder instead.
