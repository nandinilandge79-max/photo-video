# Photo to Video

Upload a photo, pick a camera style, get a short video. Claude analyses the photo and writes the motion prompt; a video model (Replicate) renders it. With no Replicate token, the browser renders a camera-move preview instead, so the app works end to end for free.

## Run it

```bash
cd backend
pip install fastapi uvicorn anthropic httpx python-multipart

export ANTHROPIC_API_KEY="sk-ant-..."
export REPLICATE_API_TOKEN="r8_..."      # optional, enables real AI video
# export REPLICATE_MODEL="owner/model"   # optional, any image-to-video model with "image" + "prompt" inputs

uvicorn main:app --reload
```

Then open `frontend/index.html` in a browser.

## Deploy

- Frontend: Vercel or Netlify (static). Change `API` at the top of the script to your backend URL.
- Backend: Render or Railway. Set the environment variables above in their dashboard, and restrict `allow_origins` in `main.py` to your frontend's URL.
