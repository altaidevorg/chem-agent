from openai import OpenAI

# vLLM local sunucu adresi
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="vllm-token-placeholder" # vLLM boş geçilmesini istemez, rastgele bir string yazabilirsin.
)

# Basit bir bağlantı testi
response = client.chat.completions.create(
    model="aleynahukmet/chem-coder-merged-model",
    messages=[
        {"role": "user", "content": "Aspirin molekülünün IUPAC adını ve genel kullanım amacını kısaca açıkla."}
    ]
)

print("Model Yanıtı:\n", response.choices[0].message.content)