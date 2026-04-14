# Orion4D_MetaNode
#
# Point d'entrée du pack. Charge dynamiquement tous les modules listés
# dans _NODE_MODULES et agrège leurs NODE_CLASS_MAPPINGS /
# NODE_DISPLAY_NAME_MAPPINGS dans les mappings globaux attendus par ComfyUI.
#
# Ajouter un nouveau node = ajouter une ligne dans _NODE_MODULES.
# Chaque module doit définir NODE_CLASS_MAPPINGS et NODE_DISPLAY_NAME_MAPPINGS
# à son niveau supérieur (c'est déjà le cas partout dans ce pack).

import importlib
import traceback

# ---------------------------------------------------------------------------
# Modules d'infrastructure (pas de nodes, juste des routes API ou des helpers
# partagés). Importés explicitement pour que leurs effets de bord (routes
# aiohttp, création de dossiers, etc.) soient déclenchés au démarrage.
# ---------------------------------------------------------------------------
try:
    from . import color_fx_presets  # noqa: F401  (système de presets pour les Color FX)
except Exception as _e:
    print(f"\033[31m[Orion4d-coder]\033[0m Échec import infra 'color_fx_presets': {_e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# Liste des modules à charger, dans l'ordre où ils apparaissent.
# L'ordre n'a pas d'importance fonctionnelle, mais on garde un regroupement
# thématique pour la lisibilité.
# ---------------------------------------------------------------------------
_NODE_MODULES = [
    # Moteur principal
    "PyCodeMax",

    # Conteneurs de données (packers, unpackers, logger)
    "Packers",

    # Widgets UI simples
    "boolean_switch",
    "text_input",
    "number_input",
    "parametric_slider",
    "Color_Picker",

    # Sélecteurs et navigateurs de fichiers
    "Master_ComboBox",
    "Model_Selector",
    "Folder_file_max",
    "load_text_file",
    "List_selector_max",

    # Routage et flux d'exécution
    "dynamic_road",
    "text_road",
    "dynamic_splitter",
    "execution_gate",
    "variable_bus",

    # Traitement d'image
    "lut_nodes",
    "image_comparer",
    "image_comparer_v2",  # version beta optimisée Nodes 2.0
    # Chaîne Color Pro (émetteurs + récepteur). color_fx_common est importé
    # automatiquement par les nodes ci-dessous, pas besoin de le lister ici.
    "color_pro_receiver",
    "color_fx_channel_mixer",
    "color_fx_css_filters",
    "color_fx_hsl",
    "color_fx_color_balance",
    "color_fx_photo_filter",
    "color_fx_vibrance",
    "curves_pro",  # v6 : unifié avec la chaîne Color Pro

    # Sauvegarde
    "super_saver",
]

# ---------------------------------------------------------------------------
# Chargement dynamique
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {}
NODE_DISPLAY_NAME_MAPPINGS: dict = {}

_loaded = 0
_failed = []

for _mod_name in _NODE_MODULES:
    try:
        _mod = importlib.import_module(f".{_mod_name}", __name__)
    except Exception as _e:
        _failed.append((_mod_name, _e))
        print(f"\033[31m[Orion4d-coder]\033[0m Échec import '{_mod_name}': {_e}")
        traceback.print_exc()
        continue

    _classes = getattr(_mod, "NODE_CLASS_MAPPINGS", None)
    _names = getattr(_mod, "NODE_DISPLAY_NAME_MAPPINGS", None)

    if not isinstance(_classes, dict):
        print(f"\033[33m[Orion4d-coder]\033[0m '{_mod_name}' n'expose pas NODE_CLASS_MAPPINGS")
        continue

    # Détection de collisions avant fusion
    _collisions = set(NODE_CLASS_MAPPINGS.keys()) & set(_classes.keys())
    if _collisions:
        print(f"\033[33m[Orion4d-coder]\033[0m Collision d'IDs dans '{_mod_name}': {_collisions}")

    NODE_CLASS_MAPPINGS.update(_classes)
    if isinstance(_names, dict):
        NODE_DISPLAY_NAME_MAPPINGS.update(_names)
    _loaded += 1

# ---------------------------------------------------------------------------
# Exports et log final
# ---------------------------------------------------------------------------
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

_count = len(NODE_CLASS_MAPPINGS)
_module_word = "module" if _loaded == 1 else "modules"
_node_word = "node" if _count == 1 else "nodes"
print(
    f"\n\033[34m[Orion4d-coder]\033[0m "
    f"{_loaded}/{len(_NODE_MODULES)} {_module_word} chargé(s) — "
    f"{_count} {_node_word} disponible(s)."
)
if _failed:
    print(f"\033[31m[Orion4d-coder]\033[0m {len(_failed)} module(s) en échec: "
          + ", ".join(name for name, _ in _failed))
