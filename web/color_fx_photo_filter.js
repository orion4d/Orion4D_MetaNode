// --- START OF FILE color_fx_photo_filter.js ---
//
// Photo Filter FX — UI custom du swatch couleur.
//
// Ajoute un aperçu DOM de la couleur courante dans le node, cliquable,
// qui ouvre le color picker système de l'OS repositionné près du swatch
// (même pattern que Color Picker v2 : input invisible déplacé avant le
// click pour que la palette s'affiche à proximité).
//
// L'aperçu se met à jour automatiquement quand color_hex change (via
// interception du callback du widget).

import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.PhotoFilterFX",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "PyCodeMax_PhotoFilterFX") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            const hexWidget = this.widgets.find((w) => w.name === "color_hex");
            if (!hexWidget) return;

            // ─── Input color natif (positionné dynamiquement) ──────────
            const colorInput = document.createElement("input");
            colorInput.type = "color";
            colorInput.style.cssText = `
                position: fixed;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: 0;
                border: 0;
                opacity: 0;
                pointer-events: none;
                z-index: -1;
            `;
            document.body.appendChild(colorInput);

            // Helper : ouvre la palette près de l'élément ancre
            const openPaletteNear = (anchorEl) => {
                let v = (hexWidget.value || "").trim();
                if (v.startsWith("#") && (v.length === 7 || v.length === 4)) {
                    colorInput.value = v.length === 4
                        ? "#" + v[1] + v[1] + v[2] + v[2] + v[3] + v[3]
                        : v;
                }
                if (anchorEl && anchorEl.getBoundingClientRect) {
                    const rect = anchorEl.getBoundingClientRect();
                    colorInput.style.left = `${rect.left}px`;
                    colorInput.style.top = `${rect.bottom}px`;
                }
                colorInput.click();
            };

            colorInput.addEventListener("input", (e) => {
                hexWidget.value = e.target.value.toUpperCase();
                updatePreview();
                app.graph.setDirtyCanvas(true, true);
            });

            // ─── DOM widget : aperçu carré cliquable ───────────────────
            const container = document.createElement("div");
            container.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 4px;
                padding: 6px;
                box-sizing: border-box;
                width: 100%;
                font-family: Arial, Helvetica, sans-serif;
            `;

            const swatch = document.createElement("div");
            swatch.style.cssText = `
                width: 100px;
                height: 60px;
                border: 2px solid #555;
                border-radius: 4px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                background: #EC8A3C;
                cursor: pointer;
                transition: background 0.1s ease;
            `;
            swatch.title = "Cliquer pour ouvrir le color picker";

            const infoLine = document.createElement("div");
            infoLine.style.cssText = `
                font-size: 10px;
                color: #ccc;
                font-family: 'Courier New', monospace;
                text-align: center;
            `;

            container.appendChild(swatch);
            container.appendChild(infoLine);

            this.addDOMWidget("photo_filter_preview", "div", container, {
                serialize: false,
            });

            swatch.addEventListener("click", () => openPaletteNear(swatch));

            // ─── Mise à jour de l'aperçu ───────────────────────────────
            const updatePreview = () => {
                let v = (hexWidget.value || "").trim();
                if (!v.startsWith("#")) v = "#" + v;
                if (/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(v)) {
                    swatch.style.background = v;
                }
                infoLine.textContent = v.toUpperCase();
            };

            // Hook : mettre à jour l'aperçu quand le widget change
            const prev = hexWidget.callback;
            hexWidget.callback = function () {
                if (prev) prev.apply(this, arguments);
                updatePreview();
            };

            updatePreview();
        };
    },
});
// --- END OF FILE color_fx_photo_filter.js ---
