// --- START OF FILE dynamic_splitter.js ---
import { app } from "/scripts/app.js";

const MIN_OUTPUTS = 2;

app.registerExtension({
    name: "Orion4D.DynamicSplitter",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "PyCodeMax_DynamicSplitter") return;

        function getWidget(node, name) {
            return node.widgets ? node.widgets.find(w => w.name === name) : null;
        }
        function readConfig(node) {
            const w = getWidget(node, "config_json");
            if (!w) return [];
            try { return JSON.parse(w.value); } catch { return []; }
        }
        function writeConfig(node, configs) {
            const w = getWidget(node, "config_json");
            if (w) w.value = JSON.stringify(configs);
        }

        // ----------------------------------------------------------------
        // syncOutputs : ajuste le nombre de ports SANS toucher aux existants
        // On ajoute à la fin si besoin, on supprime à la fin si trop.
        // Les connexions existantes sont préservées.
        // ----------------------------------------------------------------
        nodeType.prototype.syncOutputs = function(configs) {
            if (!this.outputs) this.outputs = [];
            const n = configs.length;
            const current = this.outputs.length;

            // Ajouter les manquants
            for (let i = current; i < n; i++) {
                this.addOutput(`out_${i + 1}`, "*");
            }

            // Supprimer les surplus par la fin (sans toucher aux connexions conservées)
            for (let i = this.outputs.length - 1; i >= n; i--) {
                this.removeOutput(i);
            }

            // Mettre à jour label + couleur sans recréer
            for (let i = 0; i < n; i++) {
                const cfg   = configs[i];
                const label = cfg.label && cfg.label.trim() ? cfg.label : `out_${i + 1}`;
                if (this.outputs[i]) {
                    this.outputs[i].name  = label;
                    this.outputs[i].color = cfg.enabled !== false ? "#4CAF50" : "#555555";
                }
            }
        };

        // ----------------------------------------------------------------
        // syncWidgets : reconstruit uniquement les widgets de contrôle
        // ----------------------------------------------------------------
        nodeType.prototype.syncWidgets = function(configs) {
            // Supprimer anciens widgets dynamiques
            if (this.widgets) {
                for (let i = this.widgets.length - 1; i >= 0; i--) {
                    const w = this.widgets[i];
                    if (w.name && (
                        w.name.startsWith("memo_")   ||
                        w.name.startsWith("toggle_") ||
                        w.name.startsWith("spacer_") ||
                        w.name === "add"         ||
                        w.name === "remove"
                    )) {
                        this.widgets.splice(i, 1);
                    }
                }
            }

            const n    = configs.length;
            const self = this;

            for (let i = 0; i < n; i++) {
                const cfg = configs[i];
                const idx = i + 1;

                // Séparateur
                if (i > 0) {
                    const sp = this.addWidget("separator", `spacer_${idx}`, "", () => {});
                    sp.computeSize = () => [0, 12];
                    sp.draw = function(ctx, node, w, y) {
                        ctx.save();
                        ctx.beginPath();
                        ctx.strokeStyle = "#3a3a3a";
                        ctx.lineWidth   = 1.5;
                        ctx.moveTo(15, y + 6);
                        ctx.lineTo(w - 15, y + 6);
                        ctx.stroke();
                        ctx.restore();
                    };
                }

                // Mémo — on met à jour label + output name sans recréer les ports
                const memoW = this.addWidget("text", `memo_${idx}`, cfg.label || "", (val) => {
                    const c = readConfig(self);
                    if (c[i] !== undefined) c[i].label = val;
                    writeConfig(self, c);
                    // Juste renommer l'output, pas de syncUI complet
                    if (self.outputs && self.outputs[i]) {
                        self.outputs[i].name = val && val.trim() ? val : `out_${idx}`;
                    }
                    app.graph.setDirtyCanvas(true, true);
                });
                memoW.label = `out_${idx}`;

                // Toggle — change couleur sans recréer les ports
                const togW = this.addWidget("toggle", `toggle_${idx}`, cfg.enabled !== false, (val) => {
                    const c = readConfig(self);
                    if (c[i] !== undefined) c[i].enabled = val;
                    writeConfig(self, c);
                    // Juste changer la couleur de l'output
                    if (self.outputs && self.outputs[i]) {
                        self.outputs[i].color = val ? "#4CAF50" : "#555555";
                    }
                    app.graph.setDirtyCanvas(true, true);
                });
                togW.label = "Actif";
            }

            // Boutons + / -
            const btnAdd = this.addWidget("button", "add", "＋", () => {
                const c = readConfig(self);
                c.push({ enabled: true, label: "" });
                writeConfig(self, c);
                self.syncOutputs(c);
                self.syncWidgets(c);
                const ms = self.computeSize();
                self.setSize([Math.max(self.size[0], ms[0], 260), ms[1]]);
                app.graph.setDirtyCanvas(true, true);
            });
            btnAdd.serialize = false;

            const btnRem = this.addWidget("button", "remove", "－", () => {
                const c = readConfig(self);
                if (c.length <= MIN_OUTPUTS) return;
                c.pop();
                writeConfig(self, c);
                self.syncOutputs(c);
                self.syncWidgets(c);
                const ms = self.computeSize();
                self.setSize([Math.max(self.size[0], ms[0], 260), ms[1]]);
                app.graph.setDirtyCanvas(true, true);
            });
            btnRem.serialize = false;
        };

        // ----------------------------------------------------------------
        // syncUI : point d'entrée principal
        // ----------------------------------------------------------------
        nodeType.prototype.syncUI = function() {
            // Masquer config_json
            const configW = getWidget(this, "config_json");
            if (configW) {
                configW.type        = "hidden";
                configW.hidden      = true;
                configW.computeSize = () => [0, -4];
            }

            const configs = readConfig(this);
            this.syncOutputs(configs);
            this.syncWidgets(configs);

            const ms = this.computeSize();
            this.setSize([Math.max(this.size[0], ms[0], 260), ms[1]]);
            app.graph.setDirtyCanvas(true, true);
        };

        // ----------------------------------------------------------------
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);
            const existing = readConfig(this);
            if (existing.length === 0) {
                writeConfig(this, [
                    { enabled: true, label: "" },
                    { enabled: true, label: "" },
                ]);
            }
            setTimeout(() => this.syncUI(), 50);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) onConfigure.apply(this, arguments);
            setTimeout(() => this.syncUI(), 80);
        };
    }
});
// --- END OF FILE dynamic_splitter.js ---