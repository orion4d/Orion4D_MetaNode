// --- START OF FILE execution_gate.js ---
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.ExecutionGate",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "PyCodeMax_ExecutionGate") return;

        // Propage le type de l'entrée "input" vers la sortie "output"
        // Comportement identique au nœud Reroute natif de ComfyUI.
        function syncOutputType(node) {
            const outIdx = node.outputs ? node.outputs.findIndex(o => o.name === "output") : -1;
            if (outIdx === -1) return;

            let detectedType = "*";
            if (node.inputs) {
                const inp = node.inputs.find(i => i.name === "input");
                if (inp && inp.link != null) {
                    const link = app.graph.links[inp.link];
                    if (link) {
                        const originNode = app.graph.getNodeById(link.origin_id);
                        if (originNode && originNode.outputs && originNode.outputs[link.origin_slot]) {
                            detectedType = originNode.outputs[link.origin_slot].type || "*";
                        }
                    }
                }
            }

            node.outputs[outIdx].type  = detectedType;
            node.outputs[outIdx].color = detectedType === "*"
                ? undefined
                : LiteGraph.getTypeColor?.(detectedType);

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
// --- END OF FILE execution_gate.js ---
