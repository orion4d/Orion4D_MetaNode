// --- START OF FILE text_road.js ---
// UI du nœud 📝 Text Road.
// Dynamique : entrées STRING avec memo / toggle multi-actif / prefix / suffix.
// Pattern identique à dynamic_road.js — aucune entrée déclarée côté Python.

import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4DCoder.TextRoad",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "PyCodeMax_TextRoad") return;

        // ─────────────────────────────────────────────────
        // Sérialise l'état actuel des widgets → config_json
        // ─────────────────────────────────────────────────
        nodeType.prototype._updateConfig = function () {
            const cfgW = this.widgets?.find(w => w.name === "config_json");
            if (!cfgW) return;
            const configs = [];
            for (let i = 0; i < this.inputs.length; i++) {
                const idx = i + 1;
                const en  = this.widgets?.find(w => w.name === `enabled_${idx}`);
                const pre = this.widgets?.find(w => w.name === `prefix_${idx}`);
                const suf = this.widgets?.find(w => w.name === `suffix_${idx}`);
                configs.push({
                    enabled: en  ? !!en.value        : true,
                    prefix:  pre ? String(pre.value) : "",
                    suffix:  suf ? String(suf.value) : "",
                });
            }
            cfgW.value = JSON.stringify(configs);
        };

        // ─────────────────────────────────────────────────
        // Helpers visibilité widget
        // ─────────────────────────────────────────────────
        function showW(w, visible) {
            if (!w) return;
            if (visible) {
                w.type   = w._originalType || "text";
                w.hidden = false;
                delete w.computeSize;
            } else {
                w.type        = "hidden";
                w.hidden      = true;
                w.computeSize = () => [0, 0];
            }
        }

        // Spacer pointillé entre groupes
        function makeSpacerDraw(ref) {
            return function (ctx, node, W, y) {
                if (ref.hidden) return;
                ctx.save();
                ctx.beginPath();
                ctx.strokeStyle = "#444";
                ctx.lineWidth   = 1;
                ctx.setLineDash([4, 4]);
                ctx.moveTo(12, y + 8);
                ctx.lineTo(W - 12, y + 8);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.restore();
            };
        }

        // ─────────────────────────────────────────────────
        // Crée les widgets d'un slot (idempotent)
        // ─────────────────────────────────────────────────
        nodeType.prototype._ensureWidgets = function (idx) {
            // Spacer (sauf slot 1)
            if (idx > 1) {
                const spName = `spacer_${idx}`;
                if (!this.widgets?.find(w => w.name === spName)) {
                    const sp = this.addWidget("spacer", spName, "", () => {});
                    sp._originalType = "spacer";
                    sp.draw = makeSpacerDraw(sp);
                }
            }
            // Mémo
            const mName = `memo_${idx}`;
            if (!this.widgets?.find(w => w.name === mName)) {
                const mw = this.addWidget("text", mName, `Mémo ${idx}`, () => {
                    app.graph.setDirtyCanvas(true, true);
                });
                mw.label        = `input_${idx}`;
                mw._originalType = "text";
            }
            // Enable toggle — multi-sélection possible
            const enName = `enabled_${idx}`;
            if (!this.widgets?.find(w => w.name === enName)) {
                const ew = this.addWidget("toggle", enName, true, () => {
                    this._updateConfig();
                    app.graph.setDirtyCanvas(true, true);
                });
                ew.label        = "Enable";
                ew._originalType = "toggle";
            }
            // Prefix
            const prName = `prefix_${idx}`;
            if (!this.widgets?.find(w => w.name === prName)) {
                const pw = this.addWidget("text", prName, "", () => {
                    this._updateConfig();
                    app.graph.setDirtyCanvas(true, true);
                });
                pw.label        = "Prefix";
                pw._originalType = "text";
            }
            // Suffix
            const sfName = `suffix_${idx}`;
            if (!this.widgets?.find(w => w.name === sfName)) {
                const sw = this.addWidget("text", sfName, "", () => {
                    this._updateConfig();
                    app.graph.setDirtyCanvas(true, true);
                });
                sw.label        = "Suffix";
                sw._originalType = "text";
            }
        };

        // ─────────────────────────────────────────────────
        // syncUI — cœur de la logique dynamique
        // ─────────────────────────────────────────────────
        nodeType.prototype.syncUI = function () {
            if (!this.inputs) this.inputs = [];

            // ── 1. Auto-collapse : compacte les trous ──
            let removedAny = false;
            for (let i = this.inputs.length - 2; i >= 0; i--) {
                if (this.inputs[i].link == null) {
                    for (let j = i + 1; j < this.inputs.length; j++) {
                        const src = j + 1, dst = j;
                        ["memo_", "enabled_", "prefix_", "suffix_"].forEach(pfx => {
                            const wS = this.widgets?.find(w => w.name === pfx + src);
                            const wD = this.widgets?.find(w => w.name === pfx + dst);
                            if (wS && wD) wD.value = wS.value;
                        });
                    }
                    this.removeInput(i);
                    removedAny = true;
                }
            }
            if (removedAny) {
                for (let i = 0; i < this.inputs.length; i++) {
                    this.inputs[i].name = `txt_${i + 1}`;
                }
            }

            // ── 2. Toujours au moins 1 slot ouvert ──
            if (this.inputs.length === 0) {
                this.addInput("txt_1", "STRING");
            } else {
                const last = this.inputs[this.inputs.length - 1];
                if (last && last.link != null) {
                    this.addInput(`txt_${this.inputs.length + 1}`, "STRING");
                }
            }

            // ── 3. Masquer config_json (widget technique) ──
            const cfgW = this.widgets?.find(w => w.name === "config_json");
            if (cfgW) {
                cfgW.type        = "hidden";
                cfgW.hidden      = true;
                cfgW.computeSize = () => [0, -4];
            }

            // ── 4. Créer les widgets de chaque slot + affichage conditionnel ──
            for (let i = 0; i < this.inputs.length; i++) {
                const idx       = i + 1;
                const connected = this.inputs[i].link != null;

                this._ensureWidgets(idx);

                const spW  = this.widgets?.find(w => w.name === `spacer_${idx}`);
                const mW   = this.widgets?.find(w => w.name === `memo_${idx}`);
                const enW  = this.widgets?.find(w => w.name === `enabled_${idx}`);
                const prW  = this.widgets?.find(w => w.name === `prefix_${idx}`);
                const sfW  = this.widgets?.find(w => w.name === `suffix_${idx}`);

                if (spW) showW(spW, connected && idx > 1);
                showW(mW,  connected);
                showW(enW, connected);
                showW(prW, connected);
                showW(sfW, connected);
            }

            // ── 5. Purge des widgets fantômes ──
            if (this.widgets) {
                for (let i = this.widgets.length - 1; i >= 0; i--) {
                    const w = this.widgets[i];
                    if (["config_json", "separator"].includes(w.name)) continue;
                    const m = w.name.match(/^(memo_|enabled_|prefix_|suffix_|spacer_)(\d+)$/);
                    if (m && parseInt(m[2]) > this.inputs.length) {
                        this.widgets.splice(i, 1);
                    }
                }
            }

            // Sérialise et redimensionne
            this._updateConfig();
            const ms = this.computeSize();
            this.setSize([Math.max(this.size[0], ms[0]), ms[1]]);
        };

        // ─────────────────────────────────────────────────
        // onNodeCreated
        // ─────────────────────────────────────────────────
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            // Supprimer tout slot parasite hérité du Python (il ne doit pas y en avoir)
            if (this.inputs) {
                for (let i = this.inputs.length - 1; i >= 0; i--) {
                    this.removeInput(i);
                }
            }

            this.size = [380, 120];
            this.syncUI();
        };

        // ─────────────────────────────────────────────────
        // onConfigure : restauration d'un workflow sauvegardé
        // ─────────────────────────────────────────────────
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            // Pré-crée les widgets AVANT que LiteGraph ne restaure les valeurs
            if (info?.inputs) {
                for (let i = 0; i < info.inputs.length; i++) {
                    this._ensureWidgets(i + 1);
                }
            }
            if (onConfigure) onConfigure.apply(this, arguments);
            setTimeout(() => this.syncUI(), 50);
        };

        // ─────────────────────────────────────────────────
        // onConnectionsChange
        // ─────────────────────────────────────────────────
        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
            if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
            if (type === LiteGraph.INPUT && !app.configuring) {
                this.syncUI();
            }
        };
    }
});
// --- END OF FILE text_road.js ---
