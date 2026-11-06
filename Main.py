import asyncio
import base64
import os

import anthropic
import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Keys come from environment variables, never from source code.
#   ANTHROPIC_API_KEY   (required)
#   REPLICATE_API_TOKEN (optional - without it the app returns the prompt only
#                        and the browser renders a camera-move preview itself)
#   REPLICATE_MODEL     (optional - any Replicate image-to-video model that
#                        accepts "image" and "prompt" inputs)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "wavespeedai/wan-2.1-i2v-480p")
REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024  # Claude's image limit

STYLES = {
    "cinematic": "slow cinematic push-in, shallow depth of field, gentle film grain",
    "parallax": "3D parallax tilt that separates foreground from background",
    "pan": "smooth realistic camera pan with natural handheld sway",
    "loop": "subtle seamless loop suitable for social media, minimal drift",
    "anime": "stylised anime motion, soft wind in hair and clothes, painterly light",
}

app = FastAPI(title="Photo to Video")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend's URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)
claude = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY


async def write_motion_prompt(b64: str, media_type: str, style: str, extra: str) -> str:
    brief = (
        "Look at this photo and write one paragraph that works as a prompt for an "
        "image-to-video generator. Describe the lighting, the camera movement and any "
        "believable movement of the subjects, based only on what is visible. "
        f"Style: {STYLES[style]}."
    )
    if extra:
        brief += f" The user also asks for: {extra}"
    msg = await claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": brief},
            ],
        }],
    )
    return msg.content[0].text.strip()


async def render_video(b64: str, media_type: str, prompt: str) -> str:
    headers = {"Authorization": f"Bearer {REPLICATE_TOKEN}", "Prefer": "wait=60"}
    body = {"input": {"image": f"data:{media_type};base64,{b64}", "prompt": prompt}}
    url = f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions"
    async with httpx.AsyncClient(timeout=90) as http:
        pred = (await http.post(url, headers=headers, json=body)).json()
        for _ in range(60):  # poll for up to ~3 minutes
            if pred.get("status") in ("succeeded", "failed", "canceled"):
                break
            await asyncio.sleep(3)
            pred = (await http.get(pred["urls"]["get"], headers=headers)).json()
    if pred.get("status") != "succeeded":
        raise HTTPException(502, f"Video generation failed: {pred.get('error') or pred.get('detail')}")
    out = pred["output"]
    return out[0] if isinstance(out, list) else out


@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    style: str = Form("cinematic"),
    prompt: str = Form(""),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Upload a JPEG, PNG, GIF or WebP image.")
    if style not in STYLES:
        raise HTTPException(400, f"Unknown style. Choose one of: {', '.join(STYLES)}")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "Image is over 5 MB. Upload a smaller one.")

    b64 = base64.b64encode(data).decode()
    motion_prompt = await write_motion_prompt(b64, file.content_type, style, prompt.strip())
    video_url = await render_video(b64, file.content_type, motion_prompt) if REPLICATE_TOKEN else None
    return {"prompt": motion_prompt, "video_url": video_url}
