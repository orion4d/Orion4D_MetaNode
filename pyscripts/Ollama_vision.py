# ============================================================
# Ollama Vision + VRAM + Seed - PyCodeMax
# Entrées :
# - txt_in_1   : prompt
# - txt_in_2   : modèle Ollama
# - float_in_1 : temperature
# - int_in_1   : seed
# - img_in_1   : image
#
# Sorties :
# - txt_out_1  : réponse Ollama Vision
# - txt_out_2  : état VRAM
# ============================================================

DEFAULT_MODEL = "gemma4:e4b"

prompt = (IN.get("txt_in_1") or "").strip()
model_name = (IN.get("txt_in_2") or DEFAULT_MODEL).strip()
temperature = float(IN.get("float_in_1", 0.7))
seed = int(IN.get("int_in_1", -1))

images = IN.get("img_in_1")
image = images[0] if isinstance(images, list) and images else images


def format_vram():
    info = gpu["vram"]()

    if not info.get("available"):
        return f"VRAM non disponible : {info.get('reason', 'inconnu')}"

    return (
        "VRAM GPU\n"
        f"- Utilisée : {info['used_gb']:.2f} GB\n"
        f"- Libre    : {info['free_gb']:.2f} GB\n"
        f"- Total    : {info['total_gb']:.2f} GB\n"
        f"- Usage    : {info['percent_used']:.1f} %"
    )


vram_before = format_vram()

if not prompt:
    OUT["txt_out_1"] = "Erreur : prompt manquant dans txt_in_1."
    OUT["txt_out_2"] = vram_before

elif image is None:
    OUT["txt_out_1"] = "Erreur : aucune image fournie dans img_in_1."
    OUT["txt_out_2"] = vram_before

else:
    print(f"Envoi à Ollama avec le modèle : {model_name}")
    print(f"Seed utilisée : {seed}")

    # Si seed vaut -1, on ne la transmet pas à Ollama.
    # Cela laisse Ollama utiliser un comportement non fixé.
    extra_options = {}
    if seed >= 0:
        extra_options["seed"] = seed

    result = llm["generate"](
        prompt=prompt,
        model=model_name,
        images=[image],
        temperature=temperature,
        timeout=120,
        stream=False,
        **extra_options,
    )

    vram_after = format_vram()

    OUT["txt_out_1"] = result or "Erreur : réponse vide du modèle."
    OUT["txt_out_2"] = (
        f"=== Paramètres ===\n"
        f"Modèle : {model_name}\n"
        f"Temperature : {temperature}\n"
        f"Seed : {seed if seed >= 0 else 'non fixée'}\n\n"
        f"=== Avant Ollama ===\n"
        f"{vram_before}\n\n"
        f"=== Après Ollama ===\n"
        f"{vram_after}"
    )

    print("Réponse Ollama reçue.")