# src/vllm_client.py
from openai import OpenAI
from src.config import LLM_BASE_URL, LLM_API_KEY, MODEL_NAME

def get_vllm_client():
    return OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY
    )
