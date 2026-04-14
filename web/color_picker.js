// --- START OF FILE color_picker.js ---
//
// Color Picker v2
//
// - Bouton "🎨 Ouvrir la palette" qui déclenche le color input natif du navigateur
// - Aperçu visuel : un carré coloré DOM qui se met à jour en temps réel
//   selon la valeur de color_hex
// - Texte hexadécimal et taille (width × height) affichés dans l'aperçu
//
// L'aperçu est un DOM widget classique : il prend la largeur du node et
// affiche un carré centré dont la couleur reflète l'hex courant.

import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.ColorPicker",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "PyCodeMax_ColorPicker") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            const hexWidget    = this.widgets.find(w => w.name === "color_hex");
            const widthWidget  = this.widgets.find(w => w.name === "width");
            const heightWidget = this.widgets.find(w => w.name === "height");
            if (!hexWidget) return;

            // ─── Color input natif (positionné dynamiquement) ───────────
            // L'<input type="color"> ouvre sa palette à proximité de sa propre
            // position dans le viewport. En display:none, le navigateur le
            // replie en haut-gauche par défaut. On le garde donc dans le DOM
            // avec une taille de 1×1 px (invisible) et on le déplace juste
            // avant chaque .click() pour qu'il soit positionné sous l'élément
            // déclencheur (bouton ou swatch).
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

            // Helper : positionne l'input juste sous l'élément déclencheur
            // puis ouvre la palette OS
            const openPaletteNear = (anchorEl) => {
                let v = (hexWidget.value || "").trim();
                if (v.startsWith("#") && (v.length === 7 || v.length === 4)) {
                    colorInput.value = v.length === 4
                        ? "#" + v[1] + v[1] + v[2] + v[2] + v[3] + v[3]
                        : v;
                }
                if (anchorEl && anchorEl.getBoundingClientRect) {
                    const rect = anchorEl.getBoundingClientRect();
                    // On vise le coin bas-gauche de l'élément
                    colorInput.style.left = `${rect.left}px`;
                    colorInput.style.top  = `${rect.bottom}px`;
                }
                colorInput.click();
            };

            colorInput.addEventListener("input", (event) => {
                hexWidget.value = event.target.value.toUpperCase();
                updatePreview();
                app.graph.setDirtyCanvas(true, true);
            });

            // ─── Bouton "Ouvrir la palette" ─────────────────────────────
            // On a besoin d'une référence à l'élément <button> rendu par
            // litegraph pour pouvoir l'utiliser comme ancre. Comme litegraph
            // ne nous donne pas directement le DOM, on utilise le swatch
            // (qui est dans un DOM widget, donc accessible) comme ancre par
            // défaut quand le bouton est cliqué.
            this.addWidget("button", "🎨 Ouvrir la palette", "color_btn", () => {
                openPaletteNear(swatch);
            });

            // ─── DOM widget : aperçu carré ──────────────────────────────
            const container = document.createElement("div");
            container.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 6px;
                padding: 8px;
                box-sizing: border-box;
                width: 100%;
                font-family: Arial, Helvetica, sans-serif;
            `;

            const swatch = document.createElement("div");
            swatch.style.cssText = `
                width: 120px;
                height: 120px;
                border: 2px solid #555;
                border-radius: 6px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                background: #F54927;
                transition: background 0.1s ease;
                cursor: pointer;
            `;
            swatch.title = "Cliquer pour ouvrir la palette";

            const infoLine = document.createElement("div");
            infoLine.style.cssText = `
                font-size: 11px;
                color: #ccc;
                font-family: 'Courier New', monospace;
                text-align: center;
                line-height: 1.3;
            `;

            container.appendChild(swatch);
            container.appendChild(infoLine);

            this.addDOMWidget("color_preview", "div", container, {
                serialize: false,
            });

            // Cliquer le swatch ouvre aussi la palette (raccourci ergonomique)
            swatch.addEventListener("click", () => {
                openPaletteNear(swatch);
            });

            // ─── Mise à jour de l'aperçu ────────────────────────────────
            const updatePreview = () => {
                let v = (hexWidget.value || "").trim();
                if (!v.startsWith("#")) v = "#" + v;

                // Validation rapide pour éviter d'appliquer un hex invalide
                const valid = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(v);
                if (valid) {
                    swatch.style.background = v;
                }

                const w = widthWidget ? widthWidget.value : "?";
                const h = heightWidget ? heightWidget.value : "?";
                infoLine.textContent = `${v.toUpperCase()}  •  ${w}×${h}px`;
            };

            // Hooks sur les widgets pour mettre à jour l'aperçu en temps réel
            const hookCallback = (widget) => {
                if (!widget) return;
                const prev = widget.callback;
                widget.callback = function () {
                    if (prev) prev.apply(this, arguments);
                    updatePreview();
                };
            };
            hookCallback(hexWidget);
            hookCallback(widthWidget);
            hookCallback(heightWidget);

            // État initial
            updatePreview();
        };

        // Suppression de l'ancien onDrawBackground (barre fine en bas) :
        // l'aperçu DOM le remplace avantageusement.
    }
});
// --- END OF FILE color_picker.js ---