// --- START OF FILE boolean_switch.js ---
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.BooleanSwitch",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "PyCodeMax_BooleanSwitch") return;

        // Propage le type de l'entrée connectée vers la sortie "selected_item".
        // Règles :
        //  - 1 seule entrée connectée  → type de cette entrée
        //  - 2 entrées, même type      → ce type
        //  - 2 entrées, types différents → "*" (universel)
        //  - aucune entrée connectée   → "*"
        function syncOutputType(node) {
            const outIdx = node.outputs ? node.outputs.findIndex(o => o.name === "selected_item") : -1;
            if (outIdx === -1) return;

            const types = [];
            if (node.inputs) {
                for (const inp of node.inputs) {
                    if ((inp.name === "road_A" || inp.name === "road_B") && inp.link != null) {
                        const link = app.graph.links[inp.link];
                        if (link) {
                            const originNode = app.graph.getNodeById(link.origin_id);
                            if (originNode && originNode.outputs && originNode.outputs[link.origin_slot]) {
                                const t = originNode.outputs[link.origin_slot].type || "*";
                                types.push(t);
                            }
                        }
                    }
                }
            }

            let detectedType = "*";
            if (types.length === 1) {
                detectedType = types[0];
            } else if (types.length === 2 && types[0] === types[1]) {
                detectedType = types[0];
            }
            // Si types différents ou aucun → reste "*"

            node.outputs[outIdx].type = detectedType;
            node.outputs[outIdx].color = detectedType === "*" ? undefined : LiteGraph.getTypeColor?.(detectedType);

            if (app.graph) app.graph.setDirtyCanvas(true, true);
        }

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
            if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
            setTimeout(() => syncOutputType(this), 0);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) onConfigure.apply(this, arguments);
            setTimeout(() => syncOutputType(this), 50);
        };
    }
});
// --- END OF FILE boolean_switch.js ---