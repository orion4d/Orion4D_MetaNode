// --- START OF FILE color_fx_presets.js ---
//
// Système de presets générique pour les nodes Color FX du pack.
//
// S'attache à tous les nodes FX listés dans FX_NODE_CONFIG et leur ajoute
// automatiquement les widgets :
//   - preset (combo)        : liste des presets disponibles
//   - 💾 Save preset        : bouton qui demande un nom puis sauvegarde
//   - 🗑️ Delete preset      : bouton qui supprime le preset courant
//   - 🔄 Refresh presets    : recharge la liste depuis le disque
//   - ↺ Reset               : remet tous les params à leurs valeurs par défaut
//
// La sauvegarde porte UNIQUEMENT sur les params métier (pas enabled, pas
// label). Les noms de widgets sauvegardés sont définis dans paramWidgets.

import { app } from "/scripts/app.js";

// ─── Configuration : un mapping nodeName → {fxType, paramWidgets} ──────
// Pour ajouter un nouveau FX au système de presets :
//   1. Ajouter une entrée ici avec son nodeName ComfyUI
//   2. fxType doit correspondre à ALLOWED_FX_TYPES côté Python
//   3. paramWidgets liste les noms de widgets à sauvegarder (params métier
//      uniquement, pas enabled/label/image_in)
const FX_NODE_CONFIG = {
    "PyCodeMax_ChannelMixerFX": {
        fxType: "channel_mixer",
        paramWidgets: [
            "output_channel",
            "red_source",
            "green_source",
            "blue_source",
            "constant",
            "monochrome",
            "preserve_luminosity",
        ],
    },
    "PyCodeMax_CSSFiltersFX": {
        fxType: "css_filters",
        paramWidgets: [
            "blur",
            "brightness",
            "contrast",
            "saturate",
            "grayscale",
            "sepia",
            "hue_rotate",
            "invert",
        ],
    },
    "PyCodeMax_HSLFX": {
        fxType: "hsl",
        paramWidgets: [
            "target",
            "hue",
            "saturation",
            "lightness",
            "colorize",
            "colorize_hue",
            "colorize_saturation",
        ],
    },
    "PyCodeMax_ColorBalanceFX": {
        fxType: "color_balance",
        paramWidgets: [
            "adjust_type",
            "cyan_red",
            "magenta_green",
            "yellow_blue",
            "preserve_luminosity",
        ],
    },
    "PyCodeMax_PhotoFilterFX": {
        fxType: "photo_filter",
        paramWidgets: [
            "color_hex",
            "density",
            "preserve_luminosity",
        ],
    },
    "PyCodeMax_VibranceFX": {
        fxType: "vibrance",
        paramWidgets: [
            "vibrance",
            "saturation",
            "protect_skin_tones",
            "strength",
        ],
    },
    "PyCodeMax_Matrix3x3FX": {
        fxType: "matrix_3x3",
        paramWidgets: [
            "m00", "m01", "m02",
            "m10", "m11", "m12",
            "m20", "m21", "m22",
            "offset_r",
            "offset_g",
            "offset_b",
            "strength",
            "preserve_luminosity",
            "clamp_output",
        ],
    },
    "PyCodeMax_DCTLToneMapperFX": {
        fxType: "dctl_tone_mapper",
        paramWidgets: [
            "mode",
            "exposure",
            "contrast",
            "pivot",
            "highlight_rolloff",
            "shadow_lift",
            "black_floor",
            "saturation",
            "preserve_luminosity",
            "strength",
            "clamp_output",
        ],
    },
    "PyCodeMax_CurvesPro": {
        fxType: "curves",
        paramWidgets: [
            "all_curves_json",
        ],
        // Hook spécial : après applyParams, on doit notifier le canvas
        // Curves Pro pour qu'il re-parse all_curves_json et redessine.
        // Le canvas expose une fonction globale sur le node quand il existe.
        onApplyHook: (node) => {
            if (typeof node._curvesProReloadFromJson === "function") {
                try { node._curvesProReloadFromJson(); }
                catch (e) { console.warn("[CurvesPro preset apply] reload failed:", e); }
            }
        },
        // Hook spécial pour collect : on veut stocker le JSON courant tel
        // que le canvas le connaît, pas ce qu'il y a dans le widget
        // (qui peut être désynchronisé si le widget est caché).
        onCollectHook: (node) => {
            if (typeof node._curvesProGetJson === "function") {
                try {
                    return { all_curves_json: node._curvesProGetJson() };
                } catch (e) {
                    console.warn("[CurvesPro preset collect] get failed:", e);
                }
            }
            return null; // fallback : collect normal via widgets
        },
    },
};

const NONE_LABEL = "(none)";


// Helpers API
async function apiListPresets(fxType) {
    try {
        const r = await fetch(`/orion4d/fx_presets/list?fx_type=${encodeURIComponent(fxType)}`);
        const d = await r.json();
        return Array.isArray(d.presets) ? d.presets : [];
    } catch (e) {
        console.error("[ColorFX presets] list error:", e);
        return [];
    }
}

async function apiLoadPreset(fxType, name) {
    try {
        const r = await fetch(
            `/orion4d/fx_presets/load?fx_type=${encodeURIComponent(fxType)}&name=${encodeURIComponent(name)}`
        );
        if (!r.ok) return null;
        const d = await r.json();
        return d.params || null;
    } catch (e) {
        console.error("[ColorFX presets] load error:", e);
        return null;
    }
}

async function apiSavePreset(fxType, name, params) {
    try {
        const r = await fetch("/orion4d/fx_presets/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fx_type: fxType, name, params }),
        });
        const d = await r.json();
        if (!r.ok) {
            alert("Erreur sauvegarde : " + (d.error || r.status));
            return null;
        }
        return d.presets || [];
    } catch (e) {
        console.error("[ColorFX presets] save error:", e);
        alert("Erreur sauvegarde : " + e.message);
        return null;
    }
}

async function apiDeletePreset(fxType, name) {
    try {
        const r = await fetch("/orion4d/fx_presets/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fx_type: fxType, name }),
        });
        const d = await r.json();
        if (!r.ok) {
            alert("Erreur suppression : " + (d.error || r.status));
            return null;
        }
        return d.presets || [];
    } catch (e) {
        console.error("[ColorFX presets] delete error:", e);
        return null;
    }
}


// ─── Extension : injecter le système dans chaque FX configuré ──────────
app.registerExtension({
    name: "Orion4d.ColorFXPresets",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const cfg = FX_NODE_CONFIG[nodeData.name];
        if (!cfg) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            const node = this;

            // Capturer les valeurs par défaut AVANT toute modification.
            // On utilise w.options.default si disponible, sinon w.value au moment
            // où onNodeCreated est appelé (qui correspond aux defaults Python).
            const defaultParams = {};
            for (const name of cfg.paramWidgets) {
                const w = node.widgets.find((x) => x.name === name);
                if (!w) continue;
                const def = (w.options && w.options.default !== undefined)
                    ? w.options.default
                    : w.value;
                defaultParams[name] = def;
            }

            // ─── Widget : combo preset ─────────────────────────────────
            const presetWidget = node.addWidget(
                "combo",
                "preset",
                NONE_LABEL,
                async (value) => {
                    if (value === NONE_LABEL) return;
                    const params = await apiLoadPreset(cfg.fxType, value);
                    if (!params) {
                        alert(`Preset '${value}' introuvable`);
                        presetWidget.value = NONE_LABEL;
                        return;
                    }
                    applyParams(params);
                    node.setDirtyCanvas(true, true);
                },
                { values: [NONE_LABEL] }
            );

            // ─── Bouton : 💾 Save ──────────────────────────────────────
            node.addWidget("button", "💾 Save preset", null, async () => {
                const name = prompt("Nom du preset :", presetWidget.value !== NONE_LABEL ? presetWidget.value : "");
                if (!name) return;
                const cleanName = name.trim();
                if (!cleanName) {
                    alert("Nom vide.");
                    return;
                }
                if (!/^[a-zA-Z0-9_\- ]{1,64}$/.test(cleanName)) {
                    alert("Caractères autorisés : lettres, chiffres, espace, _, -. Max 64.");
                    return;
                }
                const params = collectParams();
                const newList = await apiSavePreset(cfg.fxType, cleanName, params);
                if (newList) {
                    presetWidget.options.values = [NONE_LABEL, ...newList];
                    presetWidget.value = cleanName;
                    node.setDirtyCanvas(true, true);
                }
            });

            // ─── Bouton : 🗑️ Delete ────────────────────────────────────
            node.addWidget("button", "🗑️ Delete preset", null, async () => {
                const current = presetWidget.value;
                if (!current || current === NONE_LABEL) {
                    alert("Aucun preset sélectionné.");
                    return;
                }
                if (!confirm(`Supprimer le preset '${current}' ? Cette action est irréversible.`)) {
                    return;
                }
                const newList = await apiDeletePreset(cfg.fxType, current);
                if (newList) {
                    presetWidget.options.values = [NONE_LABEL, ...newList];
                    presetWidget.value = NONE_LABEL;
                    node.setDirtyCanvas(true, true);
                }
            });

            // ─── Bouton : 🔄 Refresh ───────────────────────────────────
            node.addWidget("button", "🔄 Refresh presets", null, async () => {
                const list = await apiListPresets(cfg.fxType);
                const cur = presetWidget.value;
                presetWidget.options.values = [NONE_LABEL, ...list];
                if (!list.includes(cur)) presetWidget.value = NONE_LABEL;
                node.setDirtyCanvas(true, true);
            });

            // ─── Bouton : ↺ Reset ──────────────────────────────────────
            node.addWidget("button", "↺ Reset params", null, () => {
                applyParams(defaultParams);
                presetWidget.value = NONE_LABEL;
                node.setDirtyCanvas(true, true);
            });

            // ─── Helpers internes ──────────────────────────────────────
            function collectParams() {
                // Hook spécial (pour Curves Pro notamment) : si le node a
                // une fonction custom qui sait collecter ses params, on
                // l'utilise en priorité.
                if (typeof cfg.onCollectHook === "function") {
                    const customParams = cfg.onCollectHook(node);
                    if (customParams && typeof customParams === "object") {
                        return customParams;
                    }
                }
                const out = {};
                for (const name of cfg.paramWidgets) {
                    const w = node.widgets.find((x) => x.name === name);
                    if (w !== undefined && w !== null) {
                        out[name] = w.value;
                    }
                }
                return out;
            }

            function applyParams(params) {
                for (const name of cfg.paramWidgets) {
                    if (!(name in params)) continue;
                    const w = node.widgets.find((x) => x.name === name);
                    if (w === undefined || w === null) continue;
                    w.value = params[name];
                    // Déclencher le callback du widget si défini (utile pour
                    // les FX qui ont une logique interne de mise à jour)
                    if (typeof w.callback === "function") {
                        try { w.callback.call(w, w.value); } catch (e) { /* ignore */ }
                    }
                }
                // Hook spécial post-apply (pour Curves Pro : redraw du canvas)
                if (typeof cfg.onApplyHook === "function") {
                    cfg.onApplyHook(node);
                }
            }

            // ─── Chargement initial de la liste ────────────────────────
            (async () => {
                const list = await apiListPresets(cfg.fxType);
                presetWidget.options.values = [NONE_LABEL, ...list];
                node.setDirtyCanvas(true, true);
            })();
        };
    },
});
// --- END OF FILE color_fx_presets.js ---
