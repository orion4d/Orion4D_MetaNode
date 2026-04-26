# --- START OF FILE color_fx_common.py ---
#
# Color Pro — infrastructure commune des nodes FX de colorimétrie.
#
# Architecture émetteur/récepteur :
#   - Chaque FX (ChannelMixer, CSSFilters, etc.) est un node "émetteur" qui
#     ne reçoit pas d'image mais produit un dict {"type", "enabled", "label",
#     "params"} de type COLOR_FX.
#   - Le récepteur (ColorProReceiver) prend une IMAGE + plusieurs slots
#     dynamiques fx_1, fx_2, ... de type COLOR_FX, et applique la chaîne
#     dans l'ordre numérique des slots.
#
# Ce fichier contient :
#   - Le type custom COLOR_FX (juste une string, ComfyUI gère le reste)
#   - Les helpers de conversion tensor ↔ numpy
#   - Le REGISTRY central qui mappe "type" → fonction d'application
#   - Les fonctions d'effet pures (channel_mixer pour le MVP)
#
# Ajouter un nouveau FX = implémenter la fonction d'effet pure + l'enregistrer
# dans FX_REGISTRY via @register_fx("nom"), puis créer le node émetteur.

import numpy as np
import torch

# ---------------------------------------------------------------------------
# Type custom pour les connexions entre FX et récepteur
# ---------------------------------------------------------------------------
# ComfyUI traite les types custom comme des chaînes opaques : il suffit que
# les deux côtés d'une connexion utilisent la même chaîne pour que le lien
# soit accepté. Le récepteur fera un `isinstance(value, dict)` au runtime.
COLOR_FX_TYPE = "COLOR_FX"


# ---------------------------------------------------------------------------
# Helpers de conversion
# ---------------------------------------------------------------------------
def tensor_to_numpy(image: torch.Tensor) -> np.ndarray:
    """(B,H,W,C) ou (H,W,C) torch → (H,W,C) numpy float32 [0..1].

    Le récepteur boucle sur le batch dans sa propre fonction d'exécution,
    donc on travaille image par image ici.
    """
    if image.ndim == 4:
        image = image[0]
    return image.cpu().numpy().astype(np.float32)


def numpy_to_tensor(arr: np.ndarray) -> torch.Tensor:
    """(H,W,C) numpy [0..1] → (1,H,W,C) torch float32."""
    arr = np.clip(arr, 0.0, 1.0).astype(np.float32)
    return torch.from_numpy(arr).unsqueeze(0)


# ---------------------------------------------------------------------------
# Registry des effets
# ---------------------------------------------------------------------------
# Chaque fonction d'effet a la signature :
#   (img: np.ndarray, params: dict) -> np.ndarray
# Elle reçoit une image (H, W, C) float32 [0..1] et renvoie une image de
# même shape également [0..1] (le récotu recupère et passe au suivant).
FX_REGISTRY: dict = {}


def register_fx(type_name: str):
    """Décorateur pour enregistrer une fonction d'effet."""
    def decorator(fn):
        FX_REGISTRY[type_name] = fn
        return fn
    return decorator


def apply_fx_chain(image: torch.Tensor, fx_list: list) -> torch.Tensor:
    """Applique une chaîne de FX sur une image (éventuellement en batch).

    - fx_list est une liste de dicts {"type", "enabled", "label", "params"}
    - Les FX non-dict ou sans "type" connu sont ignorés avec un warning
    - Les FX avec enabled=False sont ignorés silencieusement
    - Le batch est traité image par image
    """
    if image.ndim != 4:
        # (H, W, C) → ajouter la dim batch
        image = image.unsqueeze(0)

    results = []
    for b_idx in range(image.shape[0]):
        img_np = image[b_idx].cpu().numpy().astype(np.float32)

        for fx in fx_list:
            if not isinstance(fx, dict):
                continue
            if not fx.get("enabled", True):
                continue
            fx_type = fx.get("type")
            if fx_type not in FX_REGISTRY:
                print(f"[ColorPro] FX inconnu ignoré : '{fx_type}'")
                continue
            try:
                img_np = FX_REGISTRY[fx_type](img_np, fx.get("params", {}))
            except Exception as e:
                label = fx.get("label") or fx_type
                print(f"[ColorPro] Erreur dans '{label}' ({fx_type}) : {e}")
                # On continue avec l'image telle qu'elle était avant ce FX
                continue
            img_np = np.clip(img_np, 0.0, 1.0)

        results.append(torch.from_numpy(img_np))

    return torch.stack(results, dim=0).to(torch.float32)


def collect_fx_from_kwargs(kwargs: dict) -> list:
    """Récupère et ordonne tous les fx_N du kwargs par ordre numérique.

    Tolère les trous (fx_1, fx_3, fx_5 → applique dans cet ordre) et ignore
    les None (slot déclaré mais non branché).
    """
    fx_entries = []
    for key, value in kwargs.items():
        if not key.startswith("fx_"):
            continue
        if value is None:
            continue
        try:
            idx = int(key.split("_", 1)[1])
        except (ValueError, IndexError):
            continue
        fx_entries.append((idx, value))
    fx_entries.sort(key=lambda e: e[0])
    return [v for _, v in fx_entries]


def build_fx_output(
    fx_type: str,
    enabled: bool,
    label: str,
    params: dict,
) -> dict:
    """Helper utilisé par tous les nodes émetteurs pour construire le dict
    standard qu'ils émettent. Garantit une forme uniforme."""
    return {
        "type":    fx_type,
        "enabled": bool(enabled),
        "label":   str(label or ""),
        "params":  dict(params),
    }


def apply_single_fx_inline(image, fx_dict):
    """Mode hybride : applique un seul FX directement sur une image.

    Utilisé par les nodes émetteurs qui exposent aussi un input/output
    IMAGE pour permettre l'usage standalone (sans Color Pro Receiver).

    - Si `image` est None, retourne None (la sortie image du node sera ignorée).
    - Si le FX est désactivé, on retourne l'image telle quelle.
    - Sinon, on applique le FX via la chaîne (qui gère 1 ou N effets).
    """
    if image is None:
        return None
    return apply_fx_chain(image, [fx_dict])


# ---------------------------------------------------------------------------
# FX 1 : Channel Mixer (fonction pure, adaptée du fichier d'origine)
# ---------------------------------------------------------------------------
@register_fx("channel_mixer")
def _apply_channel_mixer(img: np.ndarray, params: dict) -> np.ndarray:
    """Mixe les canaux R/G/B selon la configuration Channel Mixer classique.

    params attendus :
      output_channel: "Red" | "Green" | "Blue"
      red_source, green_source, blue_source : float en pourcentage [-200..200]
      constant : float en pourcentage [-200..200]
      monochrome : bool
      preserve_luminosity : bool
    """
    output_channel       = params.get("output_channel", "Red")
    red_factor           = float(params.get("red_source",   100.0)) / 100.0
    green_factor         = float(params.get("green_source",   0.0)) / 100.0
    blue_factor          = float(params.get("blue_source",    0.0)) / 100.0
    constant_factor      = float(params.get("constant",       0.0)) / 100.0
    monochrome           = bool(params.get("monochrome", False))
    preserve_luminosity  = bool(params.get("preserve_luminosity", False))

    result = img.copy()

    # Sauvegarde de la luminance pour préservation éventuelle
    if preserve_luminosity:
        original_lum = (
            0.299 * result[:, :, 0]
            + 0.587 * result[:, :, 1]
            + 0.114 * result[:, :, 2]
        )

    # Mix effectif
    mixed = (
        result[:, :, 0] * red_factor
        + result[:, :, 1] * green_factor
        + result[:, :, 2] * blue_factor
        + constant_factor
    )
    mixed = np.clip(mixed, 0.0, 1.0)

    if monochrome:
        result[:, :, 0] = mixed
        result[:, :, 1] = mixed
        result[:, :, 2] = mixed
    else:
        if output_channel == "Red":
            result[:, :, 0] = mixed
        elif output_channel == "Green":
            result[:, :, 1] = mixed
        elif output_channel == "Blue":
            result[:, :, 2] = mixed

    # Restaurer la luminance si demandé (et seulement en mode couleur)
    if preserve_luminosity and not monochrome:
        new_lum = (
            0.299 * result[:, :, 0]
            + 0.587 * result[:, :, 1]
            + 0.114 * result[:, :, 2]
        )
        ratio = np.where(new_lum > 1e-3, original_lum / new_lum, 1.0)
        result = result * ratio[..., np.newaxis]

    return np.clip(result, 0.0, 1.0)


# ---------------------------------------------------------------------------
# FX 2 : CSS Filters (équivalents des filter: CSS du navigateur)
# ---------------------------------------------------------------------------
# Adapté de css_filters_node.py — 8 sous-effets dans un seul FX :
#   blur, brightness, contrast, grayscale, sepia, hue_rotate, saturate, invert
#
# On utilise PIL pour brightness/contrast/saturate/blur (rapide et fiable)
# et numpy pur pour les autres (pas de dépendance cv2 obligatoire ici).

@register_fx("css_filters")
def _apply_css_filters(img: np.ndarray, params: dict) -> np.ndarray:
    """Applique une combinaison des filtres CSS standard.

    params attendus (tous optionnels) :
      blur         : float   ≥ 0       — rayon du flou gaussien
      brightness   : float in [0..300] — 100 = neutre
      contrast     : float in [0..300] — 100 = neutre
      saturate     : float in [0..300] — 100 = neutre
      grayscale    : float in [0..100] — 0 = couleur, 100 = N&B
      sepia        : float in [0..100] — 0 = neutre, 100 = sépia complet
      hue_rotate   : float in [-180..180] — degrés
      invert       : float in [0..100] — 0 = normal, 100 = inversé
    """
    from PIL import Image, ImageEnhance, ImageFilter

    blur        = float(params.get("blur",         0.0))
    brightness  = float(params.get("brightness", 100.0))
    contrast    = float(params.get("contrast",   100.0))
    saturate    = float(params.get("saturate",   100.0))
    grayscale   = float(params.get("grayscale",    0.0))
    sepia       = float(params.get("sepia",        0.0))
    hue_rotate  = float(params.get("hue_rotate",   0.0))
    invert      = float(params.get("invert",       0.0))

    # Conversion vers PIL pour les effets simples
    pil_img = Image.fromarray((img * 255.0).clip(0, 255).astype(np.uint8))

    if blur > 0.0:
        pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=blur))

    if abs(brightness - 100.0) > 0.01:
        pil_img = ImageEnhance.Brightness(pil_img).enhance(brightness / 100.0)

    if abs(contrast - 100.0) > 0.01:
        pil_img = ImageEnhance.Contrast(pil_img).enhance(contrast / 100.0)

    if abs(saturate - 100.0) > 0.01:
        pil_img = ImageEnhance.Color(pil_img).enhance(saturate / 100.0)

    # Retour en numpy pour les effets matriciels
    result = np.array(pil_img, dtype=np.float32)  # [0..255]

    if grayscale > 0.0:
        # Luminance perceptuelle, broadcast sur 3 canaux
        gray = (
            0.299 * result[:, :, 0]
            + 0.587 * result[:, :, 1]
            + 0.114 * result[:, :, 2]
        )
        gray_rgb = np.stack([gray, gray, gray], axis=-1)
        alpha = grayscale / 100.0
        result = result * (1.0 - alpha) + gray_rgb * alpha

    if sepia > 0.0:
        # Matrice sépia standard (Microsoft Office, identique à css_filters d'origine)
        sepia_matrix = np.array([
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131],
        ], dtype=np.float32)
        sepia_img = result @ sepia_matrix.T
        sepia_img = np.clip(sepia_img, 0.0, 255.0)
        alpha = sepia / 100.0
        result = result * (1.0 - alpha) + sepia_img * alpha

    if abs(hue_rotate) > 0.01:
        # Rotation de teinte via matrice 3×3 (formule ITU-R BT.601 + rotation YIQ).
        # On évite cv2 ici pour ne pas imposer une dépendance dans le commun.
        # Référence : https://www.w3.org/TR/filter-effects-1/#huerotateEquivalent
        angle = np.radians(hue_rotate)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        # Matrice de rotation de teinte approximative (W3C feColorMatrix)
        m = np.array([
            [0.213 + 0.787 * cos_a - 0.213 * sin_a,
             0.715 - 0.715 * cos_a - 0.715 * sin_a,
             0.072 - 0.072 * cos_a + 0.928 * sin_a],
            [0.213 - 0.213 * cos_a + 0.143 * sin_a,
             0.715 + 0.285 * cos_a + 0.140 * sin_a,
             0.072 - 0.072 * cos_a - 0.283 * sin_a],
            [0.213 - 0.213 * cos_a - 0.787 * sin_a,
             0.715 - 0.715 * cos_a + 0.715 * sin_a,
             0.072 + 0.928 * cos_a + 0.072 * sin_a],
        ], dtype=np.float32)
        result = result @ m.T
        result = np.clip(result, 0.0, 255.0)

    if invert > 0.0:
        inverted = 255.0 - result
        alpha = invert / 100.0
        result = result * (1.0 - alpha) + inverted * alpha

    # Retour à [0..1]
    return np.clip(result / 255.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# FX 3 : Hue / Saturation / Lightness (équivalent Photoshop "Teinte/Sat")
# ---------------------------------------------------------------------------
# Permet d'ajuster teinte/saturation/luminosité globalement OU sur une famille
# de couleurs précise (Reds, Yellows, Greens, Cyans, Blues, Magentas), avec
# transition douce entre familles via gaussienne. Mode Colorize aussi.

# Centres de teinte (en degrés sur le cercle 0..360) pour chaque famille.
# Reds est centré sur 0° avec wraparound — on gère ça spécialement.
_HUE_FAMILIES = {
    "Reds":     0.0,
    "Yellows":  60.0,
    "Greens":  120.0,
    "Cyans":   180.0,
    "Blues":   240.0,
    "Magentas": 300.0,
}
# Largeur de la fenêtre par famille en degrés (sigma de la gaussienne)
_HUE_FAMILY_SIGMA = 30.0


def _rgb_to_hsv_np(rgb: np.ndarray) -> np.ndarray:
    """RGB [0..1] (H,W,3) → HSV (H,W,3) avec H ∈ [0..360], S ∈ [0..1], V ∈ [0..1].
    Implémentation numpy pur, compatible float32."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    v = maxc
    delta = maxc - minc
    # Saturation
    s = np.where(maxc > 1e-8, delta / np.maximum(maxc, 1e-8), 0.0)
    # Teinte
    rc = np.where(delta > 1e-8, (maxc - r) / np.maximum(delta, 1e-8), 0.0)
    gc = np.where(delta > 1e-8, (maxc - g) / np.maximum(delta, 1e-8), 0.0)
    bc = np.where(delta > 1e-8, (maxc - b) / np.maximum(delta, 1e-8), 0.0)
    h = np.where(r == maxc, bc - gc,
        np.where(g == maxc, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (h / 6.0) % 1.0  # [0..1]
    h = h * 360.0        # [0..360]
    return np.stack([h, s, v], axis=-1)


def _hsv_to_rgb_np(hsv: np.ndarray) -> np.ndarray:
    """HSV (H ∈ [0..360], S/V ∈ [0..1]) → RGB [0..1]."""
    h = hsv[..., 0] / 60.0  # [0..6]
    s = hsv[..., 1]
    v = hsv[..., 2]
    i = np.floor(h).astype(np.int32) % 6
    f = h - np.floor(h)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    r = np.zeros_like(v)
    g = np.zeros_like(v)
    b = np.zeros_like(v)
    # i = 0: (v, t, p), 1: (q, v, p), 2: (p, v, t), 3: (p, q, v), 4: (t, p, v), 5: (v, p, q)
    masks = [(i == k) for k in range(6)]
    rgbs = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    for m, (rr, gg, bb) in zip(masks, rgbs):
        r = np.where(m, rr, r)
        g = np.where(m, gg, g)
        b = np.where(m, bb, b)
    return np.stack([r, g, b], axis=-1)


def _hue_distance_deg(h: np.ndarray, center: float) -> np.ndarray:
    """Distance angulaire la plus courte entre h (en degrés) et un centre.
    Toujours positive, dans [0..180]."""
    d = np.abs(h - center) % 360.0
    return np.minimum(d, 360.0 - d)


@register_fx("hsl")
def _apply_hsl(img: np.ndarray, params: dict) -> np.ndarray:
    """Ajustement Teinte/Saturation/Luminosité (TSL) façon Photoshop.

    params attendus :
      target              : "Master" | "Reds" | "Yellows" | "Greens" | "Cyans" | "Blues" | "Magentas"
      hue                 : float [-180..180] — rotation de teinte en degrés
      saturation          : float [-100..100] — -100 = N&B, +100 = saturation max
      lightness           : float [-100..100] — -100 = noir, +100 = blanc
      colorize            : bool — mode monochrome teinté (ignore target)
      colorize_hue        : float [0..360] — teinte cible (si colorize)
      colorize_saturation : float [0..100] — saturation cible (si colorize)

    Note : la désaturation préserve la luminance perceptuelle (formule
    ITU-R BT.601), conformément au comportement Photoshop. La désaturation
    "naïve" en HSV donnerait du blanc plat, ce qui n'est pas l'effet voulu.
    """
    target              = params.get("target", "Master")
    hue                 = float(params.get("hue", 0.0))
    saturation          = float(params.get("saturation", 0.0))
    lightness           = float(params.get("lightness", 0.0))
    colorize            = bool(params.get("colorize", False))
    colorize_hue        = float(params.get("colorize_hue", 0.0))
    colorize_saturation = float(params.get("colorize_saturation", 25.0))

    img = img.astype(np.float32)

    if colorize:
        # Mode colorize : on construit une image monochrome teintée à partir
        # de la luminance perceptuelle, puis on applique la teinte choisie
        # via HSV (V=luminance, H=cible, S=cible).
        lum = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
        hsv_colored = np.stack([
            np.full_like(lum, colorize_hue % 360.0),
            np.full_like(lum, colorize_saturation / 100.0),
            lum,
        ], axis=-1)
        rgb_out = _hsv_to_rgb_np(hsv_colored)

        # Lightness facultatif post-colorize
        light_factor = lightness / 100.0
        if light_factor > 0:
            rgb_out = rgb_out + (1.0 - rgb_out) * light_factor
        elif light_factor < 0:
            rgb_out = rgb_out + rgb_out * light_factor

        return np.clip(rgb_out, 0.0, 1.0)

    # ─── Mode normal : Master ou cible par famille ─────────────────────────
    hsv = _rgb_to_hsv_np(img)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    # Calcul du masque de zone à affecter
    if target == "Master":
        mask = np.ones_like(H)
    elif target in _HUE_FAMILIES:
        center = _HUE_FAMILIES[target]
        d = _hue_distance_deg(H, center)
        mask = np.exp(-(d ** 2) / (2.0 * _HUE_FAMILY_SIGMA ** 2))
        # Le masque tient compte de la saturation : un pixel quasi-gris n'a
        # pas de "teinte rouge", inutile de l'affecter
        mask = mask * S
    else:
        mask = np.ones_like(H)

    # 1. Rotation de teinte (HSV-based, simple et propre)
    H_new = (H + hue * mask) % 360.0
    hsv_hue_only = np.stack([H_new, S, V], axis=-1)
    rgb_after_hue = _hsv_to_rgb_np(hsv_hue_only)

    # 2. Saturation : on interpole entre la version désaturée (luminance perceptuelle)
    # et la version pleine couleur, en pondérant par le masque.
    # sat_factor < 0 : on tend vers la luminance (gris)
    # sat_factor > 0 : on s'éloigne de la luminance
    sat_factor = saturation / 100.0
    if abs(sat_factor) > 1e-6:
        lum = (
            0.299 * rgb_after_hue[..., 0]
            + 0.587 * rgb_after_hue[..., 1]
            + 0.114 * rgb_after_hue[..., 2]
        )
        gray_rgb = np.stack([lum, lum, lum], axis=-1)
        # Combiné mask (où on agit) × sat_factor (combien on agit)
        amount = (mask * sat_factor)[..., np.newaxis]
        if sat_factor < 0:
            # Mix vers le gris : amount va de 0 (rien) à -1 (full gray)
            rgb_after_sat = rgb_after_hue * (1.0 + amount) - gray_rgb * amount
            # Quand amount = -1 → rgb_after_sat = rgb*0 - gray*(-1) = gray ✓
            # Quand amount =  0 → rgb_after_sat = rgb*1 - gray*0    = rgb  ✓
        else:
            # Mix qui amplifie la distance au gris (saturation positive)
            rgb_after_sat = rgb_after_hue + (rgb_after_hue - gray_rgb) * amount
        rgb_after_sat = np.clip(rgb_after_sat, 0.0, 1.0)
    else:
        rgb_after_sat = rgb_after_hue

    # 3. Lightness : interpolation vers blanc (positif) ou noir (négatif),
    # toujours pondéré par le masque
    light_factor = lightness / 100.0
    if abs(light_factor) > 1e-6:
        amount = (mask * light_factor)[..., np.newaxis]
        if light_factor > 0:
            rgb_out = rgb_after_sat + (1.0 - rgb_after_sat) * amount
        else:
            rgb_out = rgb_after_sat + rgb_after_sat * amount
        rgb_out = np.clip(rgb_out, 0.0, 1.0)
    else:
        rgb_out = rgb_after_sat

    return np.clip(rgb_out, 0.0, 1.0)


# ---------------------------------------------------------------------------
# FX 4 : Color Balance (équivalent Photoshop "Balance des couleurs")
# ---------------------------------------------------------------------------
# Un seul mode actif par node (shadows / midtones / highlights). Pour
# balancer les 3 zones, chaîner 3 nodes dans le Receiver.

@register_fx("color_balance")
def _apply_color_balance(img: np.ndarray, params: dict) -> np.ndarray:
    """Balance des couleurs façon Photoshop.

    params attendus :
      adjust_type         : "shadows" | "midtones" | "highlights"
      cyan_red            : float [-100..100]  — négatif = cyan, positif = rouge
      magenta_green       : float [-100..100]  — négatif = magenta, positif = vert
      yellow_blue         : float [-100..100]  — négatif = jaune, positif = bleu
      preserve_luminosity : bool
    """
    adjust_type         = params.get("adjust_type", "midtones")
    cr                  = float(params.get("cyan_red",      0.0)) / 100.0
    mg                  = float(params.get("magenta_green", 0.0)) / 100.0
    yb                  = float(params.get("yellow_blue",   0.0)) / 100.0
    preserve_luminosity = bool(params.get("preserve_luminosity", True))

    result = img.astype(np.float32).copy()

    # Masque de zone selon la luminance
    lum = 0.299 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.114 * result[:, :, 2]
    if adjust_type == "shadows":
        # Maximum à lum=0, diminue linéairement jusqu'à 0 à lum=0.33
        mask = np.clip(1.0 - (lum / 0.33), 0.0, 1.0)
    elif adjust_type == "highlights":
        # Nul jusqu'à lum=0.67, monte linéairement jusqu'à 1 à lum=1
        mask = np.clip((lum - 0.67) / 0.33, 0.0, 1.0)
    else:  # midtones
        # Triangulaire centrée sur 0.5, pleine à 0.5, 0 aux extrêmes 0.33 et 0.67
        mask = np.clip(1.0 - np.abs(lum - 0.5) / 0.17, 0.0, 1.0)

    m = mask[..., np.newaxis]

    # Ajustements Cyan↔Red : +R, -G*0.5, -B*0.5
    result[:, :, 0] += cr * m[:, :, 0]
    result[:, :, 1] -= cr * 0.5 * m[:, :, 0]
    result[:, :, 2] -= cr * 0.5 * m[:, :, 0]

    # Magenta↔Green : +R*0.5, -G, +B*0.5 (attention, en Photoshop vert POSITIF
    # signifie qu'on ENLÈVE du magenta, donc on augmente le vert. Le signe est
    # donc inversé : mg positif = +G, -R*0.5, -B*0.5)
    result[:, :, 0] -= mg * 0.5 * m[:, :, 0]
    result[:, :, 1] += mg * m[:, :, 0]
    result[:, :, 2] -= mg * 0.5 * m[:, :, 0]

    # Yellow↔Blue : yb positif = +B, -R*0.5, -G*0.5
    result[:, :, 0] -= yb * 0.5 * m[:, :, 0]
    result[:, :, 1] -= yb * 0.5 * m[:, :, 0]
    result[:, :, 2] += yb * m[:, :, 0]

    # Préservation de la luminosité
    if preserve_luminosity:
        new_lum = 0.299 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.114 * result[:, :, 2]
        ratio = np.where(new_lum > 1e-3, lum / np.maximum(new_lum, 1e-3), 1.0)
        result = result * ratio[..., np.newaxis]

    return np.clip(result, 0.0, 1.0)


# ---------------------------------------------------------------------------
# FX 5 : Photo Filter (équivalent Photoshop "Filtre photo")
# ---------------------------------------------------------------------------
# Applique une teinte colorée uniforme par-dessus l'image, avec contrôle de
# densité et option de préservation de la luminosité. Couleur saisie en hex.

def _hex_to_rgb_norm(color_hex: str) -> tuple:
    """Convertit un hex #RRGGBB ou #RGB en tuple (r, g, b) normalisé [0..1].
    Retourne (1.0, 1.0, 1.0) si format invalide."""
    s = (color_hex or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return (1.0, 1.0, 1.0)
    try:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
        return (r, g, b)
    except ValueError:
        return (1.0, 1.0, 1.0)


@register_fx("photo_filter")
def _apply_photo_filter(img: np.ndarray, params: dict) -> np.ndarray:
    """Filtre photo façon Photoshop.

    params attendus :
      color_hex           : string "#RRGGBB" ou "#RGB" — teinte du filtre
      density             : float [0..100]   — intensité d'application (%)
      preserve_luminosity : bool              — maintient la luminance

    Algorithme : mode "multiply with tint" repondéré par densité.
    La formule Photoshop exacte n'est pas publique, mais le résultat visuel
    correspond à :  result = img * (1 + density * (tint * 2 - 1))
    rebalancé pour préserver la luminance si demandé. On utilise une
    interpolation plus douce basée sur une multiplication par la teinte.
    """
    color_hex           = params.get("color_hex", "#FFFFFF")
    density             = float(params.get("density", 25.0)) / 100.0
    preserve_luminosity = bool(params.get("preserve_luminosity", True))

    tint = np.array(_hex_to_rgb_norm(color_hex), dtype=np.float32)

    img = img.astype(np.float32)

    # Luminance d'origine (pour préservation)
    original_lum = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]

    # Le filtre photo de Photoshop applique essentiellement un mélange additif
    # entre l'image et une version teintée. La formule qui donne le résultat
    # le plus proche visuellement est :
    #   tinted = image * tint * 2    (normalisation pour que tint=gris moyen soit neutre)
    # Mais comme tint peut être n'importe quoi, on préfère un mix pondéré :
    #   result = image * (1-d) + (image * tint * 2) * d
    # qui est équivalent à  image * ((1-d) + tint * 2 * d)
    tinted = img * (tint * 2.0)
    result = img * (1.0 - density) + tinted * density

    if preserve_luminosity:
        new_lum = 0.299 * result[:, :, 0] + 0.587 * result[:, :, 1] + 0.114 * result[:, :, 2]
        ratio = np.where(new_lum > 1e-3, original_lum / np.maximum(new_lum, 1e-3), 1.0)
        result = result * ratio[..., np.newaxis]

    return np.clip(result, 0.0, 1.0)


# ---------------------------------------------------------------------------
# FX 6 : Vibrance (saturation sélective, protection tons chair)
# ---------------------------------------------------------------------------
# Équivalent du slider Vibrance de Photoshop/Lightroom : booste la saturation
# des couleurs peu saturées en priorité, protège les tons chair.
#
# Adapté de vibrance_node.py sans dépendance cv2.

@register_fx("vibrance")
def _apply_vibrance(img: np.ndarray, params: dict) -> np.ndarray:
    """Vibrance sélective + saturation globale.

    params attendus :
      vibrance           : float [-100..100] — ajustement sélectif (priorise les peu saturés)
      saturation         : float [-100..100] — ajustement global (multiplicateur)
      protect_skin_tones : bool               — réduit l'effet sur les teintes 0-30° et 330-360°
      strength           : float [0..2]       — intensité globale de la correction

    Note : la désaturation préserve la luminance perceptuelle (comme HSL),
    pas la valeur V en HSV, pour éviter les sorties blanches plates.
    """
    vibrance           = float(params.get("vibrance",           0.0))
    saturation         = float(params.get("saturation",         0.0))
    protect_skin_tones = bool(params.get("protect_skin_tones", True))
    strength           = float(params.get("strength",           1.0))

    img = img.astype(np.float32)

    # Luminance perceptuelle (cible de désaturation)
    lum = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
    gray_rgb = np.stack([lum, lum, lum], axis=-1)

    # Calcul de la saturation apparente de chaque pixel, pour piloter le
    # masque de vibrance (sélectif). On réutilise S de HSV pour ça.
    hsv = _rgb_to_hsv_np(img)
    S = hsv[..., 1]

    # Facteur total à appliquer (vibrance + saturation) pondéré par strength
    # - saturation global : multiplicateur uniforme
    # - vibrance : multiplicateur modulé par (1 - S) pour prioriser les peu saturés
    sat_delta = (saturation / 100.0) * strength
    vibe_delta = (vibrance / 100.0) * strength

    # Pour chaque pixel, le facteur effectif est (sat_delta + vibe_delta * (1 - S))
    # - positif → on s'éloigne du gris
    # - négatif → on se rapproche du gris
    factor = sat_delta + vibe_delta * (1.0 - S)
    factor = factor[..., np.newaxis]  # (H, W, 1) pour broadcasting

    # Interpolation entre image et gray_rgb :
    #   factor >= 0 : result = img + (img - gray) * factor  (s'éloigne du gris)
    #   factor <  0 : result = img + (img - gray) * factor  (se rapproche, même formule)
    # Attention au clamping : factor -1 devrait donner gray pur, factor 0 = img.
    # On clampe factor à [-1, +∞) pour éviter les inversions de couleur.
    factor = np.maximum(factor, -1.0)
    result = img + (img - gray_rgb) * factor

    # Protection des tons chair : on réduit l'effet sur les teintes 0-30° et 330-360°
    # (distance à 0° avec wrap)
    if protect_skin_tones:
        H = hsv[..., 0]
        d_to_red = _hue_distance_deg(H, 0.0)
        skin_mask = np.where(d_to_red <= 30.0, 1.0 - (d_to_red / 30.0), 0.0)
        # Atténuation : 0.5 au centre (comme code d'origine) → 50% de l'effet
        # est remplacé par l'image d'origine
        protection = 0.5 * skin_mask
        result = img * protection[..., np.newaxis] + result * (1.0 - protection[..., np.newaxis])

    return np.clip(result, 0.0, 1.0)


# ---------------------------------------------------------------------------
# FX 7 : Curves (Catmull-Rom LUT, équivalent Photoshop "Courbes")
# ---------------------------------------------------------------------------
# Courbes Catmull-Rom par canal RGB + courbe globale RGB. Format des points :
# liste de [x, y] avec x et y dans [0..1], triés par x croissant.
#
# Les helpers ci-dessous (LINEAR, DEFAULT_CURVES, apply_curve_pil,
# process_image_pil, calc_histogram_pil) sont partagés entre ce FX et les
# nodes Curves Pro (curves_pro.py importe depuis ici).

from PIL import Image as _PILImage, ImageOps as _PILImageOps

LINEAR = [[0.0, 0.0], [1.0, 1.0]]
DEFAULT_CURVES = {"rgb": LINEAR, "r": LINEAR, "g": LINEAR, "b": LINEAR}

def _curve_to_lut(pts) -> list:
    """Convertit une liste de points de courbe en LUT 256 valeurs [0..255]."""
    if not pts or len(pts) < 2:
        return list(range(256))
    # Tolérance : on accepte {"x":..,"y":..} ou [x, y]
    if isinstance(pts[0], dict):
        pts = [[p["x"], p["y"]] for p in pts]
    pts = sorted(pts, key=lambda p: p[0])
    lut = [0] * 256

    if len(pts) == 2:
        x0, y0 = pts[0]
        x1, y1 = pts[1]
        span = (x1 - x0) or 1.0
        for i in range(256):
            v = i / 255.0
            out = y0 if v < x0 else (y1 if v > x1 else y0 + (v - x0) / span * (y1 - y0))
            lut[i] = int(np.clip(out * 255, 0, 255))
    else:
        # Catmull-Rom
        for i in range(256):
            v = i / 255.0
            out = 0.0
            found = False
            for j in range(len(pts) - 1):
                p1, p2 = pts[j], pts[j + 1]
                if p1[0] <= v <= p2[0]:
                    p0 = pts[max(0, j - 1)]
                    p3 = pts[min(len(pts) - 1, j + 2)]
                    t = (v - p1[0]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0
                    t2, t3 = t * t, t * t * t
                    out = 0.5 * (
                        (2 * p1[1])
                        + (-p0[1] + p2[1]) * t
                        + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                        + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                    )
                    found = True
                    break
            if not found:
                out = pts[0][1] if v <= pts[0][0] else pts[-1][1]
            lut[i] = int(np.clip(out * 255, 0, 255))

    return lut


def apply_curve_pil(pil_img, pts):
    """Applique une courbe à une image PIL (mode L ou RGB)."""
    try:
        lut = _curve_to_lut(pts)
        if pil_img.mode == "RGB":
            lut = lut * 3
        return pil_img.point(lut)
    except Exception as e:
        print(f"[curves] apply_curve_pil error: {e}")
        return pil_img


def process_image_pil(pil_rgb, curves: dict):
    """Applique courbes R/G/B puis RGB global sur une image PIL RGB."""
    r, g, b = pil_rgb.split()
    merged = _PILImage.merge("RGB", (
        apply_curve_pil(r, curves.get("r",   LINEAR)),
        apply_curve_pil(g, curves.get("g",   LINEAR)),
        apply_curve_pil(b, curves.get("b",   LINEAR)),
    ))
    return apply_curve_pil(merged, curves.get("rgb", LINEAR))


def calc_histogram_pil(pil_img, channel: str) -> list:
    """Histogramme d'un canal sous forme de liste 256 valeurs normalisées [0..1]."""
    hist = []
    if channel == "RGB":
        hist = _PILImageOps.grayscale(pil_img).histogram()
    elif channel in ("Red", "Green", "Blue"):
        idx = {"Red": 0, "Green": 1, "Blue": 2}[channel]
        hist = pil_img.split()[idx].histogram()
    if hist:
        m = max(hist)
        if m:
            hist = [h / m for h in hist]
    return hist


@register_fx("curves")
def _apply_curves(img: np.ndarray, params: dict) -> np.ndarray:
    """Applique une chaîne de courbes R/G/B + RGB global.

    params attendus :
      all_curves_json : str JSON du dict {rgb, r, g, b}   (format natif Curves Pro)
      OU directement les clés rgb/r/g/b dans params       (fallback)
    """
    import json as _json

    # Support des deux formats : soit 'all_curves_json' string, soit dict direct
    curves = None
    if "all_curves_json" in params:
        try:
            curves = _json.loads(params["all_curves_json"])
        except Exception:
            curves = None
    if curves is None:
        # Fallback : les clés rgb/r/g/b directement dans params
        if any(k in params for k in ("rgb", "r", "g", "b")):
            curves = {k: params.get(k, LINEAR) for k in ("rgb", "r", "g", "b")}
        else:
            curves = DEFAULT_CURVES

    # Conversion vers PIL pour réutiliser les helpers existants
    pil_img = _PILImage.fromarray((img * 255.0).clip(0, 255).astype(np.uint8))
    pil_result = process_image_pil(pil_img, curves)
    result = np.array(pil_result, dtype=np.float32) / 255.0
    return np.clip(result, 0.0, 1.0)



# ---------------------------------------------------------------------------
# FX 8 : Matrix 3x3 (transformation RGB complète)
# ---------------------------------------------------------------------------
# Transformation RGB par matrice complète. Les looks prédéfinis sont maintenant
# de simples presets JSON chargés par le système unifié fx_setup/matrix_3x3/.

def _luma_709(img: np.ndarray) -> np.ndarray:
    """Luminance Rec.709 perceptuelle sur RGB [0..1]."""
    return (
        0.2126 * img[..., 0]
        + 0.7152 * img[..., 1]
        + 0.0722 * img[..., 2]
    )


def _preserve_luma_np(original: np.ndarray, transformed: np.ndarray) -> np.ndarray:
    """Réajuste transformed pour conserver la luminance de original."""
    old_luma = _luma_709(original)
    new_luma = _luma_709(transformed)
    ratio = np.where(new_luma > 1e-6, old_luma / np.maximum(new_luma, 1e-6), 1.0)
    return transformed * ratio[..., np.newaxis]


@register_fx("matrix_3x3")
def _apply_matrix_3x3(img: np.ndarray, params: dict) -> np.ndarray:
    """Applique une matrice RGB 3x3 sur une image numpy RGB [0..1]."""
    original = img.astype(np.float32)
    result = original.copy()

    matrix_values = [
        [float(params.get("m00", 1.0)), float(params.get("m01", 0.0)), float(params.get("m02", 0.0))],
        [float(params.get("m10", 0.0)), float(params.get("m11", 1.0)), float(params.get("m12", 0.0))],
        [float(params.get("m20", 0.0)), float(params.get("m21", 0.0)), float(params.get("m22", 1.0))],
    ]
    offset_values = [
        float(params.get("offset_r", 0.0)),
        float(params.get("offset_g", 0.0)),
        float(params.get("offset_b", 0.0)),
    ]

    matrix = np.array(matrix_values, dtype=np.float32)
    offset = np.array(offset_values, dtype=np.float32).reshape(1, 1, 3)

    # RGB row-vector × matrice transposée.
    result = result @ matrix.T + offset

    if bool(params.get("preserve_luminosity", False)):
        result = _preserve_luma_np(original, result)

    strength = float(params.get("strength", 1.0))
    result = original + (result - original) * strength

    if bool(params.get("clamp_output", True)):
        result = np.clip(result, 0.0, 1.0)

    return result.astype(np.float32)


# ---------------------------------------------------------------------------
# FX 9 : DCTL Tone Mapper (tone mapping filmique)
# ---------------------------------------------------------------------------
# Tone mapper créatif/technique inspiré des DCTLs :
# exposition en stops, contraste avec pivot, shoulder, toe, saturation finale.

def _tone_map_reinhard_np(x: np.ndarray, rolloff: float) -> np.ndarray:
    k = max(0.001, 1.0 + rolloff)
    return x / np.maximum(x + k, 1e-6)


def _tone_map_aces_approx_np(x: np.ndarray) -> np.ndarray:
    # Approximation ACES fitted courante.
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    return (x * (a * x + b)) / np.maximum(x * (c * x + d) + e, 1e-6)


def _tone_map_filmic_soft_np(x: np.ndarray, rolloff: float) -> np.ndarray:
    shoulder = 1.0 + rolloff * 1.75
    return 1.0 - np.exp(-x / max(0.001, shoulder))


def _tone_map_filmic_strong_np(x: np.ndarray, rolloff: float) -> np.ndarray:
    shoulder = 0.85 + rolloff * 1.35
    y = 1.0 - np.exp(-x / max(0.001, shoulder))
    return np.power(np.clip(y, 0.0, None), 0.92)


def _tone_map_cineon_ish_np(x: np.ndarray, rolloff: float) -> np.ndarray:
    k = 4.0 + rolloff * 4.0
    return np.log1p(x * k) / np.log1p(k)


@register_fx("dctl_tone_mapper")
def _apply_dctl_tone_mapper(img: np.ndarray, params: dict) -> np.ndarray:
    """Tone mapper filmique inspiré DCTL, en numpy RGB [0..1]."""
    original = img.astype(np.float32)
    result = np.clip(original.copy(), 0.0, None)

    mode = params.get("mode", "Filmic Soft")

    exposure = float(params.get("exposure", 0.0))
    contrast = float(params.get("contrast", 1.0))
    pivot = max(0.001, float(params.get("pivot", 0.18)))

    highlight_rolloff = float(params.get("highlight_rolloff", 0.65))
    shadow_lift = float(params.get("shadow_lift", 0.0))
    black_floor = float(params.get("black_floor", 0.0))

    saturation = float(params.get("saturation", 1.0))
    preserve_luminosity = bool(params.get("preserve_luminosity", False))
    strength = float(params.get("strength", 1.0))
    clamp_output = bool(params.get("clamp_output", True))

    # Exposition en stops.
    result = result * (2.0 ** exposure)

    # Contraste avec pivot, en domaine positif.
    if abs(contrast - 1.0) > 1e-6:
        result = pivot * np.power(np.clip(result / pivot, 0.0, None), contrast)

    # Shadow lift / crush doux.
    if abs(shadow_lift) > 1e-6:
        shadow_mask = np.power(np.clip(1.0 - result, 0.0, 1.0), 2.0)
        result = result + shadow_mask * shadow_lift * 0.25
        result = np.clip(result, 0.0, None)

    # Tone mapping principal.
    if mode == "ACES Approx":
        mapped = _tone_map_aces_approx_np(result)
    elif mode == "Reinhard":
        mapped = _tone_map_reinhard_np(result, highlight_rolloff)
    elif mode == "Cineon-ish":
        mapped = _tone_map_cineon_ish_np(result, highlight_rolloff)
    elif mode == "Filmic Strong":
        mapped = _tone_map_filmic_strong_np(result, highlight_rolloff)
    else:
        mapped = _tone_map_filmic_soft_np(result, highlight_rolloff)

    # Black floor optionnel.
    if black_floor > 0.0:
        mapped = mapped * (1.0 - black_floor) + black_floor

    # Saturation finale.
    if abs(saturation - 1.0) > 1e-6:
        luma = _luma_709(mapped)
        gray = np.stack([luma, luma, luma], axis=-1)
        sat_mapped = gray + (mapped - gray) * saturation

        if preserve_luminosity:
            sat_mapped = _preserve_luma_np(mapped, sat_mapped)

        mapped = sat_mapped

    # Strength global.
    result = original + (mapped - original) * strength

    if clamp_output:
        result = np.clip(result, 0.0, 1.0)

    return result.astype(np.float32)


# --- END OF FILE color_fx_common.py ---
