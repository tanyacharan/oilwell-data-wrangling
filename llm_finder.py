import google.generativeai as genai

API_KEY = "AIzaSyC04Om2NPvtFTbAUaM2v1KWTxgYWn7wWQU"
genai.configure(api_key=API_KEY)

models = genai.list_models()
print("Available models:")
for m in models:
    # Use dot notation
    capabilities = getattr(m, "capabilities", [])
    print(f"{m.name} - supported methods: {capabilities}")
