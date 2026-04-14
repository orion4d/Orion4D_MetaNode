// --- START OF FILE parametric_slider.js ---
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
    name: "Orion4DCoder.ParametricSlider",

    // ========================================================
    // INTERCEPTION DE LA GÉNÉRATION (Auto-Incrément)
    // ========================================================
    setup() {
        if (app.__orion4dSliderHooked) return;

        const origQueuePrompt = app.queuePrompt;
        app.queuePrompt = async function() {
            // 1. Envoie la valeur ACTUELLE pour générer l'image
            const res = await origQueuePrompt.apply(this, arguments);

            // 2. Met à jour l'interface pour le PROCHAIN tour
            if (app.graph) {
                const nodes = app.graph._nodes.filter(n =>
                    n.type === "PyCodeMax_ParametricSlider" &&
                    n.widgets?.find(w => w.name === "control_after_generate")?.value !== "fixed"
                );

                if (nodes.length === 0) return res;

                for (let node of nodes) {
                    let ctrlW = node.widgets.find(w => w.name === "control_after_generate");
                    let valW  = node.widgets.find(w => w.name === "value");

                    if (!ctrlW || !valW) continue;

                    let action    = ctrlW.value;
                    let step      = valW.options.step      || 1;
                    let min       = valW.options.min       ?? 0;
                    let max       = valW.options.max       ?? 100;
                    let precision = valW.options.precision !== undefined ? valW.options.precision : 1;

                    if (action === "increment") {
                        valW.value += step;
                        if (valW.value > max) valW.value = min;
                    } else if (action === "decrement") {
                        valW.value -= step;
                        if (valW.value < min) valW.value = max;
                    } else if (action === "randomize") {
                        // [AMÉLIORATION 5] — seed indépendant par node
                        const ts   = Date.now();
                        const seed = (ts ^ (node.id * 2654435761)) >>> 0;
                        const rng  = ((seed * 1664525 + 1013904223) >>> 0) / 0xFFFFFFFF;
                        let range_steps = Math.floor((max - min) / step);
                        valW.value = min + Math.floor(rng * (range_steps + 1)) * step;
                    }

                    valW.value = Math.max(min, Math.min(max, valW.value));
                    if (precision === 0) valW.value = Math.round(valW.value);
                    else valW.value = Number(valW.value.toFixed(precision));

                    if (valW.element) valW.element.value = valW.value;
                }
                app.graph.setDirtyCanvas(true, true);
            }
            return res;
        };
        app.__orion4dSliderHooked = true;
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "PyCodeMax_ParametricSlider") return;

        // --------------------------------------------------------
        // [AMÉLIORATION 1] Chargement des presets avec feedback visuel
        // --------------------------------------------------------
        nodeType.prototype.fetchAndApplyPresets = async function(forceReload = false) {
            if (this._presetsLoaded && !forceReload) return;
            try {
                const endpoint = forceReload ? "/orion4d/reload_presets" : "/orion4d/slider_presets";
                const res = await api.fetchApi(endpoint, { method: forceReload ? "POST" : "GET" });
                this.sliderPresets = await res.json();

                if (Object.keys(this.sliderPresets).length === 0) {
                    console.warn("[Orion4D] Aucun preset trouvé — vérifiez le dossier json_slider/");
                    this.title = "⚠️ Parametric Slider";
                } else {
                    this.title = "🎚️ Parametric Slider";
                }

                this._presetsLoaded = true;
                this.setupWidgets();
            } catch (e) {
                console.error("[Orion4D] Erreur chargement des presets de slider", e);
                this.title = "❌ Parametric Slider";
                if (app.graph) app.graph.setDirtyCanvas(true, true);
            }
        };

        // --------------------------------------------------------
        // setupWidgets — configure uniquement, ne crée AUCUN widget
        // --------------------------------------------------------
        nodeType.prototype.setupWidgets = function() {
            const presetW = this.widgets.find(w => w.name === "preset");
            const valueW  = this.widgets.find(w => w.name === "value");

            if (!presetW || !valueW) return;

            // [AMÉLIORATION 3] — Affichage valeur formatée en temps réel
            // Guard sur flag : ne remplace le draw qu'une seule fois par instance
            if (!valueW._orionDrawSet) {
                const origDraw = valueW.draw?.bind(valueW);
                const self = this;
                valueW.draw = function(ctx, node, widget_width, y, widget_height) {
                    if (origDraw) origDraw(ctx, node, widget_width, y, widget_height);
                    const p         = self.sliderPresets?.[presetW.value] || {};
                    const unit      = p.unit ? " " + p.unit : "";
                    const precision = p.precision ?? 1;
                    const display   = precision === 0
                        ? Math.round(this.value) + unit
                        : Number(this.value).toFixed(precision) + unit;
                    ctx.save();
                    ctx.font        = "bold 11px Arial";
                    ctx.fillStyle   = "#ffffff";
                    ctx.textAlign   = "right";
                    ctx.globalAlpha = 0.85;
                    ctx.fillText(display, widget_width - 8, y + widget_height / 2 + 4);
                    ctx.restore();
                };
                valueW._orionDrawSet = true;
            }

            const applyPreset = (presetName, resetValue = true) => {
                const p = this.sliderPresets[presetName];
                if (!p) return;

                valueW.options.min       = p.min       ?? 0;
                valueW.options.max       = p.max       ?? 100;
                valueW.options.precision = p.precision ?? 1;

                if (valueW.options.precision === 0) {
                    valueW.options.step = Math.max(1, Math.round(p.step || 1));
                } else {
                    valueW.options.step = p.step !== undefined ? p.step : 0.1;
                }

                const unitText = p.unit ? " [" + p.unit.substring(0, 3) + "]" : "";
                valueW.label = (p.label || "Valeur") + unitText;

                if (resetValue && p.default !== undefined) {
                    valueW.value = p.default;
                } else {
                    valueW.value = Math.max(valueW.options.min, Math.min(valueW.options.max, valueW.value));
                }

                if (valueW.options.precision === 0) {
                    valueW.value = Math.round(valueW.value);
                } else {
                    valueW.value = Number(valueW.value.toFixed(valueW.options.precision));
                }

                if (valueW.element) valueW.element.value = valueW.value;

                // Persiste les paramètres dans le workflow pour restauration immédiate
                this.properties = this.properties || {};
                this.properties["orion_precision"] = valueW.options.precision;
                this.properties["orion_step"]      = valueW.options.step;
                this.properties["orion_min"]       = valueW.options.min;
                this.properties["orion_max"]       = valueW.options.max;
                this.properties["orion_label"]     = valueW.label;

                app.graph.setDirtyCanvas(true, true);
            };

            // Guard : n'empile pas plusieurs callbacks sur presetW
            if (!presetW._orionCallbackSet) {
                const origCallback = presetW.callback;
                presetW.callback = (val) => {
                    if (origCallback) origCallback(val);
                    applyPreset(val, true);
                };
                presetW._orionCallbackSet = true;
            }

            applyPreset(presetW.value, false);

            const minSize = this.computeSize();
            this.setSize([Math.max(this.size[0], 340), minSize[1]]);
        };

        // --------------------------------------------------------
        // Restauration immédiate depuis les properties sauvegardées
        // --------------------------------------------------------
        nodeType.prototype.restoreFromProperties = function() {
            const valueW = this.widgets?.find(w => w.name === "value");
            if (!valueW || this.properties?.orion_precision === undefined) return;

            valueW.options.precision = this.properties.orion_precision;
            valueW.options.step      = this.properties.orion_step  ?? valueW.options.step;
            valueW.options.min       = this.properties.orion_min   ?? valueW.options.min;
            valueW.options.max       = this.properties.orion_max   ?? valueW.options.max;

            if (this.properties.orion_label) valueW.label = this.properties.orion_label;

            if (this.properties.orion_precision === 0) {
                valueW.value = Math.round(valueW.value);
            } else {
                valueW.value = Number(valueW.value.toFixed(this.properties.orion_precision));
            }

            if (valueW.element) valueW.element.value = valueW.value;
        };

        // --------------------------------------------------------
        // Menu contextuel : Recharger les presets
        // --------------------------------------------------------
        const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function(_, options) {
            if (getExtraMenuOptions) getExtraMenuOptions.apply(this, arguments);
            options.push({
                content: "🔄 Recharger les presets",
                callback: () => {
                    this._presetsLoaded = false;
                    this.fetchAndApplyPresets(true);
                }
            });
        };

        // --------------------------------------------------------
        // Cycle de vie du node
        // --------------------------------------------------------
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            this.sliderPresets  = {};
            this._presetsLoaded = false;

            // [AMÉLIORATION 2] — Bouton Reset créé UNE SEULE FOIS ici,
            // jamais dans setupWidgets qui peut être appelé plusieurs fois.
            // La closure capture `this` via la flèche, donc presetW/valueW
            // sont résolus au moment du clic — toujours à jour.
            this.addWidget("button", "↺  Reset valeur", "reset_default_btn", () => {
                const presetW = this.widgets.find(w => w.name === "preset");
                const valueW  = this.widgets.find(w => w.name === "value");
                if (!presetW || !valueW) return;
                const p = this.sliderPresets?.[presetW.value];
                if (p && p.default !== undefined) {
                    valueW.value = p.default;
                    if (valueW.element) valueW.element.value = p.default;
                    app.graph.setDirtyCanvas(true, true);
                }
            });

            this.fetchAndApplyPresets();
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function(info) {
            if (onConfigure) onConfigure.apply(this, arguments);

            // Restauration synchrone immédiate depuis les properties sauvegardées
            this.restoreFromProperties();

            // Fetch ensuite pour mettre à jour si les JSONs ont changé
            if (!this._presetsLoaded) {
                this.fetchAndApplyPresets();
            }
        };
    }
});
// --- END OF FILE parametric_slider.js ---