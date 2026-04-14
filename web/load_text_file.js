// --- START OF FILE load_text_file.js ---
// Load Text File - Orion4D_MetaNode  v3
//
// FIX drag & drop : ComfyUI appelle stopPropagation() sur le canvas drop.
// On s'attache sur DOCUMENT en phase CAPTURE (capture:true) pour intercepter
// avant LiteGraph/ComfyUI. On filtre ensuite par position du node.

import { app } from "/scripts/app.js";

const NODE_TYPE = "PyCodeMax_LoadTextFile";

// Drop sur un node existant : tous les formats acceptés, .json inclus
const ALLOWED_EXTS = new Set([
    ".txt", ".json", ".csv", ".py", ".js", ".ts", ".md",
    ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    ".sh", ".bat", ".ini", ".cfg", ".env", ".log"
]);

// Drop sur le canvas vide (création d'un nouveau node) : .json EXCLU
// car ComfyUI intercepte les .json pour charger les workflows.
const CANVAS_DROP_EXTS = new Set([
    ".txt", ".csv", ".py", ".js", ".ts", ".md",
    ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    ".sh", ".bat", ".ini", ".cfg", ".env", ".log"
]);

const EXT_ICONS = {
    ".py":"🐍", ".js":"🟨", ".ts":"🔷", ".json":"📋", ".csv":"📊",
    ".md":"📝", ".txt":"📄", ".html":"🌐", ".css":"🎨",
    ".yaml":"⚙️", ".yml":"⚙️", ".sh":"💻", ".xml":"🔖", ".log":"🗒️",
};

function getExt(f) { return f?.includes(".") ? "." + f.split(".").pop().toLowerCase() : ""; }
function getIcon(f) { return EXT_ICONS[getExt(f)] || "📄"; }
function isAllowed(f) { return ALLOWED_EXTS.has(getExt(f)); }

// ---------------------------------------------------------------------------
// Lecture fichier (côté client, pas d'upload)
// ---------------------------------------------------------------------------
function readFileAsText(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload  = (e) => resolve(e.target.result);
        reader.onerror = () => resolve(null);
        reader.readAsText(file, "utf-8");
    });
}

async function readFileViaServer(file) {
    const fd = new FormData();
    fd.append("file", file);
    try {
        const r = await fetch("/orion4d/read_text_file", { method: "POST", body: fd });
        const d = await r.json();
        if (d.error) throw new Error(d.error);
        return d.content;
    } catch (e) {
        alert("❌ " + e.message);
        return null;
    }
}

async function loadFile(file, node) {
    if (!isAllowed(file.name)) {
        alert(`❌ Extension non supportée : "${getExt(file.name)}"\n\nFormats : ${[...ALLOWED_EXTS].sort().join("  ")}`);
        return false;
    }
    let content = await readFileAsText(file);
    if (content === null) content = await readFileViaServer(file);
    if (content === null) return false;

    const w = node.widgets?.find(w => w.name === "text_content");
    if (w) w.value = content;
    node._ltf_filename = file.name;
    node.title = `📄 ${file.name}`;
    node.setDirtyCanvas(true, true);
    app.graph.setDirtyCanvas(true, false);
    return true;
}

// ---------------------------------------------------------------------------
// Géométrie : point canvas → node ?
// ---------------------------------------------------------------------------
function getNodeAtCanvas(cx, cy) {
    for (const node of (app.graph._nodes || [])) {
        if (node.type !== NODE_TYPE) continue;
        const [nx, ny] = node.pos;
        const [nw, nh] = node.size;
        // tenir compte du zoom et du décalage du graphe
        if (cx >= nx && cx <= nx + nw && cy >= ny && cy <= ny + nh) return node;
    }
    return null;
}

// ---------------------------------------------------------------------------
// Extension
// ---------------------------------------------------------------------------
app.registerExtension({
    name: "Orion4d.LoadTextFile",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;

        // ── onNodeCreated ────────────────────────────────────────────────────
        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (origCreated) origCreated.apply(this, arguments);
            const node = this;
            node.setSize([320, 220]);

            // Bouton Charger
            const btn = node.addWidget("button", "📂  Load a file…", null, () => {
                const inp = document.createElement("input");
                inp.type = "file";
                inp.accept = [...ALLOWED_EXTS].join(",");
                inp.onchange = async (e) => {
                    const f = e.target.files?.[0];
                    if (f) await loadFile(f, node);
                };
                inp.click();
            });
            btn.serialize = false;

            // Bouton Effacer
            const clearBtn = node.addWidget("button", "🗑️  Clear the content", null, () => {
                const w = node.widgets?.find(w => w.name === "text_content");
                if (w) w.value = "";
                node._ltf_filename = null;
                node.title = "📄 Load Text File";
                node.setDirtyCanvas(true, true);
            });
            clearBtn.serialize = false;

            node._ltf_filename = null;
            node._ltf_over     = false;   // highlight drag-over
        };

        // ── onDrawForeground ─────────────────────────────────────────────────
        const origDraw = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            if (origDraw) origDraw.apply(this, arguments);
            if (this.flags?.collapsed) return;

            const W = this.size[0], H = this.size[1];

            if (this._ltf_over) {
                // Highlight drop
                ctx.save();
                ctx.strokeStyle = "#4a9eff";
                ctx.lineWidth = 3;
                ctx.setLineDash([6, 3]);
                ctx.strokeRect(4, 4, W - 8, H - 8);
                ctx.fillStyle = "rgba(74,158,255,0.10)";
                ctx.fillRect(4, 4, W - 8, H - 8);
                ctx.setLineDash([]);
                ctx.font = "bold 14px sans-serif";
                ctx.fillStyle = "#4a9eff";
                ctx.textAlign = "center";
                ctx.fillText("⬇  Déposer ici", W / 2, H / 2);
                ctx.restore();
                return;
            }

            const w = this.widgets?.find(w => w.name === "text_content");
            if (!w?.value && !this._ltf_filename) {
                // Hint zone de drop
                ctx.save();
                ctx.strokeStyle = "rgba(255,255,255,0.13)";
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 4]);
                ctx.strokeRect(12, H - 48, W - 24, 34);
                ctx.setLineDash([]);
                ctx.font = "12px sans-serif";
                ctx.fillStyle = "rgba(255,255,255,0.28)";
                ctx.textAlign = "center";
                ctx.fillText("📂  Glisser-déposer un fichier ici", W / 2, H - 27);
                ctx.restore();
            } else if (this._ltf_filename) {
                // Badge nom fichier
                ctx.save();
                ctx.fillStyle = "rgba(255,255,255,0.05)";
                ctx.strokeStyle = "rgba(255,255,255,0.10)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(10, H - 26, W - 20, 18, 4);
                ctx.fill(); ctx.stroke();
                ctx.font = "10px monospace";
                ctx.fillStyle = "#999";
                ctx.textAlign = "left";
                let disp = getIcon(this._ltf_filename) + "  " + this._ltf_filename;
                while (ctx.measureText(disp).width > W - 32 && disp.length > 5)
                    disp = disp.slice(0, -2) + "…";
                ctx.fillText(disp, 18, H - 13);
                ctx.restore();
            }
        };
    },

    // ── setup : listeners sur document en phase CAPTURE ─────────────────────
    // Phase capture = on arrive AVANT les handlers de ComfyUI/LiteGraph
    // qui sont enregistrés sans capture (phase bubble).
    async setup() {

        // dragover — autoriser le drop quand on survole un node LoadTextFile
        document.addEventListener("dragover", (e) => {
            if (!e.dataTransfer?.types?.includes("Files")) return;

            const pos = app.canvas?.convertEventToCanvasOffset?.(e);
            if (!pos) return;
            const node = getNodeAtCanvas(pos[0], pos[1]);

            if (node) {
                // On est sur notre node : accepter + empêcher le comportement par défaut de ComfyUI
                e.preventDefault();
                e.stopPropagation();
                e.dataTransfer.dropEffect = "copy";
                if (!node._ltf_over) {
                    node._ltf_over = true;
                    app.canvas?.setDirty?.(true);
                }
            } else {
                // Remettre à zéro les highlights
                let changed = false;
                for (const n of (app.graph?._nodes || [])) {
                    if (n.type === NODE_TYPE && n._ltf_over) { n._ltf_over = false; changed = true; }
                }
                if (changed) app.canvas?.setDirty?.(true);
            }
        }, true); // <— CAPTURE

        // dragleave — enlever highlight
        document.addEventListener("dragleave", (e) => {
            // Si on quitte la fenêtre entière
            if (e.relatedTarget === null) {
                let changed = false;
                for (const n of (app.graph?._nodes || [])) {
                    if (n.type === NODE_TYPE && n._ltf_over) { n._ltf_over = false; changed = true; }
                }
                if (changed) app.canvas?.setDirty?.(true);
            }
        }, true);

        // drop — traitement principal
        document.addEventListener("drop", (e) => {
            if (!e.dataTransfer?.files?.length) return;

            const file = e.dataTransfer.files[0];
            if (!isAllowed(file.name)) return; // pas notre affaire

            const pos = app.canvas?.convertEventToCanvasOffset?.(e);
            if (!pos) return;

            const targetNode = getNodeAtCanvas(pos[0], pos[1]);

            // Reset highlights
            for (const n of (app.graph?._nodes || [])) {
                if (n.type === NODE_TYPE) n._ltf_over = false;
            }

            if (targetNode) {
                // Drop sur un node LoadTextFile existant
                e.preventDefault();
                e.stopPropagation();
                loadFile(file, targetNode);
            } else {
                // Drop sur le canvas vide → créer un nouveau node
                // .json exclu : ComfyUI l'utilise pour charger les workflows
                if (!CANVAS_DROP_EXTS.has(getExt(file.name))) return;

                // Vérifier qu'aucun autre node n'est sous le curseur
                const anyNode = app.graph?.getNodeOnPos?.(pos[0], pos[1]);
                if (anyNode) return; // laisser ComfyUI gérer

                e.preventDefault();
                e.stopPropagation();

                const newNode = LiteGraph.createNode(NODE_TYPE);
                if (!newNode) return;
                newNode.pos = [pos[0] - 160, pos[1] - 40];
                app.graph.add(newNode);
                app.canvas?.setDirty?.(true);

                setTimeout(() => loadFile(file, newNode), 200);
            }
        }, true); // <— CAPTURE
    },
});

// --- END OF FILE load_text_file.js ---