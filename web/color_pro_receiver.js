// --- START OF FILE color_pro_receiver.js ---
//
// Color Pro Receiver — gestion des inputs dynamiques fx_N.
//
// Au démarrage, le node a un seul slot optionnel fx_1.
// Quand l'utilisateur connecte quelque chose sur fx_1, on ajoute fx_2.
// Quand il connecte fx_2, on ajoute fx_3. Etc.
// Quand il déconnecte et que deux derniers slots consécutifs sont vides,
// on supprime le dernier pour garder le node compact.
//
// Même pattern que dynamic_packers.js pour les List Packer / Dict Packer.

import { app } from "/scripts/app.js";

const FX_TYPE = "COLOR_FX";

app.registerExtension({
    name: "Orion4d.ColorProReceiver",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "PyCodeMax_ColorProReceiver") return;

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
            if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
            if (type !== 1) return; // LiteGraph.INPUT = 1, on ignore les changements de sortie

            let fxInputs = this.inputs.filter(i => i.name.startsWith("fx_"));
            if (fxInputs.length === 0) return;

            let changed = false;

            // Si le dernier slot fx_N est branché → ajouter fx_N+1
            const lastInput = fxInputs[fxInputs.length - 1];
            if (lastInput.link != null) {
                const nextIndex = fxInputs.length + 1;
                this.addInput("fx_" + nextIndex, FX_TYPE);
                changed = true;
            }

            // Nettoyage : tant que les deux derniers sont vides, on enlève le dernier
            // (on garde toujours au moins fx_1 en place comme "invitation")
            fxInputs = this.inputs.filter(i => i.name.startsWith("fx_"));
            while (fxInputs.length > 1) {
                const last = fxInputs[fxInputs.length - 1];
                const prev = fxInputs[fxInputs.length - 2];
                if (!last.link && !prev.link) {
                    this.removeInput(this.inputs.indexOf(last));
                    fxInputs.pop();
                    changed = true;
                } else {
                    break;
                }
            }

            if (changed) {
                this.setSize(this.computeSize([this.size[0], 0]));
            }
        };
    },
});
// --- END OF FILE color_pro_receiver.js ---
