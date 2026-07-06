from openai import OpenAI

# vLLM local server address
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="vllm-token-placeholder" # vLLM does not want this to be empty, you can write a random string.
)

# Simple connection test
response = client.chat.completions.create(
    model="aleynahukmet/chem-coder-merged-model",
    messages=[
        {"role": "user", "content": "Explain the IUPAC name and general use of the Aspirin molecule briefly."}
    ]
)

print("Model Response:\n", response.choices[0].message.content)