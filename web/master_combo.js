// --- START OF FILE master_combo.js ---
//
// Master Combo Box v3 — option B
//
// Le widget "value" est un STRING natif côté Python. Le JS le masque et
// le remplace par un <select> HTML stylé qui :
//   - se filtre dynamiquement selon la catégorie courante
//   - écrit dans le widget STRING sous-jacent à chaque changement
//   - se synchronise au démarrage avec la valeur déjà présente dans le
//     workflow chargé (rétrocompatibilité)

import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Orion4d.MasterCombo",
    async nodeCreated(node) {
        if (node.comfyClass !== "PyCodeMax_MasterCombo") return;

        // ─── Données ────────────────────────────────────────────────────
        let dropdownData = { categories: [], options_by_category: {} };

        const loadDropdowns = async () => {
            try {
                const response = await fetch("/orion4d/get_dropdowns");
                const data = await response.json();
                if (data && data.categories && data.options_by_category) {
                    return data;
                }
                // Fallback : ancien format dict plat
                if (data && typeof data === "object") {
                    return {
                        categories: Object.keys(data),
                        options_by_category: data,
                    };
                }
            } catch (e) {
                console.error("[Orion4d] Erreur API Dropdowns :", e);
            }
            return { categories: [], options_by_category: {} };
        };

        dropdownData = await loadDropdowns();

        // ─── Widgets natifs ─────────────────────────────────────────────
        const categoryWidget = node.widgets.find((w) => w.name === "category");
        const valueWidget    = node.widgets.find((w) => w.name === "value");

        if (!categoryWidget || !valueWidget) return;

        // Masquer le widget STRING natif (il reste dans node.widgets pour
        // la sérialisation, mais n'est plus dessiné)
        valueWidget.hidden = true;
        valueWidget.computeSize = () => [0, -4];

        // ─── Création du <select> HTML stylé ────────────────────────────
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
        label.textContent = "value";
        label.style.cssText = `
            font-size: 12px;
            color: #aaa;
            flex-shrink: 0;
            min-width: 60px;
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

        // addDOMWidget injecte un widget DOM dans le node
        node.addDOMWidget("value_select", "div", container, {
            serialize: false,  // ne pas re-sérialiser : c'est valueWidget qui porte la valeur
        });

        // ─── Logique de filtrage ────────────────────────────────────────
        const refreshSelect = (preserveValue) => {
            const cat = categoryWidget.value;
            const opts = dropdownData.options_by_category[cat] || [];

            // Reset
            select.innerHTML = "";

            if (opts.length === 0) {
                const o = document.createElement("option");
                o.value = "";
                o.textContent = "(aucune option)";
                o.disabled = true;
                select.appendChild(o);
                select.value = "";
                valueWidget.value = "";
                node.setDirtyCanvas(true, false);
                return;
            }

            opts.forEach((opt) => {
                const o = document.createElement("option");
                o.value = opt;
                o.textContent = opt;
                select.appendChild(o);
            });

            // Préserver la sélection si elle existe encore dans la nouvelle catégorie
            if (preserveValue && opts.includes(valueWidget.value)) {
                select.value = valueWidget.value;
            } else {
                select.value = opts[0];
                valueWidget.value = opts[0];
            }
            node.setDirtyCanvas(true, false);
        };

        // Écriture dans le widget STRING sous-jacent à chaque changement
        select.addEventListener("change", () => {
            valueWidget.value = select.value;
            node.setDirtyCanvas(true, false);
        });

        // Empêcher les keydown du <select> de remonter au canvas ComfyUI
        // (sinon les flèches haut/bas déplacent le node au lieu de naviguer)
        select.addEventListener("keydown", (e) => e.stopPropagation());

        // ─── Bouton Refresh ─────────────────────────────────────────────
        node.addWidget("button", "🔄 Actualiser les listes", null, async () => {
            dropdownData = await loadDropdowns();

            // Si la catégorie courante n'existe plus, retomber sur la première
            if (!dropdownData.categories.includes(categoryWidget.value)) {
                categoryWidget.options.values = dropdownData.categories.length
                    ? dropdownData.categories
                    : ["(aucun_fichier)"];
                categoryWidget.value = categoryWidget.options.values[0];
            } else {
                categoryWidget.options.values = dropdownData.categories;
            }
            refreshSelect(true);
            node.setDirtyCanvas(true, true);
        });

        // ─── Hook sur changement de catégorie ───────────────────────────
        const prevCallback = categoryWidget.callback;
        categoryWidget.callback = function () {
            if (prevCallback) prevCallback.apply(this, arguments);
            // À chaque changement de catégorie, on RESET la sélection
            // (l'ancienne valeur n'a probablement aucun sens dans la nouvelle catégorie)
            refreshSelect(false);
        };

        // ─── État initial ───────────────────────────────────────────────
        // On préserve la valeur déjà présente dans valueWidget si elle est
        // valide pour la catégorie courante (cas chargement de workflow)
        refreshSelect(true);
    },
});
// --- END OF FILE master_combo.js ---
