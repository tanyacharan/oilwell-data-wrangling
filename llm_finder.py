import google.generativeai as genai

API_KEY = ""
genai.configure(api_key=API_KEY)

models = genai.list_models()
print("Available models:")
for m in models:
    # Use dot notation
    capabilities = getattr(m, "capabilities", [])
    print(f"{m.name} - supported methods: {capabilities}")
