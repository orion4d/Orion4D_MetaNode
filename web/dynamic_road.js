// --- START OF FILE dynamic_road.js ---
import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4DCoder.DynamicRoad",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PyCodeMax_DynamicRoad") {

            nodeType.prototype.syncUI = function() {
                if (!this.inputs) this.inputs = [];

                // 1. AUTO-COLLAPSE
                let removedAny = false;
                for (let i = this.inputs.length - 2; i >= 0; i--) {
                    if (this.inputs[i].link == null) {
                        for (let j = i + 1; j < this.inputs.length; j++) {
                            let wNextDesc = this.widgets && this.widgets.find(w => w.name === "desc_" + (j + 1));
                            let wCurrDesc = this.widgets && this.widgets.find(w => w.name === "desc_" + j);
                            if (wNextDesc && wCurrDesc) wCurrDesc.value = wNextDesc.value;
                            
                            let wNextTog = this.widgets && this.widgets.find(w => w.name === "toggle_" + (j + 1));
                            let wCurrTog = this.widgets && this.widgets.find(w => w.name === "toggle_" + j);
                            if (wNextTog && wCurrTog) wCurrTog.value = wNextTog.value;
                        }
                        this.removeInput(i);
                        removedAny = true;
                    }
                }

                if (removedAny) {
                    for (let i = 0; i < this.inputs.length; i++) {
                        this.inputs[i].name = "input_" + (i + 1);
                    }
                }

                if (this.inputs.length === 0) {
                    this.addInput("input_1", "*");
                } else {
                    let lastInput = this.inputs[this.inputs.length - 1];
                    if (lastInput && lastInput.link != null) {
                        this.addInput("input_" + (this.inputs.length + 1), "*");
                    }
                }

                // 2. MASQUAGE DE L'INDEX CACHÉ
                let selWidget = this.widgets ? this.widgets.find(w => w.name === "selected_index") : null;
                if (selWidget) {
                    selWidget.type = "hidden";
                    selWidget.hidden = true;
                    selWidget.computeSize = () => [0, -4];
                }
                
                let activeIdx = selWidget ? selWidget.value : 1;

                // 3. GESTION DES GROUPES DE WIDGETS
                for (let i = 0; i < this.inputs.length; i++) {
                    let idx = i + 1;
                    
                    let spacerName = "spacer_" + idx;
                    let textName = "desc_" + idx;
                    let toggleName = "toggle_" + idx;
                    
                    let isConnected = (this.inputs[i].link != null);

                    let spacerW = this.widgets && this.widgets.find(w => w.name === spacerName);
                    if (!spacerW && idx > 1) {
                        spacerW = this.addWidget("spacer", spacerName, "", () => {});
                        spacerW._originalType = "spacer";
                        spacerW.draw = function(ctx, node, widget_width, y, widget_height) {
                            if (this.hidden) return; 
                            ctx.save();
                            ctx.beginPath();
                            ctx.strokeStyle = "#3a3a3a"; 
                            ctx.lineWidth = 2;
                            ctx.moveTo(15, y + 8);
                            ctx.lineTo(widget_width - 15, y + 8);
                            ctx.stroke();
                            ctx.restore();
                        };
                    }

                    let textW = this.widgets && this.widgets.find(w => w.name === textName);
                    if (!textW) {
                        textW = this.addWidget("text", textName, "Mémo " + idx, () => { app.graph.setDirtyCanvas(true, true); });
                        textW.label = "input_" + idx; 
                        textW._originalType = "text";
                    }
                    
                    let toggleW = this.widgets && this.widgets.find(w => w.name === toggleName);
                    if (!toggleW) {
                        toggleW = this.addWidget("toggle", toggleName, activeIdx === idx, (val) => {
                            if (val === true) {
                                if (selWidget) selWidget.value = idx;
                                this.syncUI();
                                app.graph.setDirtyCanvas(true, true);
                            } else {
                                if (selWidget && selWidget.value === idx) {
                                    let selfW = this.widgets.find(w => w.name === toggleName);
                                    if (selfW) selfW.value = true;
                                }
                            }
                        });
                        toggleW.label = "Enable"; 
                        toggleW._originalType = "toggle";
                    }
                    
                    if (toggleW) toggleW.value = (activeIdx === idx);

                    // 4. AFFICHAGE / MASQUAGE DYNAMIQUE
                    if (isConnected) {
                        if (spacerW) {
                            spacerW.type = spacerW._originalType;
                            spacerW.hidden = false;
                            spacerW.computeSize = () => [0, 16]; 
                        }
                        textW.type = textW._originalType || "text";
                        textW.hidden = false;
                        delete textW.computeSize;
                        
                        toggleW.type = toggleW._originalType || "toggle";
                        toggleW.hidden = false;
                        delete toggleW.computeSize;
                    } else {
                        if (spacerW) {
                            spacerW.type = "hidden";
                            spacerW.hidden = true;
                            spacerW.computeSize = () => [0, 0];
                        }
                        textW.type = "hidden";
                        textW.hidden = true;
                        textW.computeSize = () => [0, 0];
                        
                        toggleW.type = "hidden";
                        toggleW.hidden = true;
                        toggleW.computeSize = () => [0, 0];
                    }
                }

                // 5. NETTOYAGE DES WIDGETS FANTÔMES
                if (this.widgets) {
                    for (let i = this.widgets.length - 1; i >= 0; i--) {
                        let w = this.widgets[i];
                        if (w.name === "selected_index") continue;
                        let match = w.name.match(/^(desc_|toggle_|spacer_)(\d+)$/);
                        if (match) {
                            let idx = parseInt(match[2]);
                            if (idx > this.inputs.length) {
                                this.widgets.splice(i, 1);
                            }
                        }
                    }
                }

                // FIX DE LA LARGEUR : On ne rétrécit plus jamais la largeur (size[0]) !
                let minSize = this.computeSize();
                this.setSize([Math.max(this.size[0], minSize[0]), minSize[1]]);
            };

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);
                if (this.inputs) {
                    let badIdx = this.inputs.findIndex(i => i.name === "selected_index");
                    if (badIdx !== -1) this.removeInput(badIdx);
                }
                this.syncUI();
            };

            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (info && info.inputs) {
                    for (let i = 0; i < info.inputs.length; i++) {
                        let idx = i + 1;
                        if (idx > 1 && (!this.widgets || !this.widgets.find(w => w.name === "spacer_" + idx))) {
                            let sp = this.addWidget("spacer", "spacer_" + idx, "", () => {});
                            sp._originalType = "spacer";
                            sp.draw = function(ctx, node, widget_width, y, widget_height) {
                                if (this.hidden) return; 
                                ctx.save();
                                ctx.beginPath();
                                ctx.strokeStyle = "#3a3a3a";
                                ctx.lineWidth = 2;
                                ctx.moveTo(15, y + 8);
                                ctx.lineTo(widget_width - 15, y + 8);
                                ctx.stroke();
                                ctx.restore();
                            };
                        }
                        if (!this.widgets || !this.widgets.find(w => w.name === "desc_" + idx)) {
                            let tw = this.addWidget("text", "desc_" + idx, "Mémo " + idx, () => {});
                            tw.label = "input_" + idx;
                            tw._originalType = "text";
                        }
                        if (!this.widgets || !this.widgets.find(w => w.name === "toggle_" + idx)) {
                            let tog = this.addWidget("toggle", "toggle_" + idx, false, () => {});
                            tog.label = "Enable";
                            tog._originalType = "toggle";
                        }
                    }
                }
                if (onConfigure) onConfigure.apply(this, arguments);
                setTimeout(() => this.syncUI(), 50);
            };

            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (onConnectionsChange) onConnectionsChange.apply(this, arguments);
                if (type === LiteGraph.INPUT && !app.configuring) {
                    this.syncUI();
                }
            };
        }
    }
});
// --- END OF FILE dynamic_road.js ---