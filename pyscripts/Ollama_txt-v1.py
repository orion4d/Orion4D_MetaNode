# ============================================================
# Ollama Text Generate - PyCodeMax optimisé
# Entrées :
# - txt_in_1   : prompt
# - txt_in_2   : modèle Ollama
# - txt_in_3   : system prompt
# - float_in_1 : temperature
# - int_in_1   : seed
# - int_in_2   : think mode, 0/1
#
# Sorties :
# - txt_out_1  : réponse nettoyée
# - txt_out_2  : infos exécution
# ============================================================

import re

DEFAULT_MODEL = "gemma4:e4b"

prompt = (IN.get("txt_in_1") or "").strip()
model_name = (IN.get("txt_in_2") or DEFAULT_MODEL).strip()
system = (IN.get("txt_in_3") or "").strip()
temperature = float(IN.get("float_in_1") or 0.5)
seed = int(IN.get("int_in_1") or -1)
think_mode = bool(IN.get("int_in_2") or 0)

if not prompt:
    OUT["txt_out_1"] = "Erreur : prompt manquant"
    OUT["txt_out_2"] = ""

else:
    print(f"Envoi à Ollama : {model_name}")
    print(f"think:{think_mode} | temp:{temperature} | seed:{seed}")

    t0 = time.time()

    extra_options = {}
    if seed >= 0:
        extra_options["seed"] = seed

    raw = llm["generate"](
        prompt=prompt,
        model=model_name,
        system=system,
        temperature=temperature,
        think=think_mode,
        stream=False,
        timeout=120,
        **extra_options,
    )

    clean = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()

    elapsed = time.time() - t0

    OUT["txt_out_1"] = clean or "Erreur : réponse vide du modèle."
    OUT["txt_out_2"] = (
        f"Modèle : {model_name}\n"
        f"Think : {think_mode}\n"
        f"Temperature : {temperature}\n"
        f"Seed : {seed if seed >= 0 else 'non fixée'}\n"
        f"Temps : {elapsed:.1f}s"
    )

    print(f"OK | think:{think_mode} | {elapsed:.1f}s | temp:{temperature} | seed:{seed}")