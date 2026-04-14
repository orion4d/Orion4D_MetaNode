// --- START OF FILE List_selector_max.js ---
// List Selector Max - Orion4D_MetaNode
// Corrections v2 :
//  - Path = dossier courant (éditable), fichier sélectionné affiché en lecture seule dessous
//  - Séparateur par groupe (remplace global), accepte tous chars dont \n
//  - Suppression groups_json exposé → state transmis via widget caché lsm_state_json
//  - Pli/dépli des réglages par groupe (body collapse)
//  - Renommé List Selector Max
"use strict";

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const NODE_TYPE = "PyCodeMax_ListSelectorMax";

// ─────────────────────────────────────────────
// CSS global (injecté une seule fois)
// ─────────────────────────────────────────────
function ensureCSS() {
    if (document.getElementById("lsm-style")) return;
    const s = document.createElement("style");
    s.id = "lsm-style";
    s.textContent = `
.lsm-root {
    width:100%; box-sizing:border-box;
    display:flex; flex-direction:column; gap:6px;
    padding:6px; font-family:Arial,Helvetica,sans-serif;
    color:#ccc; font-size:12px; user-select:none;
}

/* ── Preview ── */
.lsm-preview-label {
    opacity:.6; font-size:10px; margin-bottom:1px;
    cursor:pointer; display:flex; align-items:center; gap:4px;
    user-select:none;
}
.lsm-preview-label .lsm-tri {
    display:inline-block; transition:transform .2s; font-size:9px;
}
.lsm-preview-label.open .lsm-tri { transform:rotate(90deg); }
.lsm-preview-wrap { display:flex; flex-direction:column; gap:2px; }
.lsm-preview-wrap.collapsed { display:none; }
.lsm-preview {
    background:#111; border:1px solid #2a2a2a; border-radius:8px;
    padding:6px 10px; font-size:11px; color:#8cf;
    min-height:40px; word-break:break-all; white-space:pre-wrap;
    resize:vertical; font-family:inherit; width:100%; box-sizing:border-box;
    outline:none;
}
.lsm-preview.overridden { border-color:#5c7a3c; color:#bef5cb; }
.lsm-preview-reset {
    align-self:flex-end; background:none; border:1px solid #3a4a2a;
    border-radius:5px; color:#5cb87a; font-size:10px; padding:1px 7px;
    cursor:pointer; display:none;
}
.lsm-preview-reset.visible { display:block; }
.lsm-preview-reset:hover { background:#1e3a22; }

/* ── Panneau Réglages globaux ── */
.lsm-settings-bar {
    background:#1a1a1a; border:1px solid #2e2e2e; border-radius:8px;
    overflow:hidden;
}
.lsm-settings-header {
    display:flex; align-items:center; gap:6px;
    padding:5px 10px; cursor:pointer; user-select:none;
}
.lsm-settings-header:hover { background:#222; }
.lsm-settings-tri {
    font-size:9px; opacity:.6; transition:transform .2s; display:inline-block;
}
.lsm-settings-tri.open { transform:rotate(90deg); }
.lsm-settings-title { font-size:11px; opacity:.6; flex:1; }
.lsm-settings-body {
    padding:7px 10px; display:flex; flex-direction:column; gap:5px;
    border-top:1px solid #2a2a2a;
}
.lsm-settings-body.collapsed { display:none; }
.lsm-root-row { display:flex; align-items:center; gap:5px; }
.lsm-root-row label { font-size:10px; opacity:.6; white-space:nowrap; }
.lsm-root-input {
    flex:1; background:#242424; border:1px solid #3a3a3a;
    border-radius:5px; color:#ccc; padding:3px 7px; font-size:11px; outline:none;
    min-width:0; font-family:monospace;
}
.lsm-root-input:focus { border-color:#555; }
.lsm-root-input.invalid { border-color:#7a3c3c; color:#f99; }
.lsm-root-reset {
    background:none; border:1px solid #3a3a3a; border-radius:5px;
    color:#888; font-size:10px; padding:2px 7px; cursor:pointer; white-space:nowrap;
    flex-shrink:0;
}
.lsm-root-reset:hover { border-color:#555; color:#ccc; }
.lsm-root-info { font-size:10px; opacity:.45; font-style:italic; line-height:1.5; }
.lsm-root-info code {
    font-style:normal; font-family:monospace; font-size:10px;
    background:#2a2a2a; border:1px solid #3a3a3a; border-radius:3px;
    padding:0 3px; color:#8cf; opacity:1;
}

/* ── Verrou de navigation ── */
.lsm-lock-row { display:flex; align-items:center; gap:5px; padding-top:3px; border-top:1px solid #242424; }
.lsm-lock-row label { font-size:10px; opacity:.6; white-space:nowrap; }
.lsm-lock-toggle {
    background:none; border:none; cursor:pointer; font-size:15px;
    padding:0 2px; line-height:1; flex-shrink:0; opacity:.6;
    transition:opacity .15s, transform .15s;
}
.lsm-lock-toggle:hover { opacity:1; }
.lsm-lock-toggle.enabled { opacity:1; transform:scale(1.1); }
.lsm-lock-input {
    flex:1; background:#242424; border:1px solid #3a3a3a;
    border-radius:5px; color:#ccc; padding:3px 7px; font-size:11px; outline:none;
    min-width:0; font-family:monospace;
}
.lsm-lock-input:focus { border-color:#555; }
.lsm-lock-input.has-value { border-color:#3c7a52; }
.lsm-lock-input.enabled  { background:#1a2e22; color:#bef5cb; border-color:#5cb87a; }
.lsm-lock-clear {
    background:none; border:1px solid #3a3a3a; border-radius:5px;
    color:#888; font-size:10px; padding:2px 7px; cursor:pointer; white-space:nowrap;
    flex-shrink:0;
}
.lsm-lock-clear:hover { border-color:#555; color:#ccc; }

/* ── Add button ── */
.lsm-add-btn {
    background:#1e3a28; border:1px dashed #3c7a52; border-radius:8px;
    color:#5cb87a; padding:6px; text-align:center; cursor:pointer;
    font-size:13px; transition:background .15s;
}
.lsm-add-btn:hover { background:#243d2e; }

/* ── Group card ── */
.lsm-group {
    background:#1e1e1e; border:1px solid #333; border-radius:10px;
    overflow:hidden; transition:border-color .15s;
}
.lsm-group.lsm-drag-over { border-color:#00ffc9; }
.lsm-group.lsm-dragging  { opacity:.4; }
.lsm-group.lsm-disabled  { opacity:.4; }

/* ── Header ── */
.lsm-header {
    display:flex; align-items:center; gap:5px;
    padding:5px 8px; background:#252525;
}
.lsm-drag-handle {
    opacity:.4; font-size:14px; cursor:grab; flex-shrink:0; padding:0 2px;
}
.lsm-drag-handle:active { cursor:grabbing; }

.lsm-toggle {
    width:28px; height:16px; background:#444; border-radius:8px;
    border:none; cursor:pointer; flex-shrink:0; position:relative;
    transition:background .2s;
}
.lsm-toggle::after {
    content:''; position:absolute; top:2px; left:2px;
    width:12px; height:12px; border-radius:50%;
    background:#ccc; transition:transform .2s, background .2s;
}
.lsm-toggle.on { background:#3c7a52; }
.lsm-toggle.on::after { transform:translateX(12px); background:#fff; }

.lsm-label-input {
    flex:1; background:transparent; border:none; border-bottom:1px solid transparent;
    color:#ddd; font-size:12px; outline:none; cursor:text; min-width:0;
}
.lsm-label-input:focus { border-bottom-color:#555; }

/* Bouton collapse ▸/▾ */
.lsm-collapse-btn {
    background:none; border:none; color:#888; cursor:pointer;
    font-size:13px; padding:0 3px; line-height:1; flex-shrink:0;
    transition:transform .2s;
}
.lsm-collapse-btn.open { transform:rotate(90deg); }

.lsm-remove-btn {
    background:none; border:none; color:#855; cursor:pointer;
    font-size:14px; padding:0 2px; line-height:1; flex-shrink:0;
}
.lsm-remove-btn:hover { color:#f66; }

/* ── Body (collapsible) ── */
.lsm-body {
    padding:7px 8px; display:flex; flex-direction:column; gap:6px;
    overflow:hidden;
}
.lsm-body.collapsed { display:none; }

/* ── Path section ── */
.lsm-path-row {
    display:flex; align-items:center; gap:4px;
}
.lsm-path-input {
    flex:1; background:#2a2a2a; border:1px solid #444;
    border-radius:6px; color:#ddd; padding:4px 7px; font-size:11px; outline:none;
    min-width:0;
}
.lsm-path-input:focus { border-color:#666; }
.lsm-path-btn {
    background:#2d2d2d; border:1px solid #444; border-radius:6px;
    color:#aaa; padding:4px 7px; cursor:pointer; font-size:11px;
    white-space:nowrap; flex-shrink:0;
}
.lsm-path-btn:hover { background:#383838; color:#ddd; }

/* Affichage du fichier sélectionné (read-only) */
.lsm-file-display {
    font-size:10px; color:#5cb87a; opacity:.8;
    padding:1px 4px; white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; font-style:italic;
}
.lsm-file-display:empty { display:none; }

/* ── Tree ── */
.lsm-tree {
    background:#161616; border-radius:7px; max-height:150px;
    overflow-y:auto; display:none; flex-direction:column;
    border:1px solid #2a2a2a;
}
.lsm-tree.open { display:flex; }
.lsm-tree-item {
    display:flex; align-items:center; gap:5px;
    padding:3px 8px; cursor:pointer; font-size:11px;
    border-bottom:1px solid #1a1a1a;
}
.lsm-tree-item:last-child { border-bottom:none; }
.lsm-tree-item:hover { background:#222; }
.lsm-tree-up  { color:#888; font-style:italic; }
.lsm-tree-dir  { color:#88aaee; }
.lsm-tree-file { color:#ccc; }
.lsm-tree-file.selected { color:#5cb87a; background:#1a2e22; }

/* ── Seed row ── */
.lsm-seed-row {
    display:flex; align-items:center; gap:5px; flex-wrap:wrap;
}
.lsm-seed-row label { opacity:.6; font-size:11px; white-space:nowrap; }
.lsm-seed-mode {
    background:#2a2a2a; border:1px solid #444; border-radius:5px;
    color:#ccc; padding:2px 5px; font-size:11px;
}
.lsm-seed-val {
    width:80px; background:#2a2a2a; border:1px solid #444;
    border-radius:5px; color:#ccc; padding:2px 6px; font-size:11px; text-align:right;
}
.lsm-seed-dice {
    background:none; border:1px solid #444; border-radius:5px;
    color:#aaa; padding:1px 6px; cursor:pointer; font-size:13px;
}
.lsm-seed-dice:hover { border-color:#777; color:#ddd; }

/* ── Lines list ── */
.lsm-lines {
    background:#161616; border-radius:7px; max-height:160px;
    overflow-y:auto; display:flex; flex-direction:column;
    border:1px solid #222;
}
.lsm-line-item {
    display:flex; align-items:center; padding:3px 8px;
    cursor:pointer; font-size:11px; border-bottom:1px solid #1e1e1e; gap:5px;
}
.lsm-line-item:last-child { border-bottom:none; }
.lsm-line-item:hover { background:#1e2a20; }
.lsm-line-item:focus { outline:none; background:#1e2a20; }
.lsm-line-item.selected { background:#1a2e22; border-left:3px solid #5cb87a; }
.lsm-lines:focus { outline:none; }
.lsm-line-idx { color:#555; min-width:20px; text-align:right; font-size:10px; flex-shrink:0; }
.lsm-line-text { flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lsm-line-edit {
    flex:1; background:#1a2e22; border:1px solid #3c7a52;
    border-radius:4px; color:#bef5cb; padding:2px 5px;
    font-size:11px; outline:none;
}
.lsm-empty { color:#555; font-size:11px; padding:6px 8px; }

/* ── Separator ── */
.lsm-sep-row { display:flex; align-items:center; gap:5px; }
.lsm-sep-row label { opacity:.55; font-size:10px; white-space:nowrap; }
.lsm-sep-input {
    flex:1; background:#1e1e1e; border:1px solid #333;
    border-radius:5px; color:#ccc; padding:3px 7px; font-size:11px;
    resize:none; min-height:28px; font-family:monospace;
}
`;
    document.head.appendChild(s);
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
function randSeed() { return Math.floor(Math.random() * 2147483647); }
function escHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** Debounce : regroupe les appels rapides en un seul après `delay` ms. */
function debounce(fn, delay = 300) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}
function makeGroup(overrides = {}) {
    const idx = overrides.index ?? 0;
    return {
        id: Date.now() + Math.random(),
        label: "List " + (idx + 1),
        enabled: true,
        collapsed: false,
        dir_path: "",       // dossier courant (éditable)
        file_path: "",      // fichier sélectionné (readonly)
        lines: [],
        selected_index: 0,
        edited_line: "",
        seed_mode: "select",
        seed: randSeed(),
        separator: ", ",
        ...overrides,
    };
}

// Résolution côté JS (pour preview)
function resolveGroupLine(g) {
    if (!g.lines.length) return "";
    const edited = (g.edited_line ?? "").trim();
    if (edited) return edited;
    let idx = g.selected_index ?? 0;
    const n = g.lines.length;
    if (g.seed_mode === "randomize") {
        const s = Math.abs(g.seed ?? 0);
        idx = ((s * 1664525 + 1013904223) >>> 0) % n;
    } else if (g.seed_mode === "increment") {
        idx = (g.seed ?? 0) % n;
    } else if (g.seed_mode === "decrement") {
        idx = (n - 1 - ((g.seed ?? 0) % n));
    } else {
        idx = Math.max(0, Math.min(idx, n - 1));
    }
    return g.lines[idx] ?? "";
}

// ─────────────────────────────────────────────
// API helpers
// ─────────────────────────────────────────────
async function apiListDir(path, customRoot = "") {
    const params = new URLSearchParams({ path });
    if (customRoot) params.set("root", customRoot);
    const res = await api.fetchApi("/orion4d/lsm/list_dir?" + params.toString());
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
}
async function apiReadFile(path, customRoot = "") {
    const params = new URLSearchParams({ path });
    if (customRoot) params.set("root", customRoot);
    const res = await api.fetchApi("/orion4d/lsm/read_file?" + params.toString());
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
}

// ─────────────────────────────────────────────
// Extension
// ─────────────────────────────────────────────
app.registerExtension({
    name: "Orion4d.ListSelectorMax",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!nodeData || nodeData.name !== NODE_TYPE) return;

        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onCreated) onCreated.apply(this, arguments);
            try { ensureCSS(); initNode.call(this); }
            catch (e) { console.error("[LSM] init error:", e); }
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) onConfigure.apply(this, arguments);
            if (this._lsmRestore && this.properties?.lsm_state) {
                try { this._lsmRestore(this.properties.lsm_state); } catch (e) { /**/ }
            }
        };
    },

    setup() {
        if (app.__lsmHooked) return;
        const orig = app.queuePrompt;
        app.queuePrompt = async function () {
            const res = await orig.apply(this, arguments);
            for (const node of app.graph?._nodes ?? []) {
                if (node.type === NODE_TYPE && node._lsmTickSeeds) {
                    try { node._lsmTickSeeds(); } catch (e) { /**/ }
                }
            }
            return res;
        };
        app.__lsmHooked = true;
    },
});

// ─────────────────────────────────────────────
// Init node
// ─────────────────────────────────────────────
function initNode() {
    const node = this;

    // Widget caché pour transporter l'état vers Python
    // On utilise un widget STRING hidden pour stocker le JSON d'état complet
    let wState = node.widgets?.find(w => w.name === "lsm_state_json");
    if (!wState) {
        // Créer dynamiquement un widget caché si non présent
        wState = node.addWidget("text", "lsm_state_json", "{}", () => {}, { hidden: true });
    } else {
        wState.hidden = true;
    }

    // ── State ──
    let groups = [makeGroup({ index: 0 })];
    let customRoot       = "";    // racine personnalisée
    let navLock          = "";    // chemin verrou (token ou absolu)
    let navLockEnabled   = false; // verrou actif ou non (toggle icône)
    let comfyRoot        = "";    // racine ComfyUI récupérée depuis l'API
    let settingsCollapsed = true;

    // ── DOM ──
    const root = document.createElement("div");
    root.className = "lsm-root";
    root.innerHTML = `
        <div class="lsm-settings-bar">
            <div class="lsm-settings-header">
                <span class="lsm-settings-tri">▶</span>
                <span class="lsm-settings-title">⚙ Réglages</span>
            </div>
            <div class="lsm-settings-body collapsed">
                <div class="lsm-root-row">
                    <label>Racine autorisée :</label>
                    <input class="lsm-root-input" type="text" placeholder="Dossier autorisé supplémentaire..."/>
                    <button class="lsm-root-reset" title="Réinitialiser">↺ Défaut</button>
                </div>
                <div class="lsm-root-info">ComfyUI est toujours autorisé. Ce champ ajoute une 2ᵉ racine.<br>Tokens portables : <code>{COMFY}</code> = racine ComfyUI &nbsp;·&nbsp; <code>{CUSTOM}</code> = cette racine</div>
                <div class="lsm-lock-row">
                    <button class="lsm-lock-toggle" title="Activer/désactiver le verrou">🔓</button>
                    <label>Verrou navigation :</label>
                    <input class="lsm-lock-input" type="text" placeholder="ex: {COMFY}/custom_nodes/…/lists"/>
                    <button class="lsm-lock-clear" title="Effacer">✕</button>
                </div>
            </div>
        </div>
        <div class="lsm-preview-label open">
            <span class="lsm-tri">▶</span> Aperçu de la sortie
        </div>
        <div class="lsm-preview-wrap">
            <textarea class="lsm-preview" rows="2" spellcheck="false">—</textarea>
            <button class="lsm-preview-reset" title="Restaurer le calcul automatique">↺ Auto</button>
        </div>
        <div class="lsm-groups-container"></div>
        <div class="lsm-add-btn">＋ Ajouter une liste</div>
    `;
    node.addDOMWidget("lsm_ui", "div", root, {});
    node.size = [460, 560];

    const settingsHeader  = root.querySelector(".lsm-settings-header");
    const settingsTri     = root.querySelector(".lsm-settings-tri");
    const settingsBody    = root.querySelector(".lsm-settings-body");
    const rootInput       = root.querySelector(".lsm-root-input");
    const rootResetBtn    = root.querySelector(".lsm-root-reset");
    const lockToggleBtn   = root.querySelector(".lsm-lock-toggle");
    const lockInput       = root.querySelector(".lsm-lock-input");
    const lockClearBtn    = root.querySelector(".lsm-lock-clear");
    const previewLabel    = root.querySelector(".lsm-preview-label");
    const previewWrap     = root.querySelector(".lsm-preview-wrap");
    const preview         = root.querySelector(".lsm-preview");
    const previewReset    = root.querySelector(".lsm-preview-reset");
    const groupsCont      = root.querySelector(".lsm-groups-container");
    const addBtn          = root.querySelector(".lsm-add-btn");

    // ── Charger la racine ComfyUI depuis l'API (une fois) ──
    api.fetchApi("/orion4d/lsm/comfy_root").then(r => r.json()).then(d => {
        comfyRoot = d.root ?? "";
        // Si aucune racine custom, pré-remplir le placeholder avec ComfyUI
        if (!customRoot) rootInput.placeholder = comfyRoot || "Dossier autorisé supplémentaire...";
    }).catch(() => {});

    // ── Toggle réglages ──
    settingsHeader.addEventListener("click", () => {
        settingsCollapsed = !settingsCollapsed;
        settingsBody.classList.toggle("collapsed", settingsCollapsed);
        settingsTri.classList.toggle("open", !settingsCollapsed);
    });

    // ── Racine custom ──
    rootInput.addEventListener("input", () => {
        customRoot = rootInput.value.trim();
        rootInput.classList.toggle("invalid", customRoot !== "" && !customRoot.match(/^[a-zA-Z:\\\/~]/));
        syncWidgetsDebounced();
    });
    rootResetBtn.addEventListener("click", () => {
        customRoot = "";
        rootInput.value = "";
        rootInput.classList.remove("invalid");
        syncWidgets();
    });

    // ── Verrou de navigation ──
    // resolveLock : convertit le token en chemin absolu, normalise les séparateurs
    function resolveLock() {
        if (!navLock) return "";
        let p = navLock
            .replace(/\{COMFY\}/g, comfyRoot)
            .replace(/\{CUSTOM\}/g, customRoot);
        // Normaliser les slashes selon l'OS (on compare avec des chemins Python)
        return p.replace(/\//g, "\\").replace(/\\+$/, ""); // supprimer slash final
    }

    // isLockedOut : retourne true si dirPath est EN DEHORS du verrou
    // = on ne peut pas naviguer vers ce dossier via ↑
    function isLockedOut(dirPath) {
        if (!navLockEnabled || !navLock) return false;
        const lock = resolveLock();
        if (!lock) return false;
        const norm = (dirPath ?? "").replace(/\//g, "\\").replace(/\\+$/, "");
        // Bloqué si le dossier n'est pas sous le verrou (ni égal)
        return !(norm === lock || norm.startsWith(lock + "\\"));
    }

    // Dossier d'ouverture par défaut du 📁 quand le verrou est actif
    function lockStartDir() {
        if (!navLockEnabled || !navLock) return null;
        return resolveLock() || null;
    }

    // Met à jour l'UI du toggle (icône + champ)
    function updateLockUI() {
        lockToggleBtn.textContent = navLockEnabled ? "🔒" : "🔓";
        lockToggleBtn.classList.toggle("enabled", navLockEnabled);
        lockInput.classList.toggle("enabled", navLockEnabled && navLock !== "");
        lockInput.classList.toggle("has-value", !navLockEnabled && navLock !== "");
    }

    // Toggle on/off via l'icône
    lockToggleBtn.addEventListener("click", () => {
        if (!navLock) return; // rien à verrouiller si le champ est vide
        navLockEnabled = !navLockEnabled;
        updateLockUI();
        syncWidgets();
    });

    // Saisie du chemin verrou
    lockInput.addEventListener("input", () => {
        navLock = lockInput.value.trim();
        // Si on efface le texte, désactiver le verrou automatiquement
        if (!navLock) navLockEnabled = false;
        updateLockUI();
        syncWidgetsDebounced();
    });

    // Effacer
    lockClearBtn.addEventListener("click", () => {
        navLock = "";
        navLockEnabled = false;
        lockInput.value = "";
        updateLockUI();
        syncWidgets();
    });

    // ── Preview override state ──
    let previewOverride  = "";
    let previewCollapsed = false;

    // Toggle collapse preview
    previewLabel.addEventListener("click", () => {
        previewCollapsed = !previewCollapsed;
        previewWrap.classList.toggle("collapsed", previewCollapsed);
        previewLabel.classList.toggle("open", !previewCollapsed);
    });

    // Edition manuelle du preview → override
    preview.addEventListener("input", () => {
        previewOverride = preview.value;
        preview.classList.add("overridden");
        previewReset.classList.add("visible");
        syncWidgetsDebounced();
    });
    // Ne pas laisser les clicks sur la textarea remonter à ComfyUI
    preview.addEventListener("mousedown", e => e.stopPropagation());

    // Reset override → retour calcul auto
    previewReset.addEventListener("click", () => {
        previewOverride = "";
        preview.classList.remove("overridden");
        previewReset.classList.remove("visible");
        updatePreview();
        syncWidgets();
    });

    // ── Sync → Python ──
    // syncWidgets() : immédiat — pour les actions structurelles (ajout groupe,
    //   sélection ligne, toggle, drag-drop…) qui doivent être persistées tout de suite.
    // syncWidgetsDebounced() : différé 300 ms — pour les frappes clavier
    //   (édition de ligne, label, séparateur, preview override) afin d'éviter
    //   50 redessins du canvas pour 50 caractères tapés.
    function syncWidgets() {
        const state = { groups, previewOverride, previewCollapsed, customRoot, navLock, navLockEnabled, settingsCollapsed };
        if (wState) wState.value = JSON.stringify(state);
        node.properties = node.properties || {};
        node.properties.lsm_state = state;
        updatePreview();
        node.setDirtyCanvas(true, true);
    }
    const syncWidgetsDebounced = debounce(syncWidgets, 300);

    function updatePreview() {
        // Si override manuel actif, ne pas écraser
        if (previewOverride !== "") return;
        const parts = [];
        const seps  = [];
        for (const g of groups) {
            if (!g.enabled || !g.lines.length) continue;
            parts.push(resolveGroupLine(g));
            seps.push((g.separator ?? ", ").replace(/\\n/g, "\n").replace(/\\t/g, "\t"));
        }
        const out = parts.length
            ? parts.reduce((acc, p, i) => acc + (i === 0 ? "" : seps[i - 1]) + p, "")
            : "—";
        preview.value = out;
    }

    // ── Add group ──
    addBtn.addEventListener("click", () => {
        groups.push(makeGroup({ index: groups.length }));
        renderGroups();
        syncWidgets();
    });

    // ── Drag state ──
    let dragSrcIdx = null;

    // ─────────────────────────────────────────
    // Render all groups
    // ─────────────────────────────────────────
    function renderGroups() {
        groupsCont.innerHTML = "";
        groups.forEach((g, i) => groupsCont.appendChild(buildCard(g, i)));
        updatePreview();
    }

    // ─────────────────────────────────────────
    // Build one group card
    // ─────────────────────────────────────────
    function buildCard(g, idx) {
        const card = document.createElement("div");
        card.className = "lsm-group" + (g.enabled ? "" : " lsm-disabled");

        // ── Header ──
        const header = document.createElement("div");
        header.className = "lsm-header";
        header.innerHTML = `
            <span class="lsm-drag-handle" draggable="true">⠿</span>
            <button class="lsm-toggle ${g.enabled ? "on" : ""}" title="Activer/Désactiver"></button>
            <input class="lsm-label-input" type="text" value="${escHtml(g.label)}" placeholder="Nom"/>
            <button class="lsm-collapse-btn ${g.collapsed ? "" : "open"}" title="Replier/Déplier">▸</button>
            <button class="lsm-remove-btn" title="Supprimer">✕</button>
        `;
        card.appendChild(header);

        // ── Body ──
        const body = document.createElement("div");
        body.className = "lsm-body" + (g.collapsed ? " collapsed" : "");

        // Path row (dossier courant éditable)
        const pathRow = document.createElement("div");
        pathRow.className = "lsm-path-row";
        pathRow.innerHTML = `
            <input class="lsm-path-input" type="text"
                value="${escHtml(g.dir_path)}"
                placeholder="Dossier..."/>
            <button class="lsm-path-btn lsm-btn-up" title="Remonter">↑</button>
            <button class="lsm-path-btn lsm-btn-browse" title="Parcourir">📁</button>
            <button class="lsm-path-btn lsm-btn-go" title="Aller">→</button>
        `;

        // Fichier sélectionné (read-only)
        const fileDisplay = document.createElement("div");
        fileDisplay.className = "lsm-file-display";
        fileDisplay.textContent = g.file_path ? "📄 " + g.file_path.split(/[\\/]/).pop() : "";
        fileDisplay.title = g.file_path || "";

        // Tree
        const tree = document.createElement("div");
        tree.className = "lsm-tree";

        // Seed row
        const seedRow = document.createElement("div");
        seedRow.className = "lsm-seed-row";
        seedRow.innerHTML = `
            <label>Seed :</label>
            <select class="lsm-seed-mode">
                <option value="select"    ${g.seed_mode === "select"    ? "selected":""}>Manuel</option>
                <option value="randomize" ${g.seed_mode === "randomize" ? "selected":""}>Aléatoire</option>
                <option value="increment" ${g.seed_mode === "increment" ? "selected":""}>Incrément</option>
                <option value="decrement" ${g.seed_mode === "decrement" ? "selected":""}>Décrément</option>
            </select>
            <input class="lsm-seed-val" type="number" min="0" max="2147483647" value="${g.seed ?? 0}"/>
            <button class="lsm-seed-dice" title="Nouveau seed">🎲</button>
        `;

        // Lines
        const linesDiv = document.createElement("div");
        linesDiv.className = "lsm-lines";

        // Separator (par groupe, remplace global)
        const sepRow = document.createElement("div");
        sepRow.className = "lsm-sep-row";
        sepRow.innerHTML = `<label>Séparateur :</label>`;
        const sepInput = document.createElement("textarea");
        sepInput.className = "lsm-sep-input";
        sepInput.rows = 1;
        sepInput.value = g.separator ?? ", ";
        sepInput.placeholder = "ex: ,   \\n   — ";
        sepRow.appendChild(sepInput);

        body.appendChild(pathRow);
        body.appendChild(fileDisplay);
        body.appendChild(tree);
        body.appendChild(seedRow);
        body.appendChild(linesDiv);
        body.appendChild(sepRow);
        card.appendChild(body);

        // ── Refs ──
        const pathInput   = pathRow.querySelector(".lsm-path-input");
        const btnUp       = pathRow.querySelector(".lsm-btn-up");
        const btnBrowse   = pathRow.querySelector(".lsm-btn-browse");
        const btnGo       = pathRow.querySelector(".lsm-btn-go");
        const toggleBtn   = header.querySelector(".lsm-toggle");
        const labelInput  = header.querySelector(".lsm-label-input");
        const collapseBtn = header.querySelector(".lsm-collapse-btn");
        const removeBtn   = header.querySelector(".lsm-remove-btn");
        const seedMode    = seedRow.querySelector(".lsm-seed-mode");
        const seedVal     = seedRow.querySelector(".lsm-seed-val");
        const diceBtn     = seedRow.querySelector(".lsm-seed-dice");

        // ── Render lines ──
        // • 1 clic  → sélectionne la ligne
        // • 2 clics → active l'édition inline
        // • clavier → lettre = jump alpha, ↑/↓ = navigation
        function renderLines(focusAfter = false) {
            linesDiv.innerHTML = "";
            if (!g.lines.length) {
                const em = document.createElement("div");
                em.className = "lsm-empty";
                em.textContent = "Sélectionner un fichier ci-dessus";
                linesDiv.appendChild(em);
                return;
            }

            g.lines.forEach((line, li) => {
                const item = document.createElement("div");
                item.className = "lsm-line-item" + (li === g.selected_index ? " selected" : "");
                item.tabIndex = li === g.selected_index ? 0 : -1;
                item.dataset.li = li;

                const idxEl = document.createElement("span");
                idxEl.className = "lsm-line-idx";
                idxEl.textContent = li + 1;
                item.appendChild(idxEl);

                // Ligne en édition (double-clic sur la ligne sélectionnée)
                if (li === g.selected_index && g._editing) {
                    const inp = document.createElement("input");
                    inp.type = "text";
                    inp.className = "lsm-line-edit";
                    inp.value = g.edited_line !== "" ? g.edited_line : line;
                    inp.placeholder = line;
                    inp.addEventListener("input", () => { g.edited_line = inp.value; syncWidgetsDebounced(); });
                    inp.addEventListener("mousedown", e => e.stopPropagation());
                    inp.addEventListener("keydown", e => {
                        if (e.key === "Escape") { g._editing = false; renderLines(true); }
                        if (e.key === "Enter")  { g._editing = false; renderLines(true); syncWidgets(); }
                        e.stopPropagation();
                    });
                    item.appendChild(inp);
                    setTimeout(() => { inp.focus(); inp.select(); }, 0);
                } else {
                    const txt = document.createElement("span");
                    txt.className = "lsm-line-text";
                    txt.textContent = line;
                    item.appendChild(txt);
                }

                // 1 clic → sélection
                item.addEventListener("click", () => {
                    if (li !== g.selected_index) {
                        g.selected_index = li;
                        g.edited_line = "";
                        g._editing = false;
                        renderLines(true);
                        syncWidgets();
                    }
                });

                // Double-clic → édition
                item.addEventListener("dblclick", e => {
                    e.stopPropagation();
                    if (li !== g.selected_index) {
                        g.selected_index = li;
                        g.edited_line = "";
                    }
                    g._editing = true;
                    renderLines();
                });

                linesDiv.appendChild(item);
            });

            // Focus sur la ligne sélectionnée après rendu
            if (focusAfter) {
                const sel = linesDiv.querySelector(".lsm-line-item.selected");
                if (sel) { sel.focus(); sel.scrollIntoView({ block: "nearest" }); }
            }
        }

        // ── Clavier sur la liste ──
        let _alphaTimer = null;
        let _alphaBuffer = "";
        linesDiv.addEventListener("keydown", e => {
            if (!g.lines.length) return;
            // Flèche bas
            if (e.key === "ArrowDown") {
                e.preventDefault();
                const next = Math.min(g.selected_index + 1, g.lines.length - 1);
                if (next !== g.selected_index) {
                    g.selected_index = next; g.edited_line = ""; g._editing = false;
                    renderLines(true); syncWidgets();
                }
                return;
            }
            // Flèche haut
            if (e.key === "ArrowUp") {
                e.preventDefault();
                const prev = Math.max(g.selected_index - 1, 0);
                if (prev !== g.selected_index) {
                    g.selected_index = prev; g.edited_line = ""; g._editing = false;
                    renderLines(true); syncWidgets();
                }
                return;
            }
            // Enter → activer édition
            if (e.key === "Enter") {
                e.preventDefault();
                g._editing = true; renderLines(); return;
            }
            // Lettre → recherche alphabétique (buffer + timeout 600ms)
            if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                e.preventDefault();
                _alphaBuffer += e.key.toLowerCase();
                clearTimeout(_alphaTimer);
                _alphaTimer = setTimeout(() => { _alphaBuffer = ""; }, 600);
                // Chercher à partir de la ligne suivante (rotation)
                const n = g.lines.length;
                for (let k = 1; k <= n; k++) {
                    const candidate = (g.selected_index + k) % n;
                    if (g.lines[candidate].toLowerCase().startsWith(_alphaBuffer)) {
                        g.selected_index = candidate; g.edited_line = ""; g._editing = false;
                        renderLines(true); syncWidgets(); return;
                    }
                }
                // Pas trouvé avec le buffer entier → essayer juste la dernière lettre
                const single = e.key.toLowerCase();
                if (single !== _alphaBuffer) {
                    for (let k = 1; k <= n; k++) {
                        const candidate = (g.selected_index + k) % n;
                        if (g.lines[candidate].toLowerCase().startsWith(single)) {
                            g.selected_index = candidate; g.edited_line = ""; g._editing = false;
                            _alphaBuffer = single;
                            renderLines(true); syncWidgets(); return;
                        }
                    }
                }
            }
        });
        // Permettre le focus sur le div (pour recevoir les events clavier)
        linesDiv.tabIndex = 0;

        renderLines();

        // ── Load file ──
        // filePath peut être un chemin absolu (depuis l'arbre) ou un token {COMFY}/...
        // On stocke toujours le token dans g.file_path pour la portabilité.
        async function loadFile(filePath) {
            try {
                const data = await apiReadFile(filePath, customRoot);
                // Stocker le token (ex: {COMFY}/custom_nodes/.../Lists/style.txt)
                g.file_path = data.path_token ?? filePath;
                g.lines = data.lines ?? [];
                g.selected_index = 0;
                g.edited_line = "";
                const displayName = g.file_path.split(/[\\/]/).pop();
                fileDisplay.textContent = "📄 " + displayName;
                fileDisplay.title = g.file_path;
                // Marquer dans l'arbre (comparaison sur path absolu)
                tree.querySelectorAll(".lsm-tree-file").forEach(el => {
                    el.classList.toggle("selected", el.dataset.path === filePath);
                });
                renderLines();
                syncWidgets();
            } catch (e) {
                linesDiv.innerHTML = `<div class="lsm-empty" style="color:#f77">Erreur : ${e.message}</div>`;
            }
        }

        // ── Open tree ──
        async function openTree(dirPath) {
            tree.innerHTML = '<div class="lsm-empty">Chargement…</div>';
            tree.classList.add("open");
            try {
                const data = await apiListDir(dirPath, customRoot);
                tree.innerHTML = "";

                // Stocker le token du dossier (portable), afficher le token dans le champ
                g.dir_path = data.current_token ?? data.current;
                pathInput.value = g.dir_path;

                // ── Bouton parent ──
                // Bloqué si le dossier parent sortirait du verrou de navigation
                if (data.parent) {
                    const parentBlocked = isLockedOut(data.parent);
                    const up = document.createElement("div");
                    up.className = "lsm-tree-item lsm-tree-up";
                    if (parentBlocked) {
                        up.textContent = "🔒 ..";
                        up.style.cssText = "opacity:.3; cursor:not-allowed;";
                        up.title = `Navigation verrouillée à : ${navLock}`;
                    } else {
                        up.textContent = "↑ ..";
                        up.addEventListener("click", () => openTree(data.parent));
                    }
                    tree.appendChild(up);
                }

                (data.dirs ?? []).forEach(d => {
                    const item = document.createElement("div");
                    item.className = "lsm-tree-item lsm-tree-dir";
                    item.textContent = "📁 " + d.name;
                    // Naviguer avec le chemin absolu (plus fiable), stocker le token
                    item.addEventListener("click", () => openTree(d.path));
                    tree.appendChild(item);
                });

                (data.files ?? []).forEach(f => {
                    const item = document.createElement("div");
                    item.className = "lsm-tree-item lsm-tree-file";
                    item.dataset.path = f.path; // absolu pour la sélection visuelle
                    // Marquer si ce fichier est déjà sélectionné (comparaison sur token)
                    if ((f.path_token ?? f.path) === g.file_path) item.classList.add("selected");
                    item.textContent = (f.ext === ".csv" ? "📊 " : "📄 ") + f.name;
                    item.addEventListener("click", () => loadFile(f.path));
                    tree.appendChild(item);
                });

                if (!data.dirs.length && !data.files.length) {
                    tree.innerHTML = '<div class="lsm-empty">Dossier vide (aucun .txt/.csv)</div>';
                }

                syncWidgets();
            } catch (e) {
                tree.innerHTML = `<div class="lsm-empty" style="color:#f77">Erreur : ${e.message}</div>`;
            }
        }

        // ── Path interactions ──
        btnBrowse.addEventListener("click", () => {
            if (tree.classList.contains("open")) { tree.classList.remove("open"); return; }
            // Priorité : dossier du fichier déjà sélectionné → verrou → courant → comfyRoot
            let start;
            if (g.file_path) {
                // Retrouver le dossier parent du fichier sélectionné
                const parts = g.file_path.split(/[\\/]/);
                parts.pop();
                start = parts.join("/") || lockStartDir() || comfyRoot || "~";
            } else {
                start = lockStartDir() || pathInput.value.trim() || comfyRoot || "~";
            }
            openTree(start);
        });
        btnGo.addEventListener("click", () => {
            const p = pathInput.value.trim();
            if (!p) return;
            if (/\.(txt|csv)$/i.test(p)) loadFile(p);
            else openTree(p);
        });
        btnUp.addEventListener("click", async () => {
            const p = pathInput.value.trim() || g.dir_path || comfyRoot || "~";
            try {
                const data = await apiListDir(p, customRoot);
                if (data.parent && !isLockedOut(data.parent)) openTree(data.parent);
            } catch (e) { /**/ }
        });
        pathInput.addEventListener("change", () => {
            g.dir_path = pathInput.value;
            syncWidgets();
        });
        pathInput.addEventListener("keydown", e => {
            if (e.key !== "Enter") return;
            const p = pathInput.value.trim();
            if (/\.(txt|csv)$/i.test(p)) loadFile(p);
            else openTree(p);
        });

        // ── Collapse ──
        collapseBtn.addEventListener("click", e => {
            e.stopPropagation();
            g.collapsed = !g.collapsed;
            body.classList.toggle("collapsed", g.collapsed);
            collapseBtn.classList.toggle("open", !g.collapsed);
            syncWidgets();
        });

        // ── Toggle enable ──
        toggleBtn.addEventListener("click", () => {
            g.enabled = !g.enabled;
            toggleBtn.classList.toggle("on", g.enabled);
            card.classList.toggle("lsm-disabled", !g.enabled);
            syncWidgets();
        });

        // ── Label ──
        labelInput.addEventListener("input", () => { g.label = labelInput.value; syncWidgetsDebounced(); });

        // ── Remove ──
        removeBtn.addEventListener("click", () => {
            if (groups.length <= 1) return;
            groups.splice(groups.indexOf(g), 1);
            renderGroups();
            syncWidgets();
        });

        // ── Seed ──
        seedMode.addEventListener("change", () => { g.seed_mode = seedMode.value; syncWidgets(); });
        seedVal.addEventListener("input",  () => { g.seed = parseInt(seedVal.value, 10) || 0; syncWidgetsDebounced(); });
        diceBtn.addEventListener("click",  () => { g.seed = randSeed(); seedVal.value = g.seed; syncWidgets(); });

        // ── Separator ──
        sepInput.addEventListener("input", () => { g.separator = sepInput.value; syncWidgetsDebounced(); });

        // ── Drag-and-drop (réordonnement des groupes) ──
        const handle = header.querySelector(".lsm-drag-handle");
        handle.addEventListener("dragstart", e => {
            dragSrcIdx = idx;
            card.classList.add("lsm-dragging");
            e.dataTransfer.effectAllowed = "move";
            e.stopPropagation(); // ne pas interférer avec ComfyUI
        });
        handle.addEventListener("dragend", () => {
            card.classList.remove("lsm-dragging");
            groupsCont.querySelectorAll(".lsm-group").forEach(c => c.classList.remove("lsm-drag-over"));
        });
        card.addEventListener("dragover", e => {
            e.preventDefault(); e.stopPropagation();
            e.dataTransfer.dropEffect = "move";
            groupsCont.querySelectorAll(".lsm-group").forEach(c => c.classList.remove("lsm-drag-over"));
            card.classList.add("lsm-drag-over");
        });
        card.addEventListener("dragleave", () => card.classList.remove("lsm-drag-over"));
        card.addEventListener("drop", e => {
            e.preventDefault(); e.stopPropagation();
            card.classList.remove("lsm-drag-over");
            if (dragSrcIdx === null || dragSrcIdx === idx) return;
            const moved = groups.splice(dragSrcIdx, 1)[0];
            groups.splice(idx, 0, moved);
            dragSrcIdx = null;
            renderGroups();
            syncWidgets();
        });

        return card;
    }

    // ── Tick seeds après génération ──
    node._lsmTickSeeds = () => {
        let changed = false;
        for (const g of groups) {
            if (g.seed_mode === "increment") {
                g.seed = ((g.seed ?? 0) + 1) % 2147483647; changed = true;
            } else if (g.seed_mode === "decrement") {
                g.seed = Math.max(0, (g.seed ?? 0) - 1); changed = true;
            } else if (g.seed_mode === "randomize") {
                g.seed = randSeed(); changed = true;
            }
            // Mettre à jour selected_index pour que la surbrillance suive
            if (changed && g.lines.length && g.seed_mode !== "select") {
                const n = g.lines.length;
                if (g.seed_mode === "randomize") {
                    const s = Math.abs(g.seed ?? 0);
                    g.selected_index = ((s * 1664525 + 1013904223) >>> 0) % n;
                } else if (g.seed_mode === "increment") {
                    g.selected_index = (g.seed ?? 0) % n;
                } else if (g.seed_mode === "decrement") {
                    g.selected_index = (n - 1 - ((g.seed ?? 0) % n));
                }
                g._editing = false; // quitter l'édition si active
            }
        }
        if (changed) { renderGroups(); syncWidgets(); }
    };

    // ── Restauration depuis le workflow ──
    node._lsmRestore = (state) => {
        if (!state?.groups?.length) return;
        groups = state.groups;

        // Racine personnalisée
        customRoot = state.customRoot ?? "";
        rootInput.value = customRoot;
        rootInput.classList.remove("invalid");

        // Verrou de navigation
        navLock = state.navLock ?? "";
        navLockEnabled = state.navLockEnabled ?? false;
        lockInput.value = navLock;
        updateLockUI();

        // Réglages collapse
        settingsCollapsed = state.settingsCollapsed ?? true;
        settingsBody.classList.toggle("collapsed", settingsCollapsed);
        settingsTri.classList.toggle("open", !settingsCollapsed);

        // Override preview
        previewOverride = state.previewOverride ?? "";
        if (previewOverride !== "") {
            preview.value = previewOverride;
            preview.classList.add("overridden");
            previewReset.classList.add("visible");
        } else {
            preview.classList.remove("overridden");
            previewReset.classList.remove("visible");
        }

        // Collapse preview
        previewCollapsed = state.previewCollapsed ?? false;
        previewWrap.classList.toggle("collapsed", previewCollapsed);
        previewLabel.classList.toggle("open", !previewCollapsed);

        renderGroups();
        syncWidgets();
    };

    // ── Init ──
    renderGroups();
    syncWidgets();
}

// --- END OF FILE List_selector_max.js ---