// --- START OF FILE folder_file_max.js ---
"use strict";

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

/* ---------- Lightbox (image/vidéo/audio) ---------- */
function ensureLightbox() {
  let el = document.getElementById("ffp-lightbox");
  if (el) return;
  el = document.createElement("div");
  el.id = "ffp-lightbox";
  el.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;align-items:center;justify-content:center;z-index:10000;";
  el.innerHTML =
    '<button class="ffp-close" style="position:absolute;top:15px;right:20px;width:36px;height:36px;border:2px solid #fff;border-radius:50%;background:rgba(0,0,0,.5);color:#fff;font-size:22px;cursor:pointer">x</button>' +
    '<img style="max-width:95%;max-height:95%;display:none"/>' +
    '<video controls autoplay style="max-width:95%;max-height:95%;display:none"></video>' +
    '<audio controls autoplay style="width:80%;max-width:640px;display:none"></audio>';
  document.body.appendChild(el);
  const close = () => {
    const i = el.querySelector("img"),
      v = el.querySelector("video"),
      a = el.querySelector("audio");
    if (i) i.src = "";
    if (v) { v.pause(); v.src = ""; }
    if (a) { a.pause(); a.src = ""; }
    el.style.display = "none";
  };
  el.querySelector(".ffp-close").onclick = close;
  el.addEventListener("click", (e) => {
    if (e.target === el) close();
  });
}

const FFP_FOLDER_URL = new URL("./ico_dossier.png", import.meta.url).href;

function extBadge(ext) {
  if (!ext) ext = ".file";
  if (ext[0] !== ".") ext = "." + ext;
  return '<div class="ffp-ext">[File' + ext + "]</div>";
}

app.registerExtension({
  name: "Orion4d.FolderFileMax.UI",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!nodeData || nodeData.name !== "PyCodeMax_FolderFileMax") return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      if (onCreated) onCreated.apply(this, arguments);

      try {
        ensureLightbox();

        const wDir = this.widgets?.find((w) => w.name === "directory");
        const wExt = this.widgets?.find((w) => w.name === "extensions");
        const wRe = this.widgets?.find((w) => w.name === "name_regex");
        const wReM = this.widgets?.find((w) => w.name === "regex_mode");
        const wReIC = this.widgets?.find((w) => w.name === "regex_ignore_case");
        const wSort = this.widgets?.find((w) => w.name === "sort_by");
        const wDesc = this.widgets?.find((w) => w.name === "descending");
        const wSeedMode = this.widgets?.find((w) => w.name === "seed_mode");
        const wIndex = this.widgets?.find((w) => w.name === "index");
        // wIndex reste visible : utile pour voir/régler manuellement la position
        // Masquer le widget seed (plus utilisé, index suffit)
        const wSeed = this.widgets?.find((w) => w.name === "seed");
        if (wSeed) { wSeed.hidden = true; wSeed.computeSize = () => [0, -4]; }

        // Détection mode Node 2.0 : le nouveau menu est présent dans le DOM
        const _isNode2 = !!document.querySelector(".comfyui-menu, .comfy-vue-root");

        const root = document.createElement("div");
        const css = `
<style>
  .ffp-root {
      width: 100%; height: 100%; box-sizing: border-box;
      display: flex; flex-direction: column; padding: 6px;
      font-family: Arial, Helvetica, sans-serif; color: #ddd; overflow: hidden;
  }
  .ffp-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 6px; flex-shrink: 0; }
  .ffp-input, .ffp-btn, .ffp-select {
      background: #333; color: #ccc; border: 1px solid #555;
      border-radius: 6px; padding: 6px 8px; font-size: 12px;
  }
  .ffp-input { flex: 1 1 auto; min-width: 240px; }
  .ffp-grid {
      flex: 1 1 0; overflow-y: auto; background: #222; border-radius: 10px; padding: 10px;
      display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 10px; align-content: start;
  }
  .ffp-grid.ffp-list { display: block; }
  .ffp-card { display: flex; flex-direction: column; background: #2a2a2a; border-radius: 12px; border: 2px solid transparent; user-select: none; outline: none; cursor: pointer; }
  .ffp-card:hover { border-color: #666; }
  .ffp-card.selected { border-color: #00ffc9; }
  .ffp-media { display: flex; align-items: center; justify-content: center; height: 150px; border-radius: 10px 10px 0 0; background: #1b1b1b; overflow: hidden; color: #bbb; font-size: 22px; }
  .ffp-media img { max-width: 100%; max-height: 100%; object-fit: contain; }
  .ffp-info { padding: 8px 10px; font-size: 12px; word-break: break-all; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .ffp-grid.ffp-list .ffp-card { flex-direction: row; align-items: center; padding: 6px 8px; margin-bottom: 6px; }
  .ffp-grid.ffp-list .ffp-media { width: 52px; height: 52px; border-radius: 8px; margin-right: 10px; }
  .ffp-grid.ffp-list .ffp-info { padding: 0; -webkit-line-clamp: 1; }
  .ffp-ext { display: inline-block; font-size: 12px; border: 1px solid #777; border-radius: 6px; padding: 4px 6px; background: #1e1e1e; color: #ddd; }
</style>`;

        root.innerHTML = `
          ${css}
          <div class="ffp-root">
            <div class="ffp-row">
              <select class="ffp-select ffp-root-sel" title="Racine de navigation" style="max-width:200px"></select>
              <button class="ffp-btn ffp-up">Up</button>
              <input class="ffp-input ffp-path" placeholder="Chemin courant..." readonly/>
              <select class="ffp-select ffp-view"><option value="grid">Grid</option><option value="list">List</option></select>
              <button class="ffp-btn ffp-go">Refresh</button>
              <span class="ffp-count" style="margin-left:auto;font-size:12px;opacity:.8"></span>
            </div>
            <div class="ffp-row ffp-filter-row" style="display:none">
              <label style="font-size:11px;opacity:.7;flex-shrink:0">extensions</label>
              <input class="ffp-input ffp-ext-html" placeholder="ex: .png .jpg" style="min-width:100px;flex:1"/>
              <label style="font-size:11px;opacity:.7;flex-shrink:0;margin-left:8px">name_regex</label>
              <input class="ffp-input ffp-re-html" placeholder="regex..." style="min-width:100px;flex:1"/>
            </div>
            <div class="ffp-grid" tabindex="0"><p style="padding:8px">Choisissez une racine puis Refresh.</p></div>
          </div>`;

        this.addDOMWidget("folder_file_max", "div", root, {});
        this.size = [860, 660];

        const grid       = root.querySelector(".ffp-grid");
        const pathInput  = root.querySelector(".ffp-path");
        const upBtn      = root.querySelector(".ffp-up");
        const goBtn      = root.querySelector(".ffp-go");
        const rootSel    = root.querySelector(".ffp-root-sel");
        const viewSel    = root.querySelector(".ffp-view");
        const countLbl   = root.querySelector(".ffp-count");
        const filterRow  = root.querySelector(".ffp-filter-row");
        const extHtml    = root.querySelector(".ffp-ext-html");
        const reHtml     = root.querySelector(".ffp-re-html");

        // Racine actuellement sélectionnée — utilisée par toutes les requêtes
        let currentRoot = "";

        if (_isNode2) {
          // --- MODE NODE 2.0 ---
          // Les widgets natifs STRING perdent le focus à chaque frappe.
          // On les masque et on utilise les HTML inputs à la place.
          filterRow.style.display = "flex";
          if (wExt) wExt.hidden = true;
          if (wRe)  wRe.hidden  = true;

          function _syncNative() {
            if (wExt) wExt.value = extHtml.value;
            if (wRe)  wRe.value  = reHtml.value;
          }
          // Fetch sur Enter ou perte de focus (blur), pas sur chaque frappe
          function _htmlFetch() { _syncNative(); fetchList(); }
          extHtml.addEventListener("blur",    _htmlFetch);
          reHtml.addEventListener("blur",     _htmlFetch);
          extHtml.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); extHtml.blur(); } e.stopPropagation(); });
          reHtml.addEventListener("keydown",  (e) => { if (e.key === "Enter") { e.preventDefault(); reHtml.blur();  } e.stopPropagation(); });
          extHtml.addEventListener("keyup", (e) => e.stopPropagation());
          reHtml.addEventListener("keyup",  (e) => e.stopPropagation());
        }
        // Mode normal : wExt/wRe natifs restent visibles et éditables.
        // rewire() les gère — mais on les retire du rewire pour éviter
        // le fetch lettre par lettre. L'utilisateur valide avec le bouton Refresh.

        // Lecture de la valeur ext/regex selon le mode
        function getExt()   { return _isNode2 ? extHtml.value : (wExt ? wExt.value : ""); }
        function getRegex() { return _isNode2 ? reHtml.value  : (wRe  ? wRe.value  : ""); }

        let parentDir = null;
        let isLoading = false;
        let selectedPath = null;
        let lastDir = "";
        let lastView = "grid";
        let forceResetScroll = false;
        let typeBuffer = "";
        let typeTimer = null;
        const TYPE_TIMEOUT = 800;

        function cardsArray() { return Array.from(grid.querySelectorAll(".ffp-card")); }
        function getNameFromCard(card) {
          const info = card.querySelector(".ffp-info");
          return (info ? info.textContent : "").trim();
        }
        function selectCard(card, { scroll = true, updateIndex = true } = {}) {
          if (!card) return;
          cardsArray().forEach((c) => c.classList.remove("selected"));
          card.classList.add("selected");
          selectedPath = card.dataset.path || null;
          if (scroll) card.scrollIntoView({ block: "nearest" });
          if (updateIndex && card.dataset.type === "file") {
            // Ne PLUS forcer wSeedMode.value = "manual" — l'utilisateur peut
            // cliquer sur une carte pour redéfinir le point de départ tout en
            // restant en increment/decrement/randomize.
            resolveAndSelect.call(this, selectedPath);
            this.setDirtyCanvas(true, true);
          }
        }
        function selectByIndex(idx) {
          const list = cardsArray();
          if (!list.length) return;
          if (idx < 0) idx = 0;
          if (idx >= list.length) idx = list.length - 1;
          selectCard.call(this, list[idx]);
        }
        function currentIndex() {
          const list = cardsArray();
          const cur = grid.querySelector(".ffp-card.selected");
          return Math.max(0, list.indexOf(cur || list[0] || null));
        }

        function folderHTML(d) {
          return '<div class="ffp-media"><img class="ffp-folder-img" loading="lazy" src="' + FFP_FOLDER_URL + '" alt="folder"/></div><div class="ffp-info" title="' + d.name + '">' + d.name + "</div>";
        }
        function fileHTML(f) {
          if (f.type === "image") {
            const src = "/folder_file_max/thumbnail?filepath=" + encodeURIComponent(f.path);
            return '<div class="ffp-media"><img loading="lazy" src="' + src + '" /></div><div class="ffp-info" title="' + f.name + '">' + f.name + "</div>";
          } else if (f.type === "svg") {
            const src = "/folder_file_max/view?filepath=" + encodeURIComponent(f.path);
            return '<div class="ffp-media"><img loading="lazy" src="' + src + '" /></div><div class="ffp-info" title="' + f.name + '">' + f.name + "</div>";
          } else {
            return '<div class="ffp-media">' + extBadge(f.ext || ".file") + '</div><div class="ffp-info" title="' + f.name + '">' + f.name + "</div>";
          }
        }

        async function fetchList() {
          if (isLoading) return;
          isLoading = true;
          const prevScroll = grid.scrollTop;
          const prevDir = lastDir;
          const prevView = lastView;
          grid.style.opacity = "0.6";
          grid.innerHTML = "";
          selectedPath = null;

          try {
            const params = new URLSearchParams({
              directory: String(wDir ? wDir.value : ""),
              root: currentRoot,
              exts: getExt(),
              sort_by: String(wSort ? wSort.value : "name"),
              descending: String(!!(wDesc && wDesc.value)),
              regex: getRegex(),
              regex_mode: String(wReM ? wReM.value : "include"),
              regex_ic: String(!!(wReIC && wReIC.value)),
            }).toString();
            const res = await api.fetchApi("/folder_file_max/list?" + params);
            if (!res.ok) {
              let msg = "HTTP " + res.status;
              try { const j = await res.json(); if (j && j.error) msg += " — " + j.error; } catch(_){}
              throw new Error(msg);
            }
            const data = await res.json();

            const curDir = data.current_directory || "";
            const curView = viewSel.value;
            pathInput.value = curDir;
            parentDir = data.parent_directory || null;
            upBtn.disabled = !parentDir;
            countLbl.textContent = data.total_count ? String(data.total_count) + " fichier(s)" : "";
            grid.classList.toggle("ffp-list", curView === "list");

            (data.dirs || []).forEach((d) => {
              const card = document.createElement("div");
              card.className = "ffp-card";
              card.dataset.type = "dir";
              card.dataset.path = d.path;
              card.innerHTML = folderHTML(d);
              grid.appendChild(card);
            });
            (data.files || []).forEach((f) => {
              const card = document.createElement("div");
              card.className = "ffp-card";
              card.dataset.type = "file";
              card.dataset.path = f.path;
              card.innerHTML = fileHTML(f);
              grid.appendChild(card);
            });

            requestAnimationFrame(() => {
              const sameDir = curDir === prevDir;
              const sameView = curView === prevView;
              if (!sameDir || !sameView || forceResetScroll) grid.scrollTop = 0;
              else {
                const maxScroll = Math.max(0, grid.scrollHeight - grid.clientHeight);
                grid.scrollTop = Math.min(prevScroll, maxScroll);
              }
              lastDir = curDir;
              lastView = curView;
              forceResetScroll = false;
              // Ne pas voler le focus si l'utilisateur tape dans les filtres HTML
              const ae = document.activeElement;
              if (ae !== extHtml && ae !== reHtml) grid.focus();
            });
          } catch (e) {
            grid.innerHTML = '<p style="color:#ff7777;padding:8px">' + (e.message || String(e)) + "</p>";
            lastDir = String(wDir ? wDir.value : "");
            lastView = viewSel.value;
            forceResetScroll = false;
          } finally {
            isLoading = false;
            grid.style.opacity = "1";
          }
        }

        async function resolveAndSelect(targetPath) {
          if (!targetPath) return;
          try {
            const params = new URLSearchParams({
              directory: String(wDir ? wDir.value : ""),
              root: currentRoot,
              exts: getExt(),
              sort_by: String(wSort ? wSort.value : "name"),
              descending: String(!!(wDesc && wDesc.value)),
              regex: getRegex(),
              regex_mode: String(wReM ? wReM.value : "include"),
              regex_ic: String(!!(wReIC && wReIC.value)),
              path: String(targetPath),
            }).toString();
            const res = await api.fetchApi("/folder_file_max/resolve_index?" + params);
            const data = await res.json();
            if (data && typeof data.index === "number" && data.index >= 0) {
              const idxW = this.widgets?.find((w) => w.name === "index");
              if (idxW) idxW.value = data.index;
              this.setDirtyCanvas(true, true);
              // Notifier Python pour synchroniser _state avec le mode courant.
              // En increment/decrement, Python décale pour que le prochain run
              // tombe pile sur la carte cliquée.
              try {
                const sm = wSeedMode ? String(wSeedMode.value || "manual") : "manual";
                await api.fetchApi("/folder_file_max/set_index", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    node_id: String(this.id),
                    index: data.index,
                    seed_mode: sm,
                    count: data.count || 0,
                  }),
                });
              } catch(_) {}
            }
          } catch (e) { console.warn("[FolderFileMax] resolve_index error", e); }
        }

        grid.addEventListener("click", (e) => {
          const card = e.target.closest(".ffp-card");
          if (!card) return;
          selectCard.call(this, card, { scroll: false });
          grid.focus();
        });

        grid.addEventListener("dblclick", (e) => {
          const card = e.target.closest(".ffp-card");
          if (!card) return;
          const p = card.dataset.path;
          if (card.dataset.type === "dir") {
            if (wDir) { wDir.value = p; forceResetScroll = true; fetchList(); }
            return;
          }
          const isImg = /\.(png|jpg|jpeg|bmp|gif|webp|svg)$/i.test(p);
          const lb = document.getElementById("ffp-lightbox");
          const i = lb.querySelector("img"), v = lb.querySelector("video"), a = lb.querySelector("audio");
          i.style.display = v.style.display = a.style.display = "none";
          v.pause(); a.pause();
          if (isImg) {
            i.src = "/folder_file_max/view?filepath=" + encodeURIComponent(p);
            i.style.display = "block";
            lb.style.display = "flex";
          } else {
            window.open("/folder_file_max/view?filepath=" + encodeURIComponent(p), "_blank");
          }
        });

        function handleType(char) {
          if (!char) return;
          typeBuffer += char.toLowerCase();
          if (typeTimer) clearTimeout(typeTimer);
          typeTimer = setTimeout(() => (typeBuffer = ""), TYPE_TIMEOUT);
          const list = cardsArray();
          if (!list.length) return;
          let start = currentIndex.call(this) + 1;
          const N = list.length;
          for (let k = 0; k < N; k++) {
            const idx = (start + k) % N;
            const nm = getNameFromCard(list[idx]).toLowerCase();
            if (nm.startsWith(typeBuffer)) { selectByIndex.call(this, idx); return; }
          }
        }

        // FIX Node 2.0 : keydown capture-phase sur document pour passer avant LiteGraph
        const _nodeRef = this;
        function _gridKeyHandler(e) {
          if (!grid.contains(document.activeElement) && document.activeElement !== grid) return;
          const tag = (document.activeElement && document.activeElement.tagName) || "";
          if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
          if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            handleType.call(_nodeRef, e.key); e.preventDefault(); e.stopPropagation(); return;
          }
          if (e.key === "Backspace") { typeBuffer = typeBuffer.slice(0,-1); e.preventDefault(); e.stopPropagation(); return; }
          if (e.key === "Escape")    { typeBuffer = ""; e.stopPropagation(); return; }
        }
        document.addEventListener("keydown", _gridKeyHandler, { capture: true });

        function rewire(w) {
          if (!w) return;
          const prev = w.callback;
          w.callback = function () {
            if (prev) prev.apply(w, arguments);
            fetchList();
          };
        }
        // wExt/wRe mode normal : fetch uniquement sur blur (quitter le champ).
        // On écoute directement le blur sur l'inputEl du widget natif STRING.
        // En mode Node 2.0 ces widgets sont cachés, ce code est inoffensif.
        function attachFilterBlur(w) {
          if (!w) return;
          // inputEl : référence interne à l'<input> HTML du widget STRING natif
          const el = w.inputEl || w.element || null;
          if (el) {
            el.addEventListener("blur", () => fetchList());
          } else {
            // Fallback : debounce 1s si inputEl non accessible
            const prev = w.callback;
            let _ft = null;
            w.callback = function() {
              if (prev) prev.apply(w, arguments);
              clearTimeout(_ft);
              _ft = setTimeout(() => fetchList(), 1000);
            };
          }
        }
        attachFilterBlur(wExt);
        attachFilterBlur(wRe);
        [wDir, wReM, wReIC, wSort, wDesc].forEach(rewire);
        // seed_mode : rewire spécial — met aussi à jour wIndex selon le mode
        if (wSeedMode) {
          const prevSM = wSeedMode.callback;
          wSeedMode.callback = function() {
            if (prevSM) prevSM.apply(wSeedMode, arguments);
            const sm = (wSeedMode.value || "manual").toLowerCase();
            if (sm === "randomize" && wIndex) {
              const cards = cardsArray();
              const n = cards.filter(c => c.dataset.type === "file").length;
              if (n > 0) wIndex.value = Math.floor(Math.random() * n);
            }
            fetchList();
          };
        }

        upBtn.onclick = () => { if (parentDir && wDir) { wDir.value = parentDir; forceResetScroll = true; fetchList(); } };
        goBtn.onclick = () => { forceResetScroll = true; fetchList(); };
        viewSel.onchange = () => { forceResetScroll = true; fetchList(); };

        // Changement de racine via le dropdown
        rootSel.onchange = () => {
          currentRoot = rootSel.value || "";
          if (wDir) wDir.value = currentRoot;  // remet la nav sur la racine
          pathInput.value = currentRoot;
          forceResetScroll = true;
          fetchList();
        };

        // Sync sélection grille : interroge le serveur pour l'index réel
        // (Python _state est la source de vérité pour increment/decrement/randomize)
        async function _syncSelectionToIndex() {
          try {
            const r = await api.fetchApi("/folder_file_max/current_index?node_id=" + encodeURIComponent(String(_nodeRef.id)));
            const d = await r.json();
            if (d.index !== null && d.index !== undefined) {
              const idx = parseInt(d.index);
              if (!isNaN(idx)) {
                if (wIndex) wIndex.value = idx;
                _nodeRef.setDirtyCanvas(true, true);
                const cards = cardsArray();
                const fileCards = cards.filter(c => c.dataset.type === "file");
                if (!fileCards.length) return;
                const target = fileCards[Math.max(0, Math.min(idx, fileCards.length - 1))];
                if (target) {
                  cardsArray().forEach((c) => c.classList.remove("selected"));
                  target.classList.add("selected");
                  selectedPath = target.dataset.path || null;
                  target.scrollIntoView({ block: "nearest" });
                }
              }
            }
          } catch(e) {
            console.warn("[FolderFileMax] sync error", e);
          }
        }

        // Mécanisme principal : l'event "executing" de ComfyUI passe à null
        // quand TOUTE l'exécution est terminée. C'est le signal le plus fiable
        // pour savoir qu'on peut interroger Python pour l'index courant.
        let _ranThisExec = false;
        api.addEventListener("executing", (e) => {
          const node = (e.detail || {}).node ?? e.detail;
          const execId = String(node ?? "");
          const thisId = String(_nodeRef.id ?? "");
          if (execId === thisId) {
            _ranThisExec = true;
          }
          // node === null signifie fin de l'exécution complète
          if ((node === null || node === undefined) && _ranThisExec) {
            _ranThisExec = false;
            setTimeout(_syncSelectionToIndex, 50);
          }
        });

        // Filet de sécurité : également via "executed" si l'event arrive
        api.addEventListener("executed", (e) => {
          const detail = e.detail || {};
          const execId = String(detail.node ?? detail.node_id ?? "");
          const thisId = String(_nodeRef.id ?? "");
          if (execId === thisId) {
            setTimeout(_syncSelectionToIndex, 50);
          }
        });

        // onConfigure : restaure les valeurs depuis le workflow sauvegardé
        const _origConfigure = this.onConfigure;
        this.onConfigure = function(info) {
          if (_origConfigure) _origConfigure.call(this, info);
          if (_isNode2) {
            if (extHtml && wExt) extHtml.value = wExt.value || "";
            if (reHtml  && wRe)  reHtml.value  = wRe.value  || "";
          }
        };

        (async () => {
          await new Promise(r => setTimeout(r, 30));
          if (_isNode2) {
            if (extHtml && wExt) extHtml.value = wExt.value || "";
            if (reHtml  && wRe)  reHtml.value  = wRe.value  || "";
          }

          // 1. Récupérer les racines autorisées et peupler le dropdown
          let roots = [];
          try {
            const rRoots = await api.fetchApi("/folder_file_max/roots");
            const dRoots = await rRoots.json();
            roots = Array.isArray(dRoots.roots) ? dRoots.roots : [];
          } catch (e) {
            console.warn("[FolderFileMax] /roots indisponible:", e);
          }

          if (!roots.length) {
            grid.innerHTML = '<p style="color:#ff7777;padding:8px">Aucune racine autorisée. Définissez ORION4D_FOLDER_ROOTS et redémarrez ComfyUI.</p>';
            return;
          }

          rootSel.innerHTML = "";
          roots.forEach(r => {
            const opt = document.createElement("option");
            opt.value = r.path;
            opt.textContent = r.label;
            opt.title = r.path;
            rootSel.appendChild(opt);
          });

          // 2. Choisir la racine de départ : celle persistée si valide, sinon la première
          let chosenRoot = roots[0].path;
          let chosenDir  = roots[0].path;
          try {
            const r = await api.fetchApi("/folder_file_max/get_last_path");
            const d = await r.json();
            if (d.last_root && roots.some(rr => rr.path === d.last_root)) {
              chosenRoot = d.last_root;
              if (d.last_path) chosenDir = d.last_path;
            }
          } catch (e) { /* ignore */ }

          // Si le workflow embarque déjà un wDir.value valide, on le respecte
          // à condition qu'il soit sous une des racines autorisées.
          const workflowDir = wDir ? (wDir.value || "") : "";
          if (workflowDir) {
            const matching = roots.find(rr =>
              workflowDir === rr.path || workflowDir.startsWith(rr.path + "/") || workflowDir.startsWith(rr.path + "\\")
            );
            if (matching) {
              chosenRoot = matching.path;
              chosenDir  = workflowDir;
            }
          }

          currentRoot = chosenRoot;
          rootSel.value = chosenRoot;
          if (wDir) wDir.value = chosenDir;
          pathInput.value = chosenDir;
          lastDir = chosenDir;
          lastView = viewSel.value;

          forceResetScroll = true;
          fetchList();
        })();

      } catch (err) {
        console.error("[Orion4D] Erreur lors de la création de l'interface FolderFileMax :", err);
      }
    };
  },
});
// --- END OF FILE folder_file_max.js ---