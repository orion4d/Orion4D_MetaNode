// --- START OF FILE super_saver.js ---
// Super Saver v5 - Orion4D_MetaNode
//
// Ordre des inputs :
//   image, caption_image, alpha_1…N (dynamiques), txt, add_metadata

import { app } from "/scripts/app.js";

const NODE_TYPE = "PyCodeMax_SuperSaver";

const FIXED_INPUT_ORDER = [
    "image",
    "caption_image",
    // alpha_1…N s'insèrent ici
    "txt",
    "add_metadata",
];

function reorderInputs(node) {
    if (!node.inputs) return;

    const alphas = node.inputs
        .filter(i => i.name.startsWith("alpha_"))
        .sort((a, b) => parseInt(a.name.split("_")[1]) - parseInt(b.name.split("_")[1]));

    const fixed = FIXED_INPUT_ORDER
        .map(name => node.inputs.find(i => i.name === name))
        .filter(Boolean);

    const ordered = [];
    for (const inp of fixed) {
        ordered.push(inp);
        if (inp.name === "caption_image") {
            for (const a of alphas) ordered.push(a);
        }
    }

    // Sécurité : tout input non référencé va à la fin
    for (const inp of node.inputs) {
        if (!ordered.includes(inp)) ordered.push(inp);
    }

    node.inputs = ordered;
}

function syncAlphas(node) {
    if (!node.inputs) return;

    const alphas = node.inputs
        .filter(i => i.name.startsWith("alpha_"))
        .sort((a, b) => parseInt(a.name.split("_")[1]) - parseInt(b.name.split("_")[1]));

    if (alphas.length === 0) return;

    let changed = false;

    // Dernier alpha connecté → ajouter le suivant
    if (alphas[alphas.length - 1].link != null) {
        node.addInput(`alpha_${alphas.length + 1}`, "IMAGE");
        changed = true;
    }

    // Nettoyer les doubles vides en fin (garder alpha_1 minimum)
    let current = node.inputs
        .filter(i => i.name.startsWith("alpha_"))
        .sort((a, b) => parseInt(a.name.split("_")[1]) - parseInt(b.name.split("_")[1]));

    while (current.length > 1) {
        const tail    = current[current.length - 1];
        const preTail = current[current.length - 2];
        if (!tail.link && !preTail.link) {
            node.removeInput(node.inputs.indexOf(tail));
            current.pop();
            changed = true;
        } else {
            break;
        }
    }

    if (changed) {
        reorderInputs(node);
        node.setSize(node.computeSize());
        node.setDirtyCanvas(true, true);
    }
}

app.registerExtension({
    name: "Orion4d.SuperSaver",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (origCreated) origCreated.apply(this, arguments);
            if (!this.inputs?.find(i => i.name === "alpha_1")) {
                this.addInput("alpha_1", "IMAGE");
            }
            reorderInputs(this);
            this.setSize(this.computeSize());
        };

        const origChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
            if (origChange) origChange.apply(this, arguments);
            if (type !== 1) return;
            const inp = this.inputs?.[index];
            if (!inp?.name.startsWith("alpha_")) return;
            syncAlphas(this);
        };

        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (origConfigure) origConfigure.apply(this, arguments);
            setTimeout(() => {
                syncAlphas(this);
                reorderInputs(this);
                this.setDirtyCanvas(true, true);
            }, 50);
        };
    },
});

// --- END OF FILE super_saver.js ---
