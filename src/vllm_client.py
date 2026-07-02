# src/vllm_client.py
from openai import OpenAI

def get_vllm_client():
    return OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="vllm-token-placeholder"  # vLLM requires a placeholder string
    )

MODEL_NAME = "aleynahukmet/chem-coder-merged-model"