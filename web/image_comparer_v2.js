// --- START OF FILE image_comparer_v2.js ---
//
// Image Comparer V2 (beta) — interface JS
//
// Optimisé pour ComfyUI Nodes 2.0 : rendu via DOM widget (canvas HTML)
// pour contourner la superposition du rendu natif Nodes 2.0.
//
// Modes :
//   - Slide  (défaut) : déplace la souris horizontalement pour révéler B sur A
//   - Click           : un clic toggle entre A et B
//
// Contrôles supplémentaires :
//   - Bouton "🔄 Swap A/B" qui inverse l'affichage sans rebrancher
//   - Mode sélectionnable via le widget combo

import { app } from "/scripts/app.js";

// Limite d'aperçu côté navigateur — au-dessus on consomme trop de mémoire
const MAX_PREVIEW = 2048;

app.registerExtension({
    name: "Orion4d.ImageComparerV2",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "Orion4D_ImageComparerV2") return;

        // ─── onNodeCreated : construire l'UI ────────────────────────────
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            this.size = [512, 600];
            this.resizable = true;

            // État interne
            this._compareState = {
                mode: "slide",       // "slide" | "click"
                sliderX: 0.5,        // 0..1, position du curseur en mode slide
                clickShowB: false,   // mode click : true = afficher B, false = A
                swap: false,         // si true, inverse A et B partout
                imgA: null,          // HTMLImageElement
                imgB: null,
                imgA_url: null,
                imgB_url: null,
                meta: null,          // {orig_w, orig_h, disp_w, disp_h} pour A et B
            };

            // ─── DOM widget : canvas + barre d'info ─────────────────────
            const container = document.createElement("div");
            container.style.cssText = `
                display: flex;
                flex-direction: column;
                width: 100%;
                height: 100%;
                box-sizing: border-box;
                font-family: Arial, Helvetica, sans-serif;
                color: #ddd;
                user-select: none;
                min-height: 0;
                overflow: hidden;
            `;

            // Wrapper du canvas : flex: 1 pour prendre tout l'espace dispo,
            // min-height: 0 pour permettre au flex de shrinker correctement.
            // position: relative pour que le canvas absolute s'y accroche.
            const canvasWrap = document.createElement("div");
            canvasWrap.style.cssText = `
                flex: 1 1 auto;
                min-height: 0;
                position: relative;
                width: 100%;
                background: #1a1a1a;
                border: 1px solid #444;
                border-radius: 4px;
                overflow: hidden;
            `;

            const canvas = document.createElement("canvas");
            canvas.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                cursor: ew-resize;
                display: block;
            `;
            canvasWrap.appendChild(canvas);
            const ctx = canvas.getContext("2d");

            const infoBar = document.createElement("div");
            infoBar.style.cssText = `
                flex: 0 0 auto;
                font-size: 11px;
                padding: 4px 6px;
                display: flex;
                justify-content: space-between;
                gap: 8px;
                opacity: 0.85;
                font-family: 'Courier New', monospace;
            `;
            const infoLeft  = document.createElement("span");
            const infoRight = document.createElement("span");
            infoBar.appendChild(infoLeft);
            infoBar.appendChild(infoRight);

            container.appendChild(canvasWrap);
            container.appendChild(infoBar);

            this.addDOMWidget("comparer_view", "div", container, {
                serialize: false,
            });

            // ─── Widgets de contrôle ────────────────────────────────────
            this.addWidget(
                "combo",
                "mode",
                "slide",
                (v) => {
                    this._compareState.mode = v;
                    redraw();
                },
                { values: ["slide", "click"] }
            );

            // Référence au bouton Swap pour pouvoir griser/regrisser selon mode
            const swapWidget = this.addWidget("button", "🔄 Swap A/B", null, () => {
                if (node._compareState.mode === "click") {
                    // Sans effet en mode click : on bascule entre A et B
                    // au clic sur l'image, swap n'a pas de sens.
                    return;
                }
                this._compareState.swap = !this._compareState.swap;
                redraw();
            });
            // On garde le label original pour le restaurer en mode slide
            swapWidget._origName = swapWidget.name;

            // ─── Helpers d'affichage ────────────────────────────────────
            const node = this;

            // Calcule la zone de l'image dans le canvas en préservant le ratio
            const computeFitRect = (imgW, imgH, canvasW, canvasH) => {
                if (!imgW || !imgH) return { x: 0, y: 0, w: 0, h: 0 };
                const ratio = Math.min(canvasW / imgW, canvasH / imgH);
                const w = Math.floor(imgW * ratio);
                const h = Math.floor(imgH * ratio);
                return {
                    x: Math.floor((canvasW - w) / 2),
                    y: Math.floor((canvasH - h) / 2),
                    w, h,
                };
            };

            // ─── Downscale progressif avec cache ─────────────────────────
            // Les grosses images (2048+) rendues via un seul drawImage vers
            // une petite cible (ex: 400px) sont toujours un peu floues, même
            // avec imageSmoothingQuality="high". La technique classique est
            // de downscaler par étapes (÷2 à chaque fois) via des canvas
            // intermédiaires, ce qui donne un résultat quasi-identique au
            // rendu natif <img>. On cache le résultat pour éviter de
            // recalculer à chaque redraw (ex: chaque mouvement du slider).
            //
            // Le cache est stocké sur le node (_downscaleCache) avec une clé
            // combinant l'URL de l'image et la taille cible + le ratio pixel.
            node._downscaleCache = node._downscaleCache || new Map();

            const getDownscaled = (sourceImg, sourceUrl, targetW, targetH) => {
                if (!sourceImg || !sourceUrl) return sourceImg;
                const srcW = sourceImg.naturalWidth;
                const srcH = sourceImg.naturalHeight;
                if (!srcW || !srcH) return sourceImg;

                // Résolution cible en pixels bitmap (après compensation
                // dpr × zoomComp appliquée par setTransform)
                const bmpTargetW = Math.ceil(targetW * (dpr * zoomComp));
                const bmpTargetH = Math.ceil(targetH * (dpr * zoomComp));

                // Si la cible est plus grande ou égale à la source, pas
                // besoin de downscale — on rend direct, le navigateur gère
                // le upscale de toute façon.
                if (bmpTargetW >= srcW || bmpTargetH >= srcH) return sourceImg;

                // Clé de cache : URL + taille cible arrondie. On bucketise
                // par pas de 8px pour tolérer de petits resizes sans
                // invalider le cache à chaque frame.
                const bucketW = Math.round(bmpTargetW / 8) * 8;
                const bucketH = Math.round(bmpTargetH / 8) * 8;
                const key = `${sourceUrl}|${bucketW}x${bucketH}`;
                const cached = node._downscaleCache.get(key);
                if (cached) return cached;

                // Downscale progressif ÷2 via canvas intermédiaires jusqu'à
                // atteindre une taille proche de la cible (facteur < 2).
                let curCanvas = document.createElement("canvas");
                let curCtx = curCanvas.getContext("2d");
                curCtx.imageSmoothingEnabled = true;
                curCtx.imageSmoothingQuality = "high";
                let curW = srcW;
                let curH = srcH;
                curCanvas.width = curW;
                curCanvas.height = curH;
                curCtx.drawImage(sourceImg, 0, 0);

                while (curW > bucketW * 2 && curH > bucketH * 2) {
                    const nextW = Math.max(bucketW, Math.floor(curW / 2));
                    const nextH = Math.max(bucketH, Math.floor(curH / 2));
                    const nextCanvas = document.createElement("canvas");
                    nextCanvas.width = nextW;
                    nextCanvas.height = nextH;
                    const nextCtx = nextCanvas.getContext("2d");
                    nextCtx.imageSmoothingEnabled = true;
                    nextCtx.imageSmoothingQuality = "high";
                    nextCtx.drawImage(curCanvas, 0, 0, nextW, nextH);
                    curCanvas = nextCanvas;
                    curCtx = nextCtx;
                    curW = nextW;
                    curH = nextH;
                }

                // Passe finale vers la taille cible exacte
                const finalCanvas = document.createElement("canvas");
                finalCanvas.width = bmpTargetW;
                finalCanvas.height = bmpTargetH;
                const finalCtx = finalCanvas.getContext("2d");
                finalCtx.imageSmoothingEnabled = true;
                finalCtx.imageSmoothingQuality = "high";
                finalCtx.drawImage(curCanvas, 0, 0, bmpTargetW, bmpTargetH);

                // Limite la taille du cache pour éviter les fuites mémoire
                // (4 entrées max = 2 images × 2 tailles récentes)
                if (node._downscaleCache.size > 4) {
                    const firstKey = node._downscaleCache.keys().next().value;
                    node._downscaleCache.delete(firstKey);
                }
                node._downscaleCache.set(key, finalCanvas);
                return finalCanvas;
            };

            // Cache-friendly : on suit le dpr*zoomComp courant pour que
            // getDownscaled connaisse la vraie résolution bitmap cible.
            let dpr = 1;
            let zoomComp = 1;

            const getDisplayPair = () => {
                const s = node._compareState;
                if (!s.imgA || !s.imgB) return [null, null, "A", "B"];
                // Quand on swap, on échange les images ET les labels — donc
                // ce qui était sur image_a (avec son étiquette "A") part à
                // droite et reste étiqueté "A". L'étiquette suit la donnée.
                if (s.swap) {
                    return [s.imgB, s.imgA, "B", "A"];
                }
                return [s.imgA, s.imgB, "A", "B"];
            };

            const redraw = () => {
                const s = node._compareState;
                const w = canvasLogicalW;
                const h = canvasLogicalH;
                if (!w || !h) return;

                ctx.fillStyle = "#1a1a1a";
                ctx.fillRect(0, 0, w, h);

                // Qualité de rééchantillonnage max pour le downscale des images
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = "high";

                const [imgA, imgB, labelLeft, labelRight] = getDisplayPair();
                if (!imgA || !imgB) {
                    ctx.fillStyle = "#666";
                    ctx.font = "14px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("(pending execution)", w / 2, h / 2);
                    return;
                }

                // Les deux images ont déjà été alignées côté Python, donc
                // on suppose qu'elles ont la même taille d'affichage
                const rect = computeFitRect(imgA.naturalWidth, imgA.naturalHeight, w, h);

                if (s.mode === "click") {
                    // Toggle simple : on bascule entre la "gauche" et la "droite"
                    const showRight = s.clickShowB;
                    const target = showRight ? imgB : imgA;
                    const targetUrl = showRight ? s.imgB_url : s.imgA_url;
                    const src = getDownscaled(target, targetUrl, rect.w, rect.h);
                    ctx.drawImage(src, rect.x, rect.y, rect.w, rect.h);
                    // (plus d'étiquette overlay — info affichée dans la barre du bas)
                } else {
                    // Mode slide : "imgA" (côté gauche) en entier, "imgB" clippé à droite.
                    // On passe par des versions downscalées en cache pour un
                    // rendu net même en dézoom (sinon le drawImage d'une grosse
                    // source vers une petite cible est flou).
                    const srcA = getDownscaled(imgA, s.swap ? s.imgB_url : s.imgA_url, rect.w, rect.h);
                    ctx.drawImage(srcA, rect.x, rect.y, rect.w, rect.h);

                    const splitX = rect.x + Math.floor(rect.w * s.sliderX);
                    const bWidth = rect.x + rect.w - splitX;
                    if (bWidth > 0) {
                        // Pour B on a besoin d'une version downscalée aussi.
                        // On prend la portion droite (srcOffsetX..srcW dans la
                        // version downscalée, proportionnellement à sliderX).
                        const srcB = getDownscaled(imgB, s.swap ? s.imgA_url : s.imgB_url, rect.w, rect.h);
                        const bNatW = srcB.width || srcB.naturalWidth;
                        const bNatH = srcB.height || srcB.naturalHeight;
                        const srcOffsetX = s.sliderX * bNatW;
                        const srcW = bNatW - srcOffsetX;
                        ctx.drawImage(
                            srcB,
                            srcOffsetX, 0, srcW, bNatH,
                            splitX, rect.y, bWidth, rect.h
                        );
                    }

                    // Ligne de séparation
                    ctx.strokeStyle = "#fff";
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(splitX, rect.y);
                    ctx.lineTo(splitX, rect.y + rect.h);
                    ctx.stroke();

                    // Petit rond sur la ligne pour le grip visuel
                    ctx.fillStyle = "#fff";
                    ctx.beginPath();
                    ctx.arc(splitX, rect.y + rect.h / 2, 8, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.fillStyle = "#000";
                    ctx.font = "bold 10px Arial";
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText("◀▶", splitX, rect.y + rect.h / 2);
                    // (plus d'étiquettes overlay — info affichée dans la barre du bas)
                }

                updateInfoBar();
            };

            const updateInfoBar = () => {
                const s = node._compareState;
                if (!s.meta) {
                    infoLeft.textContent = "";
                    infoRight.textContent = "";
                    return;
                }

                if (s.mode === "click") {
                    // Mode click : un seul label centré, qui se réfère à
                    // l'entrée d'origine (image_a ou image_b). Le swap est
                    // désactivé en mode click, donc on regarde directement
                    // quelle image est affichée via clickShowB.
                    const showB = s.clickShowB;
                    const meta = showB ? s.meta.b : s.meta.a;
                    const name = showB ? "Image B" : "Image A";
                    infoBar.style.justifyContent = "center";
                    infoLeft.textContent = `${name}: ${meta.orig_w}×${meta.orig_h}`;
                    infoRight.textContent = "";
                } else {
                    // Mode slide : label gauche + label droit, intervertis si swap.
                    // L'étiquette suit la donnée : ce qui est affiché à gauche
                    // garde son identité d'origine.
                    const leftMeta  = s.swap ? s.meta.b : s.meta.a;
                    const rightMeta = s.swap ? s.meta.a : s.meta.b;
                    const leftName  = s.swap ? "Image B" : "Image A";
                    const rightName = s.swap ? "Image A" : "Image B";
                    infoBar.style.justifyContent = "space-between";
                    infoLeft.textContent  = `${leftName}: ${leftMeta.orig_w}×${leftMeta.orig_h}`;
                    infoRight.textContent = `${rightName}: ${rightMeta.orig_w}×${rightMeta.orig_h}`;
                }
            };

            // ─── Gestion souris ─────────────────────────────────────────
            let isDragging = false;

            const updateSliderFromEvent = (e) => {
                const s = node._compareState;
                if (!s.imgA || !s.imgB) return;
                const r = canvas.getBoundingClientRect();
                const rect = computeFitRect(
                    s.imgA.naturalWidth, s.imgA.naturalHeight,
                    canvasLogicalW, canvasLogicalH
                );
                if (rect.w === 0) return;
                // Convertir les coordonnées CSS vers coordonnées canvas (logique).
                // r.width est en pixels CSS, canvasLogicalW aussi → ratio = 1
                // sauf si le wrapper a été scalé par CSS transform (rare).
                const scale = canvasLogicalW / r.width;
                const localX = (e.clientX - r.left) * scale - rect.x;
                const t = Math.max(0, Math.min(1, localX / rect.w));
                s.sliderX = t;
                redraw();
            };

            canvas.addEventListener("mousedown", (e) => {
                e.stopPropagation();
                const s = node._compareState;
                if (s.mode === "click") {
                    s.clickShowB = !s.clickShowB;
                    redraw();
                } else {
                    isDragging = true;
                    updateSliderFromEvent(e);
                }
            });

            canvas.addEventListener("mousemove", (e) => {
                if (node._compareState.mode === "slide") {
                    if (isDragging) {
                        e.stopPropagation();
                        updateSliderFromEvent(e);
                    } else {
                        // Mode slide passif : suit la souris au survol sans drag
                        updateSliderFromEvent(e);
                    }
                }
            });

            const stopDrag = () => { isDragging = false; };
            window.addEventListener("mouseup", stopDrag);
            canvas.addEventListener("mouseleave", stopDrag);

            // Helper : applique l'état visuel du bouton Swap selon le mode courant
            const updateSwapButtonVisual = () => {
                if (!swapWidget) return;
                if (node._compareState.mode === "click") {
                    // Grisé visuellement : on change le label avec un préfixe
                    // qui indique l'inactivité. La callback est aussi no-op
                    // (gérée dans la fonction du bouton).
                    swapWidget.name = "🚫 Swap A/B (mode click)";
                } else {
                    swapWidget.name = swapWidget._origName || "🔄 Swap A/B";
                }
            };

            // Mettre à jour le curseur visuel selon le mode
            const updateCursor = () => {
                canvas.style.cursor = node._compareState.mode === "click"
                    ? "pointer"
                    : "ew-resize";
            };

            // Hook : redessiner et resynchroniser quand le mode change
            const modeWidget = node.widgets.find(w => w.name === "mode");
            if (modeWidget) {
                const prev = modeWidget.callback;
                modeWidget.callback = function () {
                    if (prev) prev.apply(this, arguments);
                    node._compareState.mode = modeWidget.value;
                    updateCursor();
                    updateSwapButtonVisual();
                    redraw();
                };

                // Bug fix : après un F5/chargement de workflow, le widget a sa
                // valeur restaurée mais _compareState.mode est resté à "slide"
                // (l'init JS). On resynchronise explicitement, sinon le mode
                // affiché ne correspond pas au comportement réel jusqu'au
                // prochain changement manuel.
                node._compareState.mode = modeWidget.value;
            }

            // Dimensions logiques (pixels CSS) du canvas — le bitmap peut
            // être plus grand (HiDPI), on raisonne toujours en CSS pour le
            // dessin et la détection de clic.
            let canvasLogicalW = 0;
            let canvasLogicalH = 0;
            // Dernier facteur de compensation zoom appliqué — sert à détecter
            // un changement de zoom ComfyUI même si la taille logique est stable.
            let lastZoomComp = 0;

            // ─── Resize handler : adapter le canvas au wrapper ──────────
            // Gère le HiDPI (écrans Retina, devicePixelRatio > 1) : sans ça,
            // le canvas bitmap fait N pixels mais est étiré en CSS sur N×dpr
            // pixels physiques → images floues. On dimensionne le bitmap en
            // pixels physiques et on scale le contexte en conséquence.
            //
            // `force=true` : recrée le bitmap même si les dimensions CSS
            //  n'ont pas changé. Utile après chargement d'images quand on
            //  n'est pas sûr que le bitmap actuel est à la bonne résolution.
            const resizeCanvas = (force = false) => {
                // Le canvas DOM est dans un wrapper qui vit à l'intérieur du
                // canvas LiteGraph de ComfyUI. Quand l'utilisateur zoome
                // dans ComfyUI (ex: 17%), le node est affiché plus petit à
                // l'écran — MAIS sa taille logique (dans les coordonnées du
                // graphe) reste la même. Si on dimensionne le bitmap sur la
                // taille écran, il devient sous-résolu dès qu'on dézoome à
                // 100% → images pixelisées.
                //
                // clientWidth/Height donnent la taille LOGIQUE (coordonnées
                // du node, invariantes au zoom). On dimensionne le bitmap
                // sur cette taille multipliée par dpr (HiDPI) ET par le
                // facteur de zoom courant si disponible, pour que le bitmap
                // soit toujours net quel que soit le zoom au moment du run.
                const r = canvasWrap.getBoundingClientRect();
                const logicalW = canvasWrap.clientWidth  || r.width;
                const logicalH = canvasWrap.clientHeight || r.height;
                const cssW = Math.max(64, Math.floor(logicalW));
                const cssH = Math.max(64, Math.floor(logicalH));
                const newDpr = window.devicePixelRatio || 1;

                // Facteur de zoom LiteGraph : si on est à 17%, on veut un
                // bitmap ~6x plus grand pour rester net à 100%. On plafonne
                // à 6x pour éviter d'exploser la mémoire sur un gros node.
                let newZoomComp = 1;
                try {
                    const lgCanvas = app.canvas;
                    if (lgCanvas && lgCanvas.ds && lgCanvas.ds.scale > 0) {
                        newZoomComp = Math.max(1, Math.min(6, 1 / lgCanvas.ds.scale));
                    }
                } catch (_) { /* ignore */ }

                const bmpW = Math.floor(cssW * newDpr * newZoomComp);
                const bmpH = Math.floor(cssH * newDpr * newZoomComp);
                const totalScale = newDpr * newZoomComp;
                const changed = (canvas.width !== bmpW || canvas.height !== bmpH
                    || canvasLogicalW !== cssW || canvasLogicalH !== cssH
                    || lastZoomComp !== newZoomComp);
                if (changed || force) {
                    // Si la résolution bitmap cible a significativement changé,
                    // le cache de downscale devient obsolète — on le vide.
                    if (lastZoomComp !== newZoomComp && node._downscaleCache) {
                        node._downscaleCache.clear();
                    }
                    canvas.width  = bmpW;
                    canvas.height = bmpH;
                    canvasLogicalW = cssW;
                    canvasLogicalH = cssH;
                    lastZoomComp = newZoomComp;
                    dpr = newDpr;
                    zoomComp = newZoomComp;
                    // Reset transform puis scale combiné (dpr × compensation
                    // de zoom). Tout le code de dessin continue à raisonner
                    // en pixels CSS logiques.
                    ctx.setTransform(totalScale, 0, 0, totalScale, 0, 0);
                    redraw();
                }
            };

            // ResizeObserver pour suivre les changements de taille du wrapper
            if (typeof ResizeObserver !== "undefined") {
                const ro = new ResizeObserver(() => resizeCanvas());
                ro.observe(canvasWrap);
            }

            // Surveillance du zoom ComfyUI : ResizeObserver ne se déclenche
            // pas toujours au dézoome (la taille logique du wrapper ne bouge
            // pas), donc on poll le scale LiteGraph et on re-dimensionne le
            // bitmap quand on passe à un zoom où le bitmap actuel deviendrait
            // sous-résolu. Seulement actif quand des images sont chargées.
            let lastObservedScale = -1;
            const zoomWatchInterval = setInterval(() => {
                const s = node._compareState;
                if (!s || !s.imgA) return;
                try {
                    const sc = app.canvas && app.canvas.ds && app.canvas.ds.scale;
                    if (sc && sc !== lastObservedScale) {
                        lastObservedScale = sc;
                        resizeCanvas();
                    }
                } catch (_) { /* ignore */ }
            }, 200);
            // Nettoyage si le node est supprimé
            const onRemoved = this.onRemoved;
            this.onRemoved = function () {
                clearInterval(zoomWatchInterval);
                if (onRemoved) onRemoved.apply(this, arguments);
            };

            // ─── Hook onExecuted : récupérer les images après chaque run ──
            const onExecuted = nodeType.prototype.onExecuted;
            this._origOnExecuted = onExecuted;

            // On stocke les helpers sur le node pour qu'onExecuted et
            // onConfigure y accèdent depuis l'extérieur du closure
            this._compareRedraw = redraw;
            this._compareResizeCanvas = resizeCanvas;
            this._compareUpdateCursor = updateCursor;
            this._compareUpdateSwapVisual = updateSwapButtonVisual;

            updateCursor();
            updateSwapButtonVisual();
            // Premier resize après que le DOM soit attaché
            setTimeout(resizeCanvas, 50);
        };

        // ─── onConfigure : appelé après restauration des widgets depuis JSON ──
        // C'est ici que le widget "mode" reçoit sa valeur sauvegardée. À ce
        // moment-là, onNodeCreated a déjà tourné mais avec la valeur par défaut.
        // On resynchronise donc l'état JS interne avec la valeur réelle des
        // widgets restaurés. Sans ça, le combo affiche "click" mais le
        // comportement reste "slide" jusqu'à un changement manuel.
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            if (onConfigure) onConfigure.apply(this, arguments);
            const s = this._compareState;
            if (!s) return;
            const modeWidget = this.widgets && this.widgets.find(w => w.name === "mode");
            if (modeWidget) {
                s.mode = modeWidget.value;
            }
            // Mettre à jour les visuels qui dépendent du mode
            if (typeof this._compareUpdateSwapVisual === "function") {
                this._compareUpdateSwapVisual();
            }
            if (typeof this._compareUpdateCursor === "function") {
                this._compareUpdateCursor();
            }
            if (typeof this._compareRedraw === "function") {
                this._compareRedraw();
            }
        };

        // ─── onExecuted : charger les nouvelles images ──────────────────
        const prevOnExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            if (prevOnExecuted) prevOnExecuted.apply(this, arguments);

            const s = this._compareState;
            if (!s) return;
            // On lit notre clé custom (pas "images") pour éviter le rendu
            // natif ComfyUI des thumbnails en bas du node.
            const imgs = message && message.compare_images;
            if (!imgs || imgs.length < 2) return;

            // Trier par label : "a" puis "b"
            const sorted = [...imgs].sort((x, y) =>
                (x.label || "").localeCompare(y.label || "")
            );
            const metaA = sorted.find(i => i.label === "a") || sorted[0];
            const metaB = sorted.find(i => i.label === "b") || sorted[1];

            const buildUrl = (m) => {
                const params = new URLSearchParams({
                    filename:  m.filename,
                    type:      m.type || "temp",
                    subfolder: m.subfolder || "",
                });
                return `/view?${params.toString()}&t=${Date.now()}`;
            };

            const urlA = buildUrl(metaA);
            const urlB = buildUrl(metaB);

            const imgA = new Image();
            const imgB = new Image();
            let loaded = 0;
            const self = this;
            const onLoad = () => {
                loaded += 1;
                if (loaded === 2) {
                    s.imgA = imgA;
                    s.imgB = imgB;
                    s.imgA_url = urlA;
                    s.imgB_url = urlB;
                    s.meta = {
                        a: { orig_w: metaA.orig_w, orig_h: metaA.orig_h },
                        b: { orig_w: metaB.orig_w, orig_h: metaB.orig_h },
                    };
                    // Nouvelles images → le cache de downscale des images
                    // précédentes n'a plus d'intérêt.
                    if (self._downscaleCache) self._downscaleCache.clear();
                    // Au tout premier run, le layout DOM peut ne pas être
                    // encore stable au moment où les images arrivent : le
                    // canvas bitmap a été dimensionné trop tôt (ou trop petit)
                    // et les images apparaissent floues jusqu'à un resize
                    // manuel. On force donc plusieurs passes de recalcul :
                    // - rAF immédiat (une fois le layout de la frame calculé)
                    // - rAF suivant (sécurise si LiteGraph recalcule en retard)
                    // - setTimeout(100) (filet de sécurité si tout le reste
                    //   se fait avant que le node final soit dimensionné)
                    // Chaque passe utilise force=true pour recréer le bitmap
                    // même si les dimensions CSS semblent identiques.
                    const doRefresh = () => {
                        if (self._compareResizeCanvas) self._compareResizeCanvas(true);
                        if (self._compareRedraw) self._compareRedraw();
                    };
                    requestAnimationFrame(() => {
                        doRefresh();
                        requestAnimationFrame(doRefresh);
                    });
                    setTimeout(doRefresh, 100);
                }
            };
            imgA.onload = onLoad;
            imgB.onload = onLoad;
            imgA.onerror = () => console.error("[ImageComparer] échec chargement A:", urlA);
            imgB.onerror = () => console.error("[ImageComparer] échec chargement B:", urlB);
            imgA.src = urlA;
            imgB.src = urlB;
        };
    }
});
// --- END OF FILE image_comparer_v2.js ---