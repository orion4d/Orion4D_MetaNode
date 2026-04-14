# --- START OF FILE Packers.py ---

class PyCodeMax_ListPacker:
    """
    Un nœud dynamique (infini). 
    Branchez un élément, un nouveau port apparaîtra automatiquement !
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {}, 
            "optional": {
                "item_1": ("*",)
            }
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("list_out",)
    FUNCTION = "pack_items"
    CATEGORY = "Orion4D_MetaNode/Utils"

    def pack_items(self, **kwargs):
        packed_list = []
        items = [k for k in kwargs.keys() if k.startswith("item_")]
        items.sort(key=lambda x: int(x.split('_')[1]))

        for k in items:
            val = kwargs.get(k)
            if val is not None:
                packed_list.append(val)
                
        return (packed_list,)


class PyCodeMax_DictPacker:
    """
    Génère un Dictionnaire avec des clés nommées.
    Dynamique et infini ! Branchez une valeur, un nouveau champ apparaîtra.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "key_1": ("STRING", {"default": "param1"}), 
                "val_1": ("*",),
            }
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("dict_out",)
    FUNCTION = "pack_dict"
    CATEGORY = "Orion4D_MetaNode/Utils"

    def pack_dict(self, **kwargs):
        packed_dict = {}
        # Récupère tous les ports "val_X" reçus
        val_keys = [k for k in kwargs.keys() if k.startswith("val_")]
        # Tri par numéro pour s'assurer que l'ordre est respecté
        val_keys.sort(key=lambda x: int(x.split('_')[1]))

        for v_key in val_keys:
            idx = v_key.split('_')[1] # Extrait le numéro
            val = kwargs.get(v_key)
            k_key = f"key_{idx}"
            key_name = kwargs.get(k_key, f"param{idx}")
            
            if key_name != "" and val is not None:
                packed_dict[key_name] = val
                
        return (packed_dict,)


class PyCodeMax_ListUnpacker:
    """
    Décompresse une liste (list_in) en plusieurs éléments individuels.
    Optimisé à 32 sorties pour préserver les performances de ComfyUI.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_in": ("*",) 
            }
        }

    RETURN_TYPES = tuple(["*"] * 32)
    RETURN_NAMES = tuple([f"item_{i+1}" for i in range(32)])
    FUNCTION = "unpack"
    CATEGORY = "Orion4D_MetaNode/Utils"

    def unpack(self, list_in):
        if list_in is None:
            list_in = []
        elif not isinstance(list_in, list):
            list_in = [list_in]

        result = []
        for i in range(32):
            if i < len(list_in):
                result.append(list_in[i])
            else:
                result.append(None) 

        return tuple(result)

class PyCodeMax_Logger:
    """
    Affiche le contenu et le type de n'importe quelle donnée dans la console ComfyUI.
    Indispensable pour le débogage.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "any_input": ("*",),
                "prefix": ("STRING", {"default": "DEBUG"}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "log_data"
    CATEGORY = "Orion4D_MetaNode/Utils"
    OUTPUT_NODE = True 

    def log_data(self, any_input, prefix):
        data_type = type(any_input).__name__
        
        if isinstance(any_input, list):
            info = f"Liste de {len(any_input)} éléments"
        elif hasattr(any_input, "shape"): 
            info = f"Shape Tenseur: {any_input.shape}"
        else:
            info = str(any_input)[:500] 

        print(f"\n[PyCodeMax Logger | {prefix}] Type: {data_type} | Info: {info}")
        return ()

# ---------------------------------------------------------------------------
# Enregistrement des Nœuds
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "PyCodeMax_ListPacker": PyCodeMax_ListPacker,
    "PyCodeMax_DictPacker": PyCodeMax_DictPacker,
    "PyCodeMax_ListUnpacker": PyCodeMax_ListUnpacker,
    "PyCodeMax_Logger": PyCodeMax_Logger
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PyCodeMax_ListPacker": "📦 List Packer (Infinite)",
    "PyCodeMax_DictPacker": "📦 Dict Packer (Infinite)", # <-- Mise à jour du nom !
    "PyCodeMax_ListUnpacker": "📤 List Unpacker (Dynamic)",
    "PyCodeMax_Logger": "🖨️ Logger (Debug Console)"
}

# --- END OF FILE Packers.py ---