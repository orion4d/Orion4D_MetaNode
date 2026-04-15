// --- START OF FILE variable_bus.js ---
import { app } from "/scripts/app.js";

// État global du pack Bus :
//   - linksHidden : true = on ne rend pas les liens sync→dependency
// Le BusClear pilote ce flag via son widget show_bus_links.
const BusState = {
    linksHidden: true, // par défaut : câbles invisibles (effet "bus sans fil")
};

// ──────────────────────────────────────────────────────────────
// Patch du rendu des liens : on cache visuellement les liens
// sync → dependency. Ils existent toujours dans le graph (donc
// ComfyUI respecte l'ordre d'exécution), mais on ne les dessine pas.
// ──────────────────────────────────────────────────────────────
function isHiddenBusLink(link) {
    if (!link || !BusState.linksHidden) return false;
    const originNode = app.graph?.getNodeById(link.origin_id);
    const targetNode = app.graph?.getNodeById(link.target_id);
    if (!originNode || !targetNode) return false;
    if (originNode.type !== "PyCodeMax_BusSet") return false;
    if (targetNode.type !== "PyCodeMax_BusGet") return false;
    const outName = originNode.outputs?.[link.origin_slot]?.name;
    const inName  = targetNode.inputs?.[link.target_slot]?.name;
    return outName === "sync" && inName === "dependency";
}

function patchLinkRendering() {
    const proto = LGraphCanvas.prototype;
    if (proto.__orionBusPatched) return;

    const origRenderLink = proto.renderLink;
    if (typeof origRenderLink === "function") {
        proto.renderLink = function (ctx, a, b, link, ...rest) {
            if (isHiddenBusLink(link)) return;
            return origRenderLink.call(this, ctx, a, b, link, ...rest);
        };
    }

    proto.__orionBusPatched = true;
    console.log("🚌 [Bus] Rendu des liens sync/dependency patché.");
}

// ──────────────────────────────────────────────────────────────
// Helpers triplet
// ──────────────────────────────────────────────────────────────
function getWidgetValue(node, name) {
    const w = node.widgets?.find(w => w.name === name);
    return w ? w.value : null;
}
function getTriplet(node) {
    return {
        name:  getWidgetValue(node, "variable_name"),
        type:  getWidgetValue(node, "data_type"),
        phase: getWidgetValue(node, "execution_phase"),
    };
}
function tripletMatches(a, b) {
    return a.name === b.name && a.type === b.type && a.phase === b.phase;
}
function applySlotType(node, slotName, dataType, isInput = false) {
    const slots = isInput ? node.inputs : node.outputs;
    const idx = slots?.findIndex(s => s.name === slotName) ?? -1;
    if (idx === -1) return;
    const t = (!dataType || dataType === "*") ? "*" : dataType;
    slots[idx].type = t;
    slots[idx].color = (t === "*") ? undefined : LiteGraph.getTypeColor?.(t);
}

// Lit le toggle depuis le PREMIER BusClear trouvé dans le graph.
function refreshLinksVisibilityFromClear() {
    const clearNode = (app.graph?._nodes || []).find(n => n.type === "PyCodeMax_BusClear");
    if (clearNode) {
        const show = getWidgetValue(clearNode, "show_bus_links");
        BusState.linksHidden = !show;
    } else {
        BusState.linksHidden = true;
    }
    app.graph?.setDirtyCanvas(true, true);
}

function rescanAllBusLinks() {
    const nodes = app.graph?._nodes || [];
    for (const n of nodes) {
        if (n.type === "PyCodeMax_BusGet" && typeof n.__orionAutoReconnect === "function") {
            n.__orionAutoReconnect();
        }
    }
    app.graph?.setDirtyCanvas(true, true);
}

// ──────────────────────────────────────────────────────────────
// Extension principale
// ──────────────────────────────────────────────────────────────
app.registerExtension({
    name: "Orion4d.VariableBus",

    async setup() {
        patchLinkRendering();
        setTimeout(refreshLinksVisibilityFromClear, 200);
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {

        // ─────────────────────────────────────────────
        // BUS SET
        // ─────────────────────────────────────────────
        if (nodeData.name === "PyCodeMax_BusSet") {

            function syncSet(node) {
                const { type } = getTriplet(node);
                applySlotType(node, "passthrough", type, false);

                const outSyncIdx = node.outputs?.findIndex(o => o.name === "sync") ?? -1;
                if (outSyncIdx !== -1) {
                    node.outputs[outSyncIdx].color = "#445544";
                    node.outputs[outSyncIdx].label = "⬡ sync";
                }
                autoConnectAllGetsForThisSet(node);
                app.graph?.setDirtyCanvas(true, true);
            }

            function autoConnectAllGetsForThisSet(setNode) {
                const setTriplet = getTriplet(setNode);
                if (!setTriplet.name) return;
                const syncSlot = setNode.outputs?.findIndex(o => o.name === "sync");
                if (syncSlot === -1) return;

                for (const candidate of (app.graph._nodes || [])) {
                    if (candidate.type !== "PyCodeMax_BusGet") continue;
                    const getTripletVal = getTriplet(candidate);
                    if (!tripletMatches(setTriplet, getTripletVal)) continue;

                    const depIdx = candidate.inputs?.findIndex(i => i.name === "dependency");
                    if (depIdx === -1) continue;

                    const existing = candidate.inputs[depIdx].link;
                    if (existing != null) {
                        const link = app.graph.links[existing];
                        if (link && link.origin_id === setNode.id) continue;
                        candidate.disconnectInput(depIdx);
                    }
                    setNode.connect(syncSlot, candidate, depIdx);
                }
            }

            const onConnSet = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnSet) onConnSet.apply(this, arguments);
                setTimeout(() => syncSet(this), 0);
            };

            const onConfSet = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (onConfSet) onConfSet.apply(this, arguments);
                setTimeout(() => syncSet(this), 100);
            };

            const onCreatedSet = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onCreatedSet) onCreatedSet.apply(this, arguments);
                for (const wname of ["variable_name", "data_type", "execution_phase"]) {
                    const w = this.widgets?.find(w => w.name === wname);
                    if (!w) continue;
                    const orig = w.callback;
                    w.callback = (v, ...rest) => {
                        if (orig) orig.call(w, v, ...rest);
                        setTimeout(() => syncSet(this), 20);
                    };
                }
                syncSet(this);
            };
        }

        // ─────────────────────────────────────────────
        // BUS GET
        // ─────────────────────────────────────────────
        if (nodeData.name === "PyCodeMax_BusGet") {
            const DEPENDENCY_COLOR = "#445544";

            function syncGet(node) {
                const { type } = getTriplet(node);
                applySlotType(node, "output", type, false);

                const dep = node.inputs?.find(i => i.name === "dependency");
                if (dep) {
                    dep.color_on  = DEPENDENCY_COLOR;
                    dep.color_off = DEPENDENCY_COLOR;
                    dep.label     = "⬡ dependency";
                }
                app.graph?.setDirtyCanvas(true, true);
            }

            function autoReconnect(getNode) {
                const depIdx = getNode.inputs?.findIndex(i => i.name === "dependency");
                if (depIdx === -1) return;
                const getTripletVal = getTriplet(getNode);
                if (!getTripletVal.name) return;

                const curLinkId = getNode.inputs[depIdx].link;
                if (curLinkId != null) {
                    const link = app.graph.links[curLinkId];
                    if (link) {
                        const origin = app.graph.getNodeById(link.origin_id);
                        if (origin && origin.type === "PyCodeMax_BusSet") {
                            const originTriplet = getTriplet(origin);
                            if (tripletMatches(getTripletVal, originTriplet)) return;
                        }
                    }
                    getNode.disconnectInput(depIdx);
                }

                for (const candidate of (app.graph._nodes || [])) {
                    if (candidate.type !== "PyCodeMax_BusSet") continue;
                    const cTriplet = getTriplet(candidate);
                    if (!tripletMatches(getTripletVal, cTriplet)) continue;
                    const syncSlot = candidate.outputs?.findIndex(o => o.name === "sync");
                    if (syncSlot === -1) continue;
                    candidate.connect(syncSlot, getNode, depIdx);
                    console.log(`🚌 [Bus] Auto-branché: Set('${cTriplet.name}', ${cTriplet.type}, phase ${cTriplet.phase}) → Get`);
                    return;
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
                setTimeout(() => {
                    syncGet(this);
                    autoReconnect(this);
                }, 150);
            };

            const onCreatedGet = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onCreatedGet) onCreatedGet.apply(this, arguments);
                this.__orionAutoReconnect = () => autoReconnect(this);
                for (const wname of ["variable_name", "data_type", "execution_phase"]) {
                    const w = this.widgets?.find(w => w.name === wname);
                    if (!w) continue;
                    const orig = w.callback;
                    w.callback = (v, ...rest) => {
                        if (orig) orig.call(w, v, ...rest);
                        setTimeout(() => {
                            syncGet(this);
                            autoReconnect(this);
                        }, 20);
                    };
                }
                syncGet(this);
                setTimeout(() => autoReconnect(this), 100);
            };
        }

        // ─────────────────────────────────────────────
        // BUS CLEAR (contrôleur)
        // ─────────────────────────────────────────────
        if (nodeData.name === "PyCodeMax_BusClear") {

            const onCreatedClear = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onCreatedClear) onCreatedClear.apply(this, arguments);

                // Toggle "show_bus_links" : déclenche le re-render des liens
                const wShow = this.widgets?.find(w => w.name === "show_bus_links");
                if (wShow) {
                    const orig = wShow.callback;
                    wShow.callback = (v, ...rest) => {
                        if (orig) orig.call(wShow, v, ...rest);
                        BusState.linksHidden = !v;
                        app.graph?.setDirtyCanvas(true, true);
                        console.log(`🚌 [Bus] Links ${v ? "visible" : "hidden"}`);
                    };
                }

                // Bouton "Clear now" : appelle la route HTTP, clear immédiat
                this.addWidget("button", "🧹 Clear now", null, () => {
                    const mode = getWidgetValue(this, "clear_mode") || "all";
                    const varName = getWidgetValue(this, "variable_name") || "";
                    fetch("/orion4d/bus/clear", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ mode, variable_name: varName }),
                    }).then(r => r.json()).then(data => {
                        console.log(`🧹 [Bus CLEAR] ${data.before} → ${data.after} variables`);
                    }).catch(err => {
                        console.error("🧹 [Bus CLEAR] Erreur :", err);
                    });
                });

                // Bouton "Refresh bus links" : force le rescan des auto-connexions
                this.addWidget("button", "🔄 Refresh bus links", null, () => {
                    rescanAllBusLinks();
                    console.log("🚌 [Bus] Rescan terminé");
                });

                setTimeout(refreshLinksVisibilityFromClear, 50);
            };

            const onConfClear = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (onConfClear) onConfClear.apply(this, arguments);
                setTimeout(refreshLinksVisibilityFromClear, 100);
            };
        }
    }
});
// --- END OF FILE variable_bus.js ---
