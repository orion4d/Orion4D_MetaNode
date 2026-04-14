// --- START OF FILE lut_manager.js ---
// Orion4D_MetaNode — LUT Manager  JS  v5
//
// • Menu déroulant "image de calibration" — scanne lut_files/images_calibration/
//   + image_base.png (lut_files/) en tête (défaut)
// • L'image sélectionnée s'affiche en permanent dans le node
// • La LUT sélectionnée s'applique dessus en temps réel
// • Bouton "↺ Rafraîchir" recharge LUTs ET images de calibration

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// ---------------------------------------------------------------------------
// Cache images de calibration  [ { name, b64, default } ]
// ---------------------------------------------------------------------------
let _calibImages   = null;   // tableau complet
let _calibByName   = {};     // { name → b64 }
let _calibLoaded   = false;
let _calibPromise  = null;

async function loadCalibImages(force = false) {
    if (_calibLoaded && !force) return;
    if (_calibPromise && !force) return _calibPromise;
    _calibPromise = (async () => {
        try {
            const res  = await api.fetchApi("/orion4d/lut/calibration_images", { cache: "no-store" });
            const data = await res.json();
            _calibImages = data.images || [];
            _calibByName = {};
            for (const img of _calibImages) _calibByName[img.name] = img.b64;
            _calibLoaded = true;
        } catch (e) {
            console.warn("[LUTManager] Erreur chargement calibration_images:", e);
            _calibImages = []; _calibByName = {}; _calibLoaded = true;
        }
    })();
    return _calibPromise;
}
loadCalibImages();

// ---------------------------------------------------------------------------
// Cache liste presets
// ---------------------------------------------------------------------------
let _lutPresetNames = null;

async function fetchLutList(force = false) {
    if (_lutPresetNames && !force) return _lutPresetNames;
    try {
        const res  = await api.fetchApi("/orion4d/lut/list", { cache: "no-store" });
        const data = await res.json();
        _lutPresetNames = (data.presets || []).map(p => p.name);
    } catch { _lutPresetNames = []; }
    return _lutPresetNames;
}
fetchLutList();

// ---------------------------------------------------------------------------
// Résolution preset → chemin absolu
// ---------------------------------------------------------------------------
async function resolveLutPath(presetName) {
    if (!presetName || presetName === "None") return "";
    try {
        const res  = await api.fetchApi(`/orion4d/lut/resolve?name=${encodeURIComponent(presetName)}`, { cache: "no-store" });
        const data = await res.json();
        return data.path || "";
    } catch { return ""; }
}

// ---------------------------------------------------------------------------
// Appel /orion4d/lut/apply
// ---------------------------------------------------------------------------
async function applyLut(srcB64, lutPath, intensity, dataOrder, tableOrder) {
    try {
        const res = await api.fetchApi("/orion4d/lut/apply", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                base_data_b64: srcB64, lut_path: lutPath,
                intensity, data_order: dataOrder, table_order: tableOrder,
            }),
        });
        const data = await res.json();
        if (data.error) { console.warn("[LUTManager] apply error:", data.error); return null; }
        return data.adjusted_image_data || null;
    } catch (e) { console.warn("[LUTManager] fetch error:", e); return null; }
}

// ---------------------------------------------------------------------------
// Setup node
// ---------------------------------------------------------------------------
function setupLUTManager(node) {
    const _origConfigure = node.configure?.bind(node);

    node._lut_debounce      = null;
    node._lut_currentCalib  = null;   // nom de l'image de calibration active
    node._lut_currentB64    = null;   // b64 de cette image
    node._lut_currentImgEl  = null;   // HTMLImageElement chargé

    // ── DOM ───────────────────────────────────────────────────────────────────
    const wrap = document.createElement("div");
    wrap.style.cssText = "width:100%;position:relative;border-radius:6px;overflow:hidden;background:#111;";

    const canvas = document.createElement("canvas");
    canvas.style.cssText = "display:block;width:100%;image-rendering:auto;";
    canvas._ratio = 0;
    wrap.appendChild(canvas);

    const badge = document.createElement("div");
    badge.style.cssText = [
        "position:absolute;top:6px;right:6px;display:none;pointer-events:none;",
        "background:rgba(80,180,255,0.92);color:#000;font-size:10px;",
        "font-weight:bold;padding:2px 8px;border-radius:4px;"
    ].join("");
    wrap.appendChild(badge);

    const spinner = document.createElement("div");
    spinner.style.cssText = [
        "position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);",
        "color:rgba(255,255,255,0.75);font-size:13px;display:none;pointer-events:none;",
        "background:rgba(0,0,0,0.45);padding:4px 10px;border-radius:6px;"
    ].join("");
    spinner.textContent = "⏳";
    wrap.appendChild(spinner);

    const domWidget = node.addDOMWidget("lut_preview_canvas", "div", wrap, {
        computeSize(nodeW) {
            if (!canvas._ratio) return [nodeW, 0];
            const h = Math.round(nodeW * canvas._ratio);
            canvas.style.height = h + "px";
            return [nodeW, h + 2];
        },
        getValue() { return ""; }, setValue() {},
    });

    // ── Dessin canvas ─────────────────────────────────────────────────────────
    function paintImgEl(imgEl) {
        if (!imgEl) return;
        canvas._ratio = imgEl.naturalHeight / imgEl.naturalWidth;
        const W = canvas.offsetWidth || 300;
        const H = Math.round(W * canvas._ratio);
        canvas.width  = imgEl.naturalWidth;
        canvas.height = imgEl.naturalHeight;
        canvas.style.height = H + "px";
        canvas.getContext("2d").drawImage(imgEl, 0, 0);
        domWidget.computeSize?.(W);
        app.graph?.setDirtyCanvas(true, true);
    }

    function paintB64(b64) {
        return new Promise(resolve => {
            const img = new Image();
            img.onload  = () => { paintImgEl(img); resolve(img); };
            img.onerror = () => resolve(null);
            img.src = "data:image/png;base64," + b64;
        });
    }

    function clearCanvas() {
        canvas._ratio = 0; canvas.width = 1; canvas.height = 1;
        canvas.style.height = "0px"; badge.style.display = "none";
        domWidget.computeSize?.(canvas.offsetWidth || 300);
        app.graph?.setDirtyCanvas(true, true);
    }

    // ── Lecture widgets ───────────────────────────────────────────────────────
    function getW(name) { return node.widgets?.find(w => w.name === name)?.value ?? ""; }

    function getCurrentParams() {
        return {
            rawPath:    (getW("lut_path") || "").trim().replace(/^["']|["']$/g, ""),
            preset:     getW("lut_preset") || "None",
            intensity:  parseFloat(getW("intensity"))   || 1.0,
            opacity:    parseFloat(getW("opacity"))     || 1.0,
            dataOrder:  getW("data_order")  || "BGR",
            tableOrder: getW("table_order") || "BGR",
        };
    }

    // ── Chargement image de calibration ──────────────────────────────────────
    async function switchCalibImage(name) {
        await loadCalibImages();
        const b64 = _calibByName[name] || null;
        if (!b64) { clearCanvas(); node._lut_currentB64 = null; node._lut_currentImgEl = null; return; }
        node._lut_currentCalib = name;
        node._lut_currentB64   = b64;
        const imgEl = await paintB64(b64);
        node._lut_currentImgEl = imgEl;
        // Redéclencher la preview avec la nouvelle image
        node._lut_schedule(50);
    }

    // ── Update preview ────────────────────────────────────────────────────────
    node._lut_updatePreview = async function () {
        if (!node._lut_currentB64 || !node._lut_currentImgEl) {
            clearCanvas(); return;
        }
        const { rawPath, preset, intensity, opacity, dataOrder, tableOrder } = getCurrentParams();
        let lutPath = rawPath;
        if (!lutPath && preset !== "None") lutPath = await resolveLutPath(preset);

        if (!lutPath) {
            paintImgEl(node._lut_currentImgEl);
            badge.style.display = "none";
            return;
        }

        spinner.style.display = "block";
        const resultB64 = await applyLut(node._lut_currentB64, lutPath, intensity, dataOrder, tableOrder);
        spinner.style.display = "none";

        if (!resultB64) {
            paintImgEl(node._lut_currentImgEl);
            badge.style.display = "none";
            return;
        }

        if (opacity < 1.0) {
            paintImgEl(node._lut_currentImgEl);
            await new Promise(resolve => {
                const overlay = new Image();
                overlay.onload = () => {
                    const ctx = canvas.getContext("2d");
                    ctx.globalAlpha = opacity;
                    ctx.drawImage(overlay, 0, 0, canvas.width, canvas.height);
                    ctx.globalAlpha = 1.0;
                    app.graph?.setDirtyCanvas(true, true);
                    resolve();
                };
                overlay.onerror = () => resolve();
                overlay.src = "data:image/png;base64," + resultB64;
            });
        } else {
            await paintB64(resultB64);
        }

        badge.textContent = preset !== "None" ? preset : "custom";
        badge.style.display = "block";
    };

    node._lut_schedule = function (delay = 80) {
        clearTimeout(node._lut_debounce);
        node._lut_debounce = setTimeout(() => node._lut_updatePreview(), delay);
    };

    // ── Construction widgets ──────────────────────────────────────────────────
    function buildWidgets() {
        // Mise à jour liste combo LUTs
        const presetW = node.widgets?.find(w => w.name === "lut_preset");
        if (presetW) {
            fetchLutList(true).then(names => {
                presetW.options = presetW.options || {};
                presetW.options.values = ["None", ...names];
            });
        }

        // Hook tous les paramètres LUT
        ["lut_path", "lut_preset", "intensity", "opacity", "data_order", "table_order"].forEach(name => {
            const w = node.widgets?.find(ww => ww.name === name);
            if (w && !w._lut_hooked) {
                w._lut_hooked = true;
                const prev = w.callback;
                w.callback = function(value) {
                    if (prev) prev.call(this, value);
                    node._lut_schedule(name === "lut_preset" || name === "lut_path" ? 100 : 60);
                };
            }
        });

        // ── Sélecteur image de calibration ───────────────────────────────────
        // On crée un widget bouton + select DOM custom
        if (!node._calib_select_built) {
            node._calib_select_built = true;

            const selWrap = document.createElement("div");
            selWrap.style.cssText = "width:100%;display:flex;gap:4px;padding:2px 0;align-items:center;";

            const label = document.createElement("span");
            label.textContent = "📷";
            label.style.cssText = "font-size:14px;flex-shrink:0;";

            const select = document.createElement("select");
            select.style.cssText = [
                "flex:1;background:#2a2a2a;color:#ddd;border:1px solid #555;",
                "border-radius:4px;padding:3px 6px;font-size:12px;cursor:pointer;"
            ].join("");

            selWrap.appendChild(label);
            selWrap.appendChild(select);

            // Remplissage du select
            async function populateSelect() {
                await loadCalibImages(true);
                select.innerHTML = "";
                if (_calibImages.length === 0) {
                    const opt = document.createElement("option");
                    opt.value = ""; opt.textContent = "(aucune image de calibration)";
                    select.appendChild(opt); return;
                }
                for (const img of _calibImages) {
                    const opt = document.createElement("option");
                    opt.value       = img.name;
                    opt.textContent = img.default ? `${img.name} ★` : img.name;
                    select.appendChild(opt);
                }
                // Sélectionner le défaut (image_base) ou la première
                const defaultImg = _calibImages.find(i => i.default) || _calibImages[0];
                if (defaultImg) {
                    select.value = defaultImg.name;
                    await switchCalibImage(defaultImg.name);
                }
            }

            select.addEventListener("change", async () => {
                if (select.value) await switchCalibImage(select.value);
            });

            node.addDOMWidget("calib_selector", "div", selWrap, {
                computeSize(w) { return [w, 30]; },
                getValue() { return select.value; },
                setValue(v) { if (v) { select.value = v; switchCalibImage(v); } },
            });

            populateSelect();
            node._calib_populate = populateSelect;
        }
    }

    // ── Bouton Rafraîchir ─────────────────────────────────────────────────────
    node.addWidget("button", "↺ Rafraîchir", null, async () => {
        _calibLoaded = false; _calibImages = null; _calibByName = {};
        await loadCalibImages(true);
        await fetchLutList(true);
        // Relancer la liste du combo LUT
        const presetW = node.widgets?.find(w => w.name === "lut_preset");
        if (presetW) {
            presetW.options = presetW.options || {};
            presetW.options.values = ["None", ...(_lutPresetNames || [])];
        }
        // Repeupler le sélecteur images
        if (node._calib_populate) await node._calib_populate();
        node._lut_schedule(100);
    });

    // ResizeObserver
    new ResizeObserver(() => {
        requestAnimationFrame(() => {
            if (!canvas._ratio) return;
            const W = canvas.offsetWidth || 300;
            canvas.style.height = Math.round(W * canvas._ratio) + "px";
            domWidget.computeSize?.(W);
            app.graph?.setDirtyCanvas(true, true);
        });
    }).observe(wrap);

    node.configure = function(data) {
        if (_origConfigure) _origConfigure.call(this, data);
        setTimeout(() => buildWidgets(), 250);
    };
    setTimeout(() => buildWidgets(), 250);
}

// ---------------------------------------------------------------------------
// Enregistrement
// ---------------------------------------------------------------------------
app.registerExtension({
    name: "Orion4d.LUTManager",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "PyCodeMax_LUTManager") {
            const names = await fetchLutList();
            const inp = nodeData.input?.required?.lut_preset;
            if (inp) inp[0] = ["None", ...names];
        }
    },

    nodeCreated(node) {
        if (node.comfyClass === "PyCodeMax_LUTManager") setupLUTManager(node);
    },
});

// --- END OF FILE lut_manager.js ---
