# 🚀 Orion4D_Metanode — Custom Nodes ComfyUI

<div align="center">

![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom_Nodes-blue?style=for-the-badge&logo=python&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Nodes](https://img.shields.io/badge/Nodes-29+-orange?style=for-the-badge)

**Ce projet est l'aboutissement de mes contributions custom nodes pour ComfyUI, reprenez le contrôle total de l'interface avec ma suite de nœuds avancés, articulée autour du moteur "PyCode Max" qui permet d'exécuter du Python directement dans les workflows. Routing dynamique, bus de variables, UI enrichie, gestion de fichiers, traitement d'image…\
Tout est réuni pour transformer ComfyUI en véritable environnement programmable. A noter, pratiquement tous les nodes sont compatibles Nodes V2**

</div>

## 🚧 Status

**Version : 1** (14/04/2026)

---

## 🔧 Nodes

### ⚙️ PyCode Max
> Véritable "cerveau" de cette suite, exécutez du code Python directement dans votre workflow ComfyUI.
> 
<img width="606" height="1110" alt="image" src="https://github.com/user-attachments/assets/702f3a5a-34e5-43b8-8993-c2e97a51f9af" />

- **Deux modes** : saisie directe (`text_input`) ou fichier externe (`file`)
- **Entrées universelles** : texte, entiers, floats, images, masks, latents, conditioning, model, clip, vae, audio, vidéo, et types personnalisés
- **STATE persistant** par nœud entre les exécutions (réinitialisable)
- **Timeout configurable** (5–600 sec) contre les boucles infinies
- **Mode sécurisé** : l'exécution en mode texte est verrouillée par défaut (nécessite `"developer_mode": true` dans `config.json`)
- **Documentation automatique** : les commentaires en tête d'un script `.py` sont affichés dans la console
- **Console** intégrée avec durée d'exécution et logs structurés

---

### 📂 Folder File Max
> Un explorateur de fichiers visuel complet, directement dans un nœud ComfyUI.
> 
<img width="1048" height="1089" alt="image" src="https://github.com/user-attachments/assets/d7393eef-8508-40c7-af11-7bfac40e924a" />
<img width="1068" height="1124" alt="image" src="https://github.com/user-attachments/assets/12f7457f-fde7-449a-ab77-d68e4c15fd8f" />

- **Vue grille ou liste** avec miniatures générées à la volée
- **Filtrage** par extension, regex (include/exclude), tri par nom/date/taille
- **Navigation** : remonter dans les dossiers, double-clic pour ouvrir
- **Lightbox** intégrée pour prévisualiser images, vidéos et audio
- **Bouton "Explorer"** pour ouvrir le dossier dans l'explorateur système (Windows/macOS/Linux)
- **Modes de seed** : fixed, aléatoire, incrément…
- Retourne : `file_path`, `filename`, `dir_used`, `files_json`, `file_info`, `IMAGE`

---

### 📄 Load Text File
> Charge n'importe quel fichier texte et expose son contenu dans un widget éditable.
> 
<img width="949" height="738" alt="image" src="https://github.com/user-attachments/assets/c60e0b47-92ab-4098-9f94-15f382859d25" />

- **Glisser-déposer** ou sélection de fichier depuis l'interface
- Le contenu apparaît dans un widget `STRING` multiline **directement éditable** dans le nœud
- Formats supportés : `.txt`, `.json`, `.csv`, `.py`, `.js`, `.md`, `.yaml`, `.toml`, `.xml`, `.html`, `.sh`, `.bat`, `.ini`, `.cfg`, `.env`, `.log`
- Détection automatique de l'encodage (UTF-8, Latin-1, CP1252…)
- Retourne : `text` (STRING)

---

### 💾 Super Saver
> Sauvegarde avancée d'images et de textes avec gestion fine des noms de fichiers et des métadonnées.
> 
<img width="875" height="1103" alt="image" src="https://github.com/user-attachments/assets/fcfe12f8-0a63-4cdb-ae92-79e8bd472f60" />

- **Image** : PNG, JPEG, WEBP, TIFF — qualité configurable par format
- **Alpha dynamique** : ports `alpha_N` supplémentaires pour sauvegarder des calques (géré par le JS)
- **Texte** : sauvegarde simultanée d'un fichier `.txt` (ou autre extension) accompagnant l'image
- **Métadonnées** : injection de JSON ou texte libre dans le chunk `iTXt` du PNG (UTF-8 natif)
- **Nommage** : préfixe, timestamp (Date_Time / HHMMSS / Unix_Epoch), compteur auto, sous-dossiers
- **Strip Workflow** : supprime les données de workflow du PNG avant sauvegarde
- Retourne : `image_path`, `text_path` (STRING)

---

### 🔀 Dynamic Road
> Routeur d'entrées dynamique — connectez N entrées universelles et choisissez laquelle transmettre.
> 
<img width="1531" height="992" alt="image" src="https://github.com/user-attachments/assets/9e7731d0-4256-48e4-beb5-256a68988a89" />

- Les ports d'entrée `*` apparaissent automatiquement à la connexion
- Chaque entrée dispose d'un **champ mémo** (label personnalisable) et d'un **toggle radio**
- Sélection par interface visuelle ou par index Python
- Retourne : la valeur sélectionnée, sa représentation texte, et un log détaillé

---

### 📝 Text Road
> Concaténateur de textes multi-entrées avec contrôle fin par entrée.

- Entrées `STRING` dynamiques (ports apparaissent à la connexion)
- Chaque entrée dispose d'un **mémo**, d'un **toggle actif/inactif**, d'un **préfixe** et d'un **suffixe**
- **Séparateur configurable** (supporte `\n`, `\t`, ou toute chaîne)
- Retourne : `text_out` (STRING)

---

### 🔀 Dynamic Splitter
> Diffuse une entrée unique vers N sorties dynamiques, avec activation sélective par sortie.
> 
<img width="1348" height="1016" alt="image" src="https://github.com/user-attachments/assets/bec16c4c-688c-43cc-99da-87241e7df216" />

- **1 entrée → N sorties** : la même donnée est broadcastée sur toutes les sorties actives
- Les sorties apparaissent dynamiquement (gérées par le JS)
- Les sorties **désactivées** émettent un `ExecutionBlocker` — le flux en aval est stoppé proprement sans crash
- Chaque sortie dispose d'un **label** personnalisable et d'un **toggle actif/inactif**
- Retourne : jusqu'à 32 sorties `out_N` + un `log` (STRING)

---

### 🚦 Execution Gate
> Laisse passer ou bloque proprement un flux selon un booléen.
> 
<img width="469" height="284" alt="image" src="https://github.com/user-attachments/assets/907f1395-8fee-4318-af3c-8a172823bbae" />

- **Open ✅** → la donnée passe telle quelle
- **Blocked 🚫** → émet un `ExecutionBlocker` : tout le graphe en aval est stoppé sans erreur
- Compatible avec la sortie `boolean` du **Boolean Switch**
- Accepte n'importe quel type en entrée (`*`)
- Retourne : `output` (`*`)

---

### 🚌 Variable Bus (Set) + Variable Bus (Get)
> Partagez n'importe quelle donnée entre des nœuds distants sans câble direct.

<img width="546" height="565" alt="image" src="https://github.com/user-attachments/assets/22112a4f-283f-434f-9c46-52a01a6330bc" />

**Bus Set :**
- Stocke la donnée dans un bus global (dictionnaire Python en mémoire) sous un nom de variable
- Sortie `passthrough` : retourne la donnée originale pour continuer le flux
- Sortie `sync` (INT=0) : à brancher sur le port `dependency` du BusGet pour garantir l'ordre d'exécution
- `OUTPUT_NODE = True` : s'exécute même sans consommateur en aval

**Bus Get :**
- Récupère la donnée depuis le bus global par son nom
- Port optionnel `dependency` : branchez-y le `sync` du BusSet correspondant
- Si la variable est introuvable → `ExecutionBlocker` propre (pas de crash)

> 💡 Idéal pour partager un modèle, une image ou un latent entre branches sans rallonger les câbles.

---

### 📋 List Selector Max
> Un "must have" pour la génération de prompts : Sélecteur de lignes multi-groupes depuis des fichiers `.txt` / `.csv`, avec seed indépendant par groupe.
> Astuce : le résultat peut être enrichi via PycodeMax avec un modèle LLM, le tout en automatique !
> 
<img width="683" height="1163" alt="image" src="https://github.com/user-attachments/assets/892fa828-94b7-43cf-9c90-dc6c039518bb" />
<img width="1224" height="979" alt="image" src="https://github.com/user-attachments/assets/f98734cf-22ec-46de-94eb-0924a0735df8" />

- **Multi-groupes** : chaque groupe pointe vers un fichier différent, avec son propre seed et séparateur
- **Modes de sélection par groupe** : `select` (index manuel), `randomize`, `increment`, `decrement`
- **Édition inline** : modifiez la ligne sélectionnée directement dans le nœud avant de l'envoyer
- **Override manuel** : saisissez un texte libre dans le champ preview pour court-circuiter la sélection
- **Tokens de chemin** : `{COMFY}` et `{CUSTOM}` pour des chemins portables entre machines
- **Sécurité** : l'accès est restreint à la racine ComfyUI et au dossier personnalisé défini
- Retourne : `concatenated` (STRING), `lines_json` (STRING), `total_count` (INT)

---

### 🎚️ Parametric Slider

> Slider configurable dynamiquement depuis des fichiers JSON.
> <img width="849" height="554" alt="image" src="https://github.com/user-attachments/assets/0d187e92-aec2-4087-962d-1e34da1a1658" />
<img width="925" height="779" alt="image" src="https://github.com/user-attachments/assets/a788dfe6-e709-41ab-b5fa-5f4d29a5601b" />

- Chargez vos **presets de plage** depuis le dossier `json_slider/`
- Supporte `min`, `max`, `step`, `default`, `label`, `precision`, `unit`
- **Modes après génération** : `fixed`, `increment`, `decrement`, `randomize`
- Retourne : `float_val`, `int_val`, `text_val` (avec unité), `label`, `min`, `max`, `step`, `log`

**Exemple de preset (`json_slider/px_1_to_8192.json`) :**
```json
{ "min": 1, "max": 8192, "step": 64, "default": 512, "label": "Résolution", "precision": 0, "unit": "px" }
```

---

### 🔽 Master Combo Box
> Menu déroulant double lié à des fichiers JSON dans le dossier `dropdowns/`.
> 
<img width="1084" height="829" alt="image" src="https://github.com/user-attachments/assets/0cfbc386-411f-47b3-98b2-50b88a36b247" />

- **Menu 1** : choisit le fichier JSON (catégorie)
- **Menu 2** : affiche le contenu du fichier sélectionné
- Bouton **Actualiser** pour recharger sans redémarrer ComfyUI
- Retourne : `selected_text` (STRING)

---

### 📂 Model Selector
> Naviguez dans les sous-dossiers de `models/` avec un sélecteur à deux niveaux.
> 
<img width="568" height="689" alt="image" src="https://github.com/user-attachments/assets/e110e697-61ef-4e63-a238-8503b7d368b1" />

- **Menu 1** : catégorie (`checkpoints`, `loras`, `upscale_models`…)
- **Menu 2** : fichier dans cette catégorie
- Filtre automatique sur les extensions `.safetensors`, `.gguf`, `.pth`, `.bin`
- Retourne : `absolute_path`, `relative_path`, `filename_only`, `any_path`, `any_filename`

---

### 🎨 Color Picker
> Ouvre la palette de couleur native de l'OS pour sélectionner une couleur.
> 
<img width="1123" height="1088" alt="image" src="https://github.com/user-attachments/assets/5d6ca7aa-b86c-4bdf-b6e3-465b9cb1e81c" />

- Aperçu de la couleur dessiné directement sur le nœud
- Retourne : `hex_value` (ex: `#F54927`), `rgb_string` (ex: `245, 73, 39`), canaux `R`, `G`, `B`

---

### 📈 Curves Pro + 🖼️ Curves Pro Image
> Éditeur de courbes RVB style Photoshop, avec aperçu live.
> 
<img width="1847" height="943" alt="image" src="https://github.com/user-attachments/assets/3a5fe5a9-a6ea-412c-9d45-2f0f70936f63" />
<img width="1230" height="1109" alt="image" src="https://github.com/user-attachments/assets/de0a5aa9-c390-42f9-abf4-479f379ab375" />
<img width="1694" height="1032" alt="image" src="https://github.com/user-attachments/assets/e420a817-bf39-4763-a740-5dd17f9329f4" />

**Curves Pro (éditeur) :**
- Canvas interactif pour les canaux **RGB**, **R**, **G**, **B**
- **Histogramme live** calculé depuis l'image connectée
- **Magnétisme de grille** (3 niveaux de densité)
- **Système de présets** : sauvegarde/chargement depuis `json_curves/`
- Retourne : `curves_json` (STRING)

**Curves Pro Image (récepteur) :**
- Charge une image (style Load Image natif)
- Reçoit le `curves_json` et applique les courbes en temps réel
- **Aperçu live** renvoyé au nœud éditeur via WebSocket
- Retourne : `IMAGE`, `MASK`, `log`

---

### 🎨 LUT Generator + 🎬 LUT Manager
> Création et application de LUTs 3D `.cube` directement dans ComfyUI.
> 
<img width="1873" height="1137" alt="image" src="https://github.com/user-attachments/assets/3f179096-d6c1-4697-8b90-abfc93af72c9" />
<img width="818" height="818" alt="image" src="https://github.com/user-attachments/assets/916de328-0781-44c7-9e41-fbf8cdd8517b" />
<img width="1742" height="946" alt="image" src="https://github.com/user-attachments/assets/4940b4e0-3db4-4a56-b09d-ca0f5dd9985b" />
<img width="1717" height="943" alt="image" src="https://github.com/user-attachments/assets/87a985c1-7ed0-4894-beca-766ee5066f28" />


**LUT Generator :**
- Génère une LUT 3D à partir de deux images (avant/après) — idéal pour **capturer le look d'un grading** existant
- Paramètres fins : taille de LUT (9–65), nombre d'échantillons, méthode d'interpolation (`linear`, `nearest`, `cubic`), lissage gaussien, ancrage identity
- **Mode sans sauvegarde** (`save_lut = False`) : calcule la LUT en mémoire pour tester sans écrire sur disque
- Formats d'export : `.cube`, `.3dl`, `.csp`
- Images de calibration stockées dans `lut_files/images_calibration/` pour faciliter les comparaisons
- Retourne : `preview_image`, `tested_image`, `lut_path`

**LUT Manager :**
- Applique n'importe quelle LUT `.cube` à une image, via chemin direct ou sélection dans `lut_files/`
- Contrôle de l'**intensité** (0–2) et de l'**opacité** (0–1) indépendamment
- Choix des ordres data/table (`BGR`/`RGB`) pour compatibilité maximale avec les LUTs du commerce
- **Cache en mémoire** : la LUT n'est rechargée depuis le disque qu'en cas de modification du fichier
- Retourne : `IMAGE`, `lut_path`

---

### 🔍 Image Comparer  *(Legacy)*

<img width="1001" height="1015" alt="image" src="https://github.com/user-attachments/assets/10cea0dc-f84a-4019-b78a-1decc7267841" />

> Comparateur d'images interactif, optimisé pour l'interface ComfyUI classique (LiteGraph).
- **Interaction directe** : bascule entre A et B au clic sur l'image, ou via les deux ronds indicateurs sous l'image
- **Rendu HD** : dessin natif sur le canvas LiteGraph, reste net à tous les niveaux de zoom
- **Tailles différentes** : alignement automatique sur la plus grande dimension, letterbox sur fond noir — idéal pour comparer un original et son upscale
- **Compatible Nodes 2.0** avec deux limitations : le clic dans l'image ne bascule pas (utiliser les ronds en bas du node) ; le survol assombrit l'image (rendu natif Nodes 2.0 qui se superpose)
- **Usage idéal** : utilisateurs de l'interface ComfyUI classique (LiteGraph)

### 🔍 Image Comparer V2  *(beta, optimisé Nodes 2.0)*

<img width="846" height="991" alt="image" src="https://github.com/user-attachments/assets/c18d7d52-8a1a-42db-8261-b74ca09f2f64" />

> Comparateur d'images interactif, conçu pour la nouvelle interface Nodes 2.0 de ComfyUI.
- **Deux modes** : `slide` (curseur vertical révèle B sur A) et `click` (toggle entre A et B au clic)
- **Bouton Swap A/B** : inverse les deux images sans rebrancher les connexions (mode slide uniquement)
- **Tailles différentes** : alignement automatique sur la plus grande dimension, letterbox sur fond noir — idéal pour comparer un original et son upscale
- **Limitation** : en zoom du canvas ComfyUI (valeurs supérieures à 100%), pixelisation progressive d'affichage d'image
- **Usage idéal** : utilisateurs de la nouvelle interface Nodes 2.0

---

### 🎨 Color Pro — Chaîne de colorimétrie modulaire

> Un système d'effets colorimétrique en pipeline : des nœuds **émetteurs** produisent des descripteurs `COLOR_FX`, que le nœud **récepteur** applique dans l'ordre sur une image. Chaque émetteur peut aussi fonctionner en mode **standalone** (image directe en entrée/sortie).

**🎨 Color Pro Receiver** — Récepteur / point d'application
- Reçoit une `IMAGE` + des slots dynamiques `fx_1`, `fx_2`, … de type `COLOR_FX`
- Applique les effets dans l'ordre numérique des slots
- Les slots s'ajoutent automatiquement à la connexion (pattern dynamique)
- Retourne : `image` (IMAGE), `log` (STRING)

**Émetteurs disponibles :**

| Nœud | Description |
|------|-------------|
| **🎨 Channel Mixer FX** | Mixe les canaux R/G/B pour reconstruire chaque canal de sortie. Mode monochrome et préservation de luminosité. Équivalent Photoshop Channel Mixer. |
| **🎨 Color Balance FX** | Ajustement Ombres / Tons moyens / Hautes lumières façon Photoshop. Bascule "Preserve Luminosity". |
| **🎨 CSS Filters FX** | Applique les filtres CSS standard : `brightness`, `contrast`, `saturate`, `hue-rotate`, `sepia`, `grayscale`, `invert`. |
| **🎨 Hue/Sat/Light FX** | Ajustement TSL global ou ciblé par famille de teintes (Reds, Yellows, Greens, Cyans, Blues, Magentas) avec transition douce gaussienne. Mode Colorize inclus. |
| **🎨 Photo Filter FX** | Filtre de réchauffement/refroidissement couleur avec opacité et mode préservation luminosité, inspiré du filtre Photo de Photoshop. |
| **🎨 Vibrance FX** | Ajustement de Vibrance (protection des tons chair) et Saturation globale, indépendamment contrôlables. |

> 💡 Les émetteurs peuvent être utilisés en **mode chaîne** (sortie `fx` → slot `fx_N` du Receiver) ou en **mode standalone** (image directe en entrée/sortie), ou les deux simultanément.

---

### 📦 List Packer / Dict Packer / 📤 List Unpacker / 🖨️ Logger

| Nœud | Comportement |
|------|-------------|
| **List Packer (Infinite)** | Ports `item_N` dynamiques → sortie `list_out` |
| **Dict Packer (Infinite)** | Ports `val_N` + champs `key_N` dynamiques → sortie `dict_out` |
| **List Unpacker (Dynamic)** | Entrée `list_in` → jusqu'à 32 sorties `item_N` |
| **Logger (Debug Console)** | Affiche type, shape et valeur de n'importe quelle donnée |

> Tous les ports Packer/Unpacker apparaissent et disparaissent automatiquement selon les connexions.

---

## 🔧 Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/votre-username/Orion4D-coder.git
```

Redémarrez ComfyUI. Les nœuds apparaîtront dans la catégorie **`Orion4D_MetaNode`**.

> **Dépendances optionnelles** pour le LUT Generator : `pip install scipy opencv-python`

---

## ⚙️ Configuration

### Mode développeur (PyCode Max)
Par défaut, l'exécution de code en mode `text_input` est **désactivée** pour protéger contre les workflows partagés malveillants.

Éditez `config.json` à la racine du custom node :
```json
{
    "developer_mode": true
}
```

> ⚠️ N'activez cette option que sur votre machine personnelle. Ne partagez jamais de workflows contenant du code non vérifié en mode `text_input`.

---

### 📂 Folder File Max — Dossiers personnalisés

#### Pourquoi une allow-list ?

Les routes HTTP de **Folder File Max** sont exposées sur le serveur ComfyUI. Sans restriction, n'importe quel client sur le même réseau pourrait énumérer et lire n'importe quel fichier du disque. Par défaut, seules les racines internes de ComfyUI sont accessibles :

| Label | Chemin résolu |
|-------|--------------|
| `{COMFY}/input` | `ComfyUI/input/` |
| `{COMFY}/output` | `ComfyUI/output/` |
| `{COMFY}/temp` | `ComfyUI/temp/` |
| `{COMFY}/models` | `ComfyUI/models/` |

Tout chemin hors de ces racines est **refusé silencieusement** (le node retourne des sorties vides et log la raison dans la console).

#### Ajouter des dossiers via variable d'environnement

Déclarez la variable **`ORION4D_FOLDER_ROOTS`** avant de lancer ComfyUI. Les chemins sont séparés par le séparateur de votre OS (`;` sous Windows, `:` sous Linux/macOS).

**Windows — invite de commandes (cmd)**
```bat
set ORION4D_FOLDER_ROOTS=F:\lists;C:\Users\orion4d\Desktop\IN
python main.py
```

**Windows — PowerShell**
```powershell
$env:ORION4D_FOLDER_ROOTS = "F:\lists;C:\Users\orion4d\Desktop\IN"
python main.py
```

**Windows — permanent (session utilisateur)**
```bat
setx ORION4D_FOLDER_ROOTS "F:\lists;C:\Users\orion4d\Desktop\IN"
```
> Redémarrez le terminal après `setx` pour que la variable soit prise en compte.

**Linux / macOS — session courante**
```bash
export ORION4D_FOLDER_ROOTS="/home/orion4d/photos:/mnt/nas/shoots"
python main.py
```

**Linux / macOS — permanent** — ajoutez la ligne dans `~/.bashrc` ou `~/.zshrc` :
```bash
export ORION4D_FOLDER_ROOTS="/home/orion4d/photos:/mnt/nas/shoots"
```

#### Vérifier que les racines sont chargées

Au démarrage de ComfyUI, le node affiche dans la console la liste complète des racines autorisées :

```
[FolderFileMax] Racines autorisées (6) :
  {COMFY}/input                  → C:\ComfyUI\input
  {COMFY}/output                 → C:\ComfyUI\output
  {COMFY}/temp                   → C:\ComfyUI\temp
  {COMFY}/models                 → C:\ComfyUI\models
  F:\lists                       → F:\lists
  C:\Users\orion4d\Desktop\IN    → C:\Users\orion4d\Desktop\IN
```

Si un dossier déclaré n'existe pas au moment du démarrage, il est ignoré silencieusement (pas d'erreur, pas d'entrée dans la liste).

#### Comportement de sécurité

- Les chemins contenant `..` sont rejetés (pas de traversée de répertoire).
- Seules les extensions médias sont servies par les routes `/thumbnail` et `/view` — aucun fichier `.py`, `.json`, `.exe`, etc. n'est jamais transmis au navigateur.
- La navigation est **cadenassée à la racine choisie** dans le dropdown : il est impossible de remonter au-dessus via l'interface.
- Les jonctions Windows (Junction Points) pointant vers l'extérieur d'une racine autorisée sont **bloquées**.

> ⚠️ **Usage en réseau / partage de workflow** : toute racine ajoutée via `ORION4D_FOLDER_ROOTS` est accessible à **tous les clients** qui peuvent atteindre votre instance ComfyUI. N'exposez pas ComfyUI sur Internet avec des dossiers personnels dans l'allow-list.

---

### 📋 List Selector Max — Autoriser un dossier racine personnalisé

#### Modèle de sécurité

Par défaut, **List Selector Max** restreint l'accès aux fichiers `.txt` / `.csv` situés dans le dossier racine de ComfyUI (et tous ses sous-dossiers). Le token `{COMFY}` pointe toujours vers cette racine.

```
{COMFY}/custom_nodes/Orion4D_MetaNode/Lists/styles.txt  ✅ autorisé
C:\Users\orion4d\Desktop\prompts\abstract.txt           ❌ refusé par défaut
```

#### Autoriser un dossier externe via le widget `custom_root`

Le node expose un champ **`custom_root`** directement dans son interface. Renseignez-y le chemin absolu du dossier racine que vous souhaitez autoriser :

```
C:\Users\orion4d\Desktop\prompts
```

Une fois défini, le token `{CUSTOM}` est résolu vers ce dossier. Vous pouvez l'utiliser dans les chemins de vos groupes :

```
{CUSTOM}/styles/abstract.txt
{CUSTOM}/moods.csv
```

La validation s'effectue à chaque exécution : si le dossier n'existe pas ou si le chemin tente de sortir de la racine via `..`, l'accès est refusé et le groupe retourne une sélection vide.

#### Utiliser `{COMFY}` et `{CUSTOM}` ensemble

Les deux tokens sont cumulables au sein d'un même node. Un groupe peut pointer vers `{COMFY}/Lists/cameras.txt` et un autre vers `{CUSTOM}/moods.csv` — chaque chemin est validé indépendamment contre sa racine.

```
Groupe 1  →  {COMFY}/Lists/cameras.txt      (dans ComfyUI, portable)
Groupe 2  →  {CUSTOM}/abstract_moods.txt    (dossier personnel local)
```

#### ⚠️ Avertissement pour le partage de workflows et l'usage en réseau

> **Racine personnalisée = chemin absolu local.** Un workflow qui contient un `custom_root` ou des chemins `{CUSTOM}` **ne fonctionnera pas** tel quel sur une autre machine, ou si ComfyUI est partagé sur un réseau avec d'autres utilisateurs.
>
> - **Ne partagez pas** de workflows avec `custom_root` renseigné si d'autres personnes ont accès à votre instance ComfyUI — la route HTTP `/orion4d/lsm/list_dir` et `/orion4d/lsm/read_file` répondra à **tous les clients du réseau** pour les fichiers de cette racine.
> - **Préférez `{COMFY}`** pour tout ce qui doit rester portable : placez vos listes dans un sous-dossier de ComfyUI (ex. `ComfyUI/Lists/`) et référencez-les avec `{COMFY}/Lists/fichier.txt`.
> - Si vous devez partager un workflow utilisant `{CUSTOM}`, **videz `custom_root`** avant l'export ou remplacez les chemins par des équivalents `{COMFY}`.

---

<div align="center">

Fait avec ❤️ pour la communauté ComfyUI · **Orion4D**

</div>
