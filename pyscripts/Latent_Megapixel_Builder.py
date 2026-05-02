# ======================================================================
# 📖 Latent Megapixel Builder — FORCE x16 DEBUG
# Génère un Empty Latent en considérant que 1 case latent = 16 pixels décodés.
# À utiliser si ton VAE Decode sort 2048 px quand tu attends 1024 px.
#
# Entrées :
# - txt_in_1 : Ratio, ex: "1:1 (Perfect Square)" ou "16:9"
# - txt_in_2 : Mégapixels, ex: "1.0"
# - txt_in_3 : Divisible par, ex: "64"
# - int_in_1 : Batch Size
#
# Sorties :
# - latent_out : latent ComfyUI
# - int_out_1 : largeur décodée prévue
# - int_out_2 : hauteur décodée prévue
# ======================================================================

import re

VAE_SCALE = 16  # FORCE : 1 latent pixel = 16 pixels image

ratio_str = IN.get("txt_in_1", "1:1")
mp_str = IN.get("txt_in_2", "1.0")
div_str = IN.get("txt_in_3", "64")
batch_size = IN.get("int_in_1", 1)


def clean_text(v, default=""):
    if v is None:
        return default
    return str(v).strip()


def first_number(v, default=1.0):
    txt = clean_text(v, str(default)).replace(",", ".")
    m = re.search(r"[-+]?\d*\.?\d+", txt)
    if not m:
        return default
    try:
        return float(m.group(0))
    except Exception:
        return default


def parse_ratio(v):
    txt = clean_text(v, "1:1")
    m = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", txt)
    if not m:
        return 1.0, 1.0, "1:1"
    rw = float(m.group(1))
    rh = float(m.group(2))
    return max(rw, 0.0001), max(rh, 0.0001), f"{m.group(1)}:{m.group(2)}"


def round_to_multiple(value, multiple):
    return int(round(value / multiple) * multiple)


rw, rh, clean_ratio = parse_ratio(ratio_str)
target_mp = max(0.0001, first_number(mp_str, 1.0))
divisible_by = max(1, int(first_number(div_str, 64)))
batch_size = max(1, int(first_number(batch_size, 1)))

# Résolution image cible à partir des mégapixels.
target_area = target_mp * 1_000_000.0
ratio_val = rw / rh
h_exact = math.sqrt(target_area / ratio_val)
w_exact = h_exact * ratio_val

# On garde une résolution cible propre côté image.
width_target = max(divisible_by, round_to_multiple(w_exact, divisible_by))
height_target = max(divisible_by, round_to_multiple(h_exact, divisible_by))

# IMPORTANT : pour un decode x16, le latent doit être 16 fois plus petit.
# On arrondit aussi le latent pour éviter les demi-tailles.
latent_w = max(1, round_to_multiple(width_target / VAE_SCALE, max(1, divisible_by // VAE_SCALE)))
latent_h = max(1, round_to_multiple(height_target / VAE_SCALE, max(1, divisible_by // VAE_SCALE)))

width_decoded = latent_w * VAE_SCALE
height_decoded = latent_h * VAE_SCALE

latent_tensor = torch.zeros([batch_size, 4, latent_h, latent_w])
OUT["latent_out"] = {"samples": latent_tensor}
OUT["int_out_1"] = width_decoded
OUT["int_out_2"] = height_decoded