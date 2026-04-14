// --- START OF FILE list_unpacker.js ---
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.ListUnpacker",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PyCodeMax_ListUnpacker") {

            // 1. CRÉATION DU NŒUD 
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);

                // On réduit les 32 ports par défaut à un seul
                if (this.outputs) {
                    while (this.outputs.length > 1) {
                        this.removeOutput(this.outputs.length - 1);
                    }
                }
                
                // 🌟 LE CORRECTIF DE LA GRANDE FENÊTRE :
                // On dit au moteur de rétrécir la boîte juste après avoir supprimé les ports.
                setTimeout(() => {
                    this.setSize(this.computeSize([this.size[0], 0]));
                    if (app.graph) app.graph.setDirtyCanvas(true, true);
                }, 10);
            };

            // 2. LA GESTION DYNAMIQUE (Auto-Expand)
            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnectionsChange) onConnectionsChange.apply(this, arguments);

                // On ignore tout ce qui n'est pas une sortie
                if (type !== LiteGraph.OUTPUT) return;

                let changed = false;

                if (connected) {
                    // Si on branche le dernier, on ajoute
                    if (index === this.outputs.length - 1 && this.outputs.length < 32) {
                        this.addOutput("item_" + (this.outputs.length + 1), "*");
                        changed = true;
                    }
                } else {
                    // Si on débranche, on nettoie
                    while (this.outputs.length > 1) {
                        const last = this.outputs[this.outputs.length - 1];
                        const prev = this.outputs[this.outputs.length - 2];

                        const lastEmpty = !last.links || last.links.length === 0;
                        const prevEmpty = !prev.links || prev.links.length === 0;

                        if (lastEmpty && prevEmpty) {
                            this.removeOutput(this.outputs.length - 1);
                            changed = true;
                        } else {
                            break;
                        }
                    }
                }

                // 3. MISE À JOUR VISUELLE
                if (changed) {
                    if (this.outputs) {
                        this.outputs = [...this.outputs]; 
                    }
                    this.setSize(this.computeSize([this.size[0], 0]));
                    if (app.graph) app.graph.setDirtyCanvas(true, true);
                }
            };
        }
    }
});
// --- END OF FILE list_unpacker.js ---