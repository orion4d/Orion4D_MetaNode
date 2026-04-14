import os
import torch
import numpy as np
from PIL import Image

# On importe le registre global des nœuds de ComfyUI
from nodes import NODE_CLASS_MAPPINGS

# 1. RÉCUPÉRATION DU NŒUD ORIGINAL
RMBG_Node_Class = NODE_CLASS_MAPPINGS.get("BiRefNetRMBG")
if not RMBG_Node_Class:
    raise RuntimeError("Le nœud 'BiRefNet (RMBG)' n'a pas été trouvé. Assurez-vous qu'il est bien installé.")

# On instancie le nœud
rmbg_node = RMBG_Node_Class()

# 2. VÉRIFICATION DES ENTRÉES
pil_images = IN.get('img_in_1')
if not pil_images:
    raise ValueError("Veuillez connecter une image au port 'img_in_1'.")

params = IN.get('custom_in_1')
if not params or len(params) < 6:
    raise ValueError("Le 'List Packer' branché sur 'custom_in_1' doit contenir les 6 paramètres.")

# 3. DÉCORTICAGE DU LIST PACKER
model_path     = str(params[0])            
mask_blur      = int(params[1])            
mask_offset    = int(params[2])            
invert_output  = bool(params[3])           
background     = str(params[4])            
bg_color       = str(params[5]).strip()    

if not bg_color.startswith('#'):
    bg_color = f"#{bg_color}"

model_key = os.path.basename(model_path).replace(".safetensors", "").replace(".pth", "")

print(f"🔧 Launch of BiRefNet with the model : {model_key}")

# 4. PRÉPARATION DE L'IMAGE POUR LE NŒUD COMFYUI
tensor_images = []
for img in pil_images:
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_np = np.array(img).astype(np.float32) / 255.0
    tensor_images.append(torch.from_numpy(img_np))

input_tensor = torch.stack(tensor_images)

# 5. EXÉCUTION DU DÉTOURAGE
out_images, out_masks, out_mask_images = rmbg_node.process_image(
    image=input_tensor,
    model=model_key,
    mask_blur=mask_blur,
    mask_offset=mask_offset,
    invert_output=invert_output,
    refine_foreground=True, 
    background=background,
    background_color=bg_color
)

# 6. RETOUR VERS PYCODEMAX
# -> img_out_1 (L'image détourée)
result_pil = []
for i in range(out_images.shape[0]):
    t = out_images[i]
    arr = np.clip(255.0 * t.cpu().numpy(), 0, 255).astype(np.uint8)
    mode = 'RGBA' if arr.shape[-1] == 4 else 'RGB'
    result_pil.append(Image.fromarray(arr, mode=mode))

# -> img_out_2 (Le Masque en tant qu'Image RGB)
result_mask_pil = []
for i in range(out_mask_images.shape[0]):
    t_mask = out_mask_images[i]
    # Conversion du Tensor RGB (0.0 à 1.0) en pixels classiques (0 à 255)
    arr_mask = np.clip(255.0 * t_mask.cpu().numpy(), 0, 255).astype(np.uint8)
    result_mask_pil.append(Image.fromarray(arr_mask, mode='RGB'))

# Affectation des sorties
OUT['img_out_1'] = result_pil
OUT['img_out_2'] = result_mask_pil  # <-- Ton masque visuel en noir et blanc !
OUT['mask_out']  = out_masks        # <-- Le masque tensor natif (au cas où tu as besoin de l'utiliser avec d'autres nœuds)
OUT['txt_out_1'] = f"Success! Clipping completed with {model_key}."