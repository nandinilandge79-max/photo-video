
pip install fastapi uvicorn anthropic httpx python-multipart

export ANTHROPIC_API_KEY="sk-ant-..."
export REPLICATE_API_TOKEN="r8_..."      # optional, enables real AI video
# export REPLICATE_MODEL="owner/model"   # optional, any image-to-video model with "image" + "prompt" inputs

uvicorn main:app --reload
