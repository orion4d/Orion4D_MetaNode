// --- START OF FILE model_selector.js ---
//
// Model Selector v3 — option B (select HTML custom)
//
// Même mécanique que master_combo.js : le widget STRING file_name est
// masqué et remplacé par un <select> HTML stylé qui affiche uniquement
// les fichiers de la catégorie courante, sans préfixe.

import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.ModelSelector",
    async nodeCreated(node) {
        if (node.comfyClass !== "PyCodeMax_ModelSelector") return;

        let modelData = { categories: [], files_by_category: {} };

        const loadModels = async () => {
            try {
                const response = await fetch("/orion4d/get_models");
                const data = await response.json();
                if (data && data.categories && data.files_by_category) {
                    return data;
                }
                if (data && typeof data === "object") {
                    return {
                        categories: Object.keys(data),
                        files_by_category: data,
                    };
                }
            } catch (e) {
                console.error("[Orion4d] Erreur API Modèles :", e);
            }
            return { categories: [], files_by_category: {} };
        };

        modelData = await loadModels();

        const categoryWidget = node.widgets.find((w) => w.name === "category");
        const fileWidget     = node.widgets.find((w) => w.name === "file_name");
        if (!categoryWidget || !fileWidget) return;

        // Masquer le STRING natif
        fileWidget.hidden = true;
        fileWidget.computeSize = () => [0, -4];

        // ─── Création du <select> ───────────────────────────────────────
        const container = document.createElement("div");
        container.style.cssText = `
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 2px 4px;
            box-sizing: border-box;
            width: 100%;
            font-family: Arial, Helvetica, sans-serif;
        `;

        const label = document.createElement("span");
        label.textContent = "file_name";
        label.style.cssText = `
            font-size: 12px;
            color: #aaa;
            flex-shrink: 0;
            min-width: 70px;
        `;

        const select = document.createElement("select");
        select.style.cssText = `
            flex: 1;
            min-width: 0;
            background: #222;
            color: #ddd;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 13px;
            font-family: inherit;
            cursor: pointer;
        `;

        container.appendChild(label);
        container.appendChild(select);

        node.addDOMWidget("file_name_select", "div", container, {
            serialize: false,
        });

        const refreshSelect = (preserveValue) => {
            const cat = categoryWidget.value;
            const opts = modelData.files_by_category[cat] || [];
            select.innerHTML = "";

            if (opts.length === 0) {
                const o = document.createElement("option");
                o.value = "";
                o.textContent = "(aucun fichier)";
                o.disabled = true;
                select.appendChild(o);
                select.value = "";
                fileWidget.value = "";
                node.setDirtyCanvas(true, false);
                return;
            }

            opts.forEach((opt) => {
                const o = document.createElement("option");
                o.value = opt;
                o.textContent = opt;
                select.appendChild(o);
            });

            if (preserveValue && opts.includes(fileWidget.value)) {
                select.value = fileWidget.value;
            } else {
                select.value = opts[0];
                fileWidget.value = opts[0];
            }
            node.setDirtyCanvas(true, false);
        };

        select.addEventListener("change", () => {
            fileWidget.value = select.value;
            node.setDirtyCanvas(true, false);
        });
        select.addEventListener("keydown", (e) => e.stopPropagation());

        // ─── Bouton Refresh ─────────────────────────────────────────────
        node.addWidget("button", "🔄 Actualiser les modèles", null, async () => {
            modelData = await loadModels();
            if (!modelData.categories.includes(categoryWidget.value)) {
                categoryWidget.options.values = modelData.categories.length
                    ? modelData.categories
                    : ["(aucun)"];
                categoryWidget.value = categoryWidget.options.values[0];
            } else {
                categoryWidget.options.values = modelData.categories;
            }
            refreshSelect(true);
            node.setDirtyCanvas(true, true);
        });

        const prevCallback = categoryWidget.callback;
        categoryWidget.callback = function () {
            if (prevCallback) prevCallback.apply(this, arguments);
            refreshSelect(false);
        };

        refreshSelect(true);
    },
});
// --- END OF FILE model_selector.js ---
