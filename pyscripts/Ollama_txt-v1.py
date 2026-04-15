import requests
import json
import re

OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

prompt      = IN.get("txt_in_1", "")
model_name  = IN.get("txt_in_2", "gemma4:e4b")
system      = IN.get("txt_in_3", "")
temperature = float(IN.get("float_in_1") or 0.5)
seed        = int(IN.get("int_in_1") or -1)
think_mode  = bool(IN.get("int_in_2") or 0)  # 0 = off, 1 = on

if not prompt:
    OUT["txt_out_1"] = "Erreur: prompt manquant"
else:
    payload = {
        "model":   model_name,
        "prompt":  prompt,
        "system":  system,
        "stream":  False,
        "think":   think_mode,
        "options": {
            "temperature": temperature,
            "seed": seed
        }
    }
    try:
        t0 = time.time()
        r = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        r.raise_for_status()
        raw = r.json().get("response", "").strip()

        # Nettoyage défensif des blocs <think>
        clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        elapsed = time.time() - t0
        OUT["txt_out_1"] = clean
        OUT["txt_out_2"] = f"think:{think_mode} | {elapsed:.1f}s | {model_name}"
        print(f"OK | think:{think_mode} | {elapsed:.1f}s | temp:{temperature} | seed:{seed}")

    except Exception as e:
        OUT["txt_out_1"] = f"Erreur: {e}"