// --- START OF FILE variable_bus.js ---
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.VariableBus",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {

        // ─────────────────────────────────────────────
        // BUS SET
        // ─────────────────────────────────────────────
        if (nodeData.name === "PyCodeMax_BusSet") {

            function syncSet(node) {
                const outPassIdx = node.outputs?.findIndex(o => o.name === "passthrough") ?? -1;
                const outSyncIdx = node.outputs?.findIndex(o => o.name === "sync") ?? -1;
                if (outPassIdx === -1) return;

                let detectedType = "*";
                const inp = node.inputs?.find(i => i.name === "input");
                if (inp?.link != null) {
                    const link = app.graph.links[inp.link];
                    if (link) {
                        const origin = app.graph.getNodeById(link.origin_id);
                        if (origin?.outputs?.[link.origin_slot]) {
                            detectedType = origin.outputs[link.origin_slot].type || "*";
                        }
                    }
                }

                node.outputs[outPassIdx].type  = detectedType;
                node.outputs[outPassIdx].color = detectedType === "*"
                    ? undefined
                    : LiteGraph.getTypeColor?.(detectedType);

                if (outSyncIdx !== -1) {
                    node.outputs[outSyncIdx].color = "#445544";
                    node.outputs[outSyncIdx].label = "⬡ sync";
                }

                app.graph?.setDirtyCanvas(true, true);
            }

            const onConnSet = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnSet) onConnSet.apply(this, arguments);
                setTimeout(() => syncSet(this), 0);
            };

            const onConfSet = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (onConfSet) onConfSet.apply(this, arguments);
                setTimeout(() => syncSet(this), 50);
            };

            const onCreatedSet = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onCreatedSet) onCreatedSet.apply(this, arguments);
                syncSet(this);
            };
        }

        // ─────────────────────────────────────────────
        // BUS GET
        // ─────────────────────────────────────────────
        if (nodeData.name === "PyCodeMax_BusGet") {

            const DEPENDENCY_COLOR = "#445544";

            function syncGet(node) {
                const outIdx = node.outputs?.findIndex(o => o.name === "output") ?? -1;
                if (outIdx === -1) return;

                let detectedType = "*";
                const dep = node.inputs?.find(i => i.name === "dependency");

                if (dep?.link != null) {
                    const link = app.graph.links[dep.link];
                    if (link) {
                        const originNode = app.graph.getNodeById(link.origin_id);
                        if (originNode?.outputs?.[0]) {
                            detectedType = originNode.outputs[0].type || "*";
                        }
                    }
                }

                node.outputs[outIdx].type  = detectedType;
                node.outputs[outIdx].color = detectedType === "*"
                    ? undefined
                    : LiteGraph.getTypeColor?.(detectedType);

                if (dep) {
                    dep.color_on  = DEPENDENCY_COLOR;
                    dep.color_off = DEPENDENCY_COLOR;
                    dep.label     = "⬡ dependency";
                }

                app.graph?.setDirtyCanvas(true, true);
            }

            // ── Auto-reconnexion après duplication ────────────────────────
            // Quand l'utilisateur duplique un BusGet (Ctrl+D ou copier/coller),
            // LiteGraph appelle onConfigure sur le nouveau nœud SANS recréer
            // les liens. On cherche alors un BusSet portant le même variable_name
            // et on reconnecte automatiquement sync → dependency.
            function autoReconnect(node) {
                const dep = node.inputs?.find(i => i.name === "dependency");
                if (!dep || dep.link != null) return; // déjà branché

                const varWidget = node.widgets?.find(w => w.name === "variable_name");
                if (!varWidget) return;
                const varName = varWidget.value;

                // Cherche un BusSet avec le même variable_name dans le graphe
                const allNodes = app.graph._nodes || [];
                for (const candidate of allNodes) {
                    if (candidate.type !== "PyCodeMax_BusSet") continue;
                    const cw = candidate.widgets?.find(w => w.name === "variable_name");
                    if (!cw || cw.value !== varName) continue;

                    // Trouve le slot "sync" (slot 1) sur le BusSet
                    const syncSlot = candidate.outputs?.findIndex(o => o.name === "sync");
                    if (syncSlot === -1) continue;

                    // Trouve le slot "dependency" sur ce BusGet
                    const depSlot = node.inputs?.findIndex(i => i.name === "dependency");
                    if (depSlot === -1) continue;

                    // Crée le lien dans le graphe
                    app.graph.connect(candidate.id, syncSlot, node.id, depSlot);
                    console.log(`🚌 [Bus] Auto-reconnecté: BusSet('${varName}').sync → BusGet.dependency`);
                    break;
                }
            }

            const onConnGet = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnGet) onConnGet.apply(this, arguments);
                setTimeout(() => syncGet(this), 0);
            };

            const onConfGet = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (onConfGet) onConfGet.apply(this, arguments);
                // Délai plus long pour laisser le graphe finaliser la duplication
                setTimeout(() => {
                    autoReconnect(this);
                    syncGet(this);
                }, 100);
            };

            const onCreatedGet = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onCreatedGet) onCreatedGet.apply(this, arguments);
                syncGet(this);
            };
        }
    }
});
// --- END OF FILE variable_bus.js ---
