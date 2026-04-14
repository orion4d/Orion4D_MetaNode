// --- START OF FILE dynamic_packers.js ---
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.DynamicPackers",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        
        // ==========================================
        // 1. GESTION DU LIST PACKER
        // ==========================================
        if (nodeData.name === "PyCodeMax_ListPacker") {
            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
                if (type !== 1) return; // Uniquement les Entrées

                let itemInputs = this.inputs.filter(i => i.name.startsWith("item_"));
                if (itemInputs.length === 0) return;

                let lastInput = itemInputs[itemInputs.length - 1];
                let changed = false;

                // Si le dernier est branché, on ajoute le suivant
                if (lastInput.link != null) {
                    let nextIndex = itemInputs.length + 1;
                    this.addInput("item_" + nextIndex, "*");
                    changed = true;
                }

                // Nettoyage en cas de débranchement
                itemInputs = this.inputs.filter(i => i.name.startsWith("item_"));
                while (itemInputs.length > 1) {
                    let last = itemInputs[itemInputs.length - 1];
                    let prev = itemInputs[itemInputs.length - 2];

                    if (!last.link && !prev.link) {
                        this.removeInput(this.inputs.indexOf(last));
                        itemInputs.pop();
                        changed = true;
                    } else {
                        break;
                    }
                }
                
                // Redimensionnement de la boîte pour éviter le vide
                if (changed) {
                    this.setSize(this.computeSize([this.size[0], 0]));
                }
            };
        }

        // ==========================================
        // 2. GESTION DU DICT PACKER
        // ==========================================
        if (nodeData.name === "PyCodeMax_DictPacker") {

            // Fonction utilitaire : synchronise les widgets key_ avec les val_ connectés.
            // Règle : key_N existe UNIQUEMENT si val_N est connecté (link != null).
            // Le dernier port libre (invitation) n'a jamais de key_.
            function syncWidgets(node) {
                if (!node.inputs || !node.widgets) return;

                const valInputs = node.inputs.filter(i => i.name.startsWith("val_"));

                valInputs.forEach((inp, idx) => {
                    const n = idx + 1;
                    const keyName = "key_" + n;
                    const wIdx = node.widgets.findIndex(w => w.name === keyName);

                    if (inp.link != null) {
                        // Val connecté → key_ doit exister
                        if (wIdx === -1) {
                            node.addWidget("text", keyName, "param" + n);
                        }
                    } else {
                        // Val libre → key_ ne doit PAS exister
                        if (wIdx !== -1) {
                            node.widgets.splice(wIdx, 1);
                        }
                    }
                });

                node.setSize(node.computeSize([node.size[0], 0]));
            }

            // Étape A : Au chargement d'un workflow sauvegardé
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (onConfigure) onConfigure.apply(this, arguments);
                if (!this.inputs) return;

                // Supprimer les ports val_ vides en surplus (garder 1 seul port libre à la fin)
                let valInputs = this.inputs.filter(i => i.name.startsWith("val_"));
                while (valInputs.length > 1) {
                    let last = valInputs[valInputs.length - 1];
                    let prev = valInputs[valInputs.length - 2];
                    if (!last.link && !prev.link) {
                        this.removeInput(this.inputs.indexOf(last));
                        valInputs.pop();
                    } else {
                        break;
                    }
                }

                syncWidgets(this);
            };

            // Étape B : Interaction dynamique (branchement / débranchement)
            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
                if (type !== 1) return; // Uniquement les Entrées

                let valInputs = this.inputs.filter(i => i.name.startsWith("val_"));
                if (valInputs.length === 0) return;

                let lastInput = valInputs[valInputs.length - 1];
                let changed = false;

                // Si le dernier port est branché → ajouter un nouveau port libre
                if (lastInput.link != null) {
                    this.addInput("val_" + (valInputs.length + 1), "*");
                    changed = true;
                }

                // Nettoyer les ports libres en surplus (garder 1 seul à la fin)
                valInputs = this.inputs.filter(i => i.name.startsWith("val_"));
                while (valInputs.length > 1) {
                    let last = valInputs[valInputs.length - 1];
                    let prev = valInputs[valInputs.length - 2];
                    if (!last.link && !prev.link) {
                        this.removeInput(this.inputs.indexOf(last));
                        valInputs.pop();
                        changed = true;
                    } else {
                        break;
                    }
                }

                // Toujours resynchroniser les widgets key_ après chaque changement
                syncWidgets(this);
            };
        }
    }
});
// --- END OF FILE dynamic_packers.js ---