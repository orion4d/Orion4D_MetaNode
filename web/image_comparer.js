// --- START OF FILE image_comparer.js ---
//
// Image Comparer — Orion4D (version Legacy / LiteGraph)
//
// Approche "tout-canvas" :
//   - Pas de DOM widget. Tout le rendu se fait via onDrawForeground,
//     directement sur le canvas LiteGraph.
//   - Rendu toujours net à tout zoom, toujours visible en dézoom extrême.
//
// Fonctionnement :
//   - Clic dans l'image : toggle A ↔ B.
//   - Deux ronds indicateurs sous l'image : plein = affiché, vide = masqué.
//     Cliquables aussi pour basculer directement sur A ou B.
//   - Label centré sous les ronds : "Image A: WxH" ou "Image B: WxH".

import { app } from "/scripts/app.js";

const IMG_TOP_PAD    = 8;
const INFO_BAR_H     = 38;
const DOTS_Y_OFFSET  = 10;
const LABEL_Y_OFFSET = 26;
const DOT_RADIUS     = 5;
const DOT_SPACING    = 18;

const INIT_W = 512;
const INIT_H = 600;
const MIN_W  = 280;
const MIN_H  = 260;

app.registerExtension({
    name: "Orion4d.ImageComparer",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "Orion4D_ImageComparer") return;

        // ─── onNodeCreated ───────────────────────────────────────────────
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreated) onNodeCreated.apply(this, arguments);

            this.size = [INIT_W, INIT_H];
            this.resizable = true;

            this._cmp = {
                showB: false,
                imgA: null,
                imgB: null,
                meta: null,
                imgRect:  { x: 0, y: 0, w: 0, h: 0 },
                dotARect: { x: 0, y: 0, r: 0 },
                dotBRect: { x: 0, y: 0, r: 0 },
            };
        };

        // ─── onExecuted : charger les images ─────────────────────────────
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            if (onExecuted) onExecuted.apply(this, arguments);
            if (!this._cmp) return;

            // Lire compare_images (enrichi) en priorité, fallback sur images
            const imgs = message && (message.compare_images || message.images);
            if (!imgs || imgs.length < 2) return;

            this.imgs = null; // supprime le rendu natif des thumbnails

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
            imgA.crossOrigin = "anonymous";
            imgB.crossOrigin = "anonymous";

            let loaded = 0;
            const s = this._cmp;
            const node = this;
            const onLoad = () => {
                loaded += 1;
                if (loaded === 2) {
                    s.imgA = imgA;
                    s.imgB = imgB;
                    s.meta = {
                        a: { orig_w: metaA.orig_w, orig_h: metaA.orig_h },
                        b: { orig_w: metaB.orig_w, orig_h: metaB.orig_h },
                    };
                    node.imgs = null;
                    app.graph.setDirtyCanvas(true, true);
                }
            };
            imgA.onload = onLoad;
            imgB.onload = onLoad;
            imgA.onerror = () => console.error("[ImageComparer] échec chargement A:", urlA);
            imgB.onerror = () => console.error("[ImageComparer] échec chargement B:", urlB);
            imgA.src = urlA;
            imgB.src = urlB;
        };

        // ─── onDrawBackground : empêche le rendu natif ───────────────────
        nodeType.prototype.onDrawBackground = function () {
            if (this.imgs) this.imgs = null;
        };

        // ─── onDrawForeground : image + ronds + label ────────────────────
        const onDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            if (onDrawForeground) onDrawForeground.call(this, ctx);
            if (this.flags && this.flags.collapsed) return;

            if (this.size[0] < MIN_W) this.size[0] = MIN_W;
            if (this.size[1] < MIN_H) this.size[1] = MIN_H;

            const s = this._cmp;
            if (!s) return;

            const topAfterWidgets = this._cmpComputeImageTop();
            const nodeW = this.size[0];
            const nodeH = this.size[1];

            const imgTop    = topAfterWidgets + IMG_TOP_PAD;
            const imgBottom = nodeH - INFO_BAR_H - 4;
            const imgLeft   = 8;
            const imgRight  = nodeW - 8;
            const zoneW     = Math.max(0, imgRight - imgLeft);
            const zoneH     = Math.max(0, imgBottom - imgTop);

            ctx.save();
            ctx.fillStyle = "#1a1a1a";
            ctx.fillRect(imgLeft, imgTop, zoneW, zoneH);
            ctx.strokeStyle = "#444";
            ctx.lineWidth = 1;
            ctx.strokeRect(imgLeft + 0.5, imgTop + 0.5, zoneW - 1, zoneH - 1);

            if (!s.imgA || !s.imgB) {
                ctx.fillStyle = "#666";
                ctx.font = "14px Arial, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText("(pending execution)",
                    imgLeft + zoneW / 2, imgTop + zoneH / 2);
                ctx.restore();
                s.imgRect = { x: imgLeft, y: imgTop, w: zoneW, h: zoneH };
                this._cmpDrawInfoBar(ctx, nodeW, nodeH);
                return;
            }

            const target = s.showB ? s.imgB : s.imgA;
            const fit = this._cmpComputeFitRect(
                target.naturalWidth, target.naturalHeight,
                imgLeft, imgTop, zoneW, zoneH
            );
            s.imgRect = fit;

            ctx.beginPath();
            ctx.rect(imgLeft, imgTop, zoneW, zoneH);
            ctx.clip();
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(target, fit.x, fit.y, fit.w, fit.h);
            ctx.restore();

            this._cmpDrawInfoBar(ctx, nodeW, nodeH);
        };

        // ─── Helpers ─────────────────────────────────────────────────────
        nodeType.prototype._cmpComputeFitRect = function (imgW, imgH, zoneX, zoneY, zoneW, zoneH) {
            if (!imgW || !imgH || zoneW <= 0 || zoneH <= 0) {
                return { x: zoneX, y: zoneY, w: 0, h: 0 };
            }
            const ratio = Math.min(zoneW / imgW, zoneH / imgH);
            const w = Math.floor(imgW * ratio);
            const h = Math.floor(imgH * ratio);
            return {
                x: zoneX + Math.floor((zoneW - w) / 2),
                y: zoneY + Math.floor((zoneH - h) / 2),
                w, h,
            };
        };

        nodeType.prototype._cmpComputeImageTop = function () {
            let maxBottom = 0;
            if (this.widgets) {
                for (const w of this.widgets) {
                    if (typeof w.last_y === "number") {
                        const wh = (w.computeSize
                            ? (w.computeSize(this.size[0])[1] || 20)
                            : (w.size && w.size[1]) || 20);
                        maxBottom = Math.max(maxBottom, w.last_y + wh);
                    }
                }
            }
            if (maxBottom > 0) return maxBottom;
            const numSockets = Math.max(
                (this.inputs || []).length,
                (this.outputs || []).length
            );
            return 30 + numSockets * 20;
        };

        nodeType.prototype._cmpDrawInfoBar = function (ctx, nodeW, nodeH) {
            const s = this._cmp;
            const barY = nodeH - INFO_BAR_H;
            ctx.save();

            const cx = nodeW / 2;
            const dotY = barY + DOTS_Y_OFFSET;
            const dotAx = cx - DOT_SPACING / 2;
            const dotBx = cx + DOT_SPACING / 2;
            s.dotARect = { x: dotAx, y: dotY, r: DOT_RADIUS };
            s.dotBRect = { x: dotBx, y: dotY, r: DOT_RADIUS };

            const drawDot = (x, y, filled) => {
                ctx.beginPath();
                ctx.arc(x, y, DOT_RADIUS, 0, Math.PI * 2);
                if (filled) {
                    ctx.fillStyle = "#fff";
                    ctx.fill();
                } else {
                    ctx.strokeStyle = "#888";
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                }
            };
            drawDot(dotAx, dotY, !s.showB);
            drawDot(dotBx, dotY,  s.showB);

            if (s.meta) {
                const meta = s.showB ? s.meta.b : s.meta.a;
                const name = s.showB ? "Image B" : "Image A";
                ctx.font = "11px 'Courier New', monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = "rgba(221, 221, 221, 0.85)";
                ctx.fillText(
                    `${name}: ${meta.orig_w}×${meta.orig_h}`,
                    cx, barY + LABEL_Y_OFFSET
                );
            }
            ctx.restore();
        };

        // ─── Souris ──────────────────────────────────────────────────────
        const _origMouseDown = nodeType.prototype.onMouseDown;
        nodeType.prototype.onMouseDown = function (e, pos) {
            const s = this._cmp;
            if (!s || !s.imgA || !s.imgB) {
                if (_origMouseDown) return _origMouseDown.call(this, e, pos);
                return;
            }

            const hitRadius = DOT_RADIUS + 4;
            const inDot = (p, rect) => {
                const dx = p[0] - rect.x;
                const dy = p[1] - rect.y;
                return dx * dx + dy * dy <= hitRadius * hitRadius;
            };
            if (inDot(pos, s.dotARect)) {
                s.showB = false;
                app.graph.setDirtyCanvas(true, true);
                return true;
            }
            if (inDot(pos, s.dotBRect)) {
                s.showB = true;
                app.graph.setDirtyCanvas(true, true);
                return true;
            }

            const r = s.imgRect;
            if (pos[0] >= r.x && pos[0] <= r.x + r.w &&
                pos[1] >= r.y && pos[1] <= r.y + r.h) {
                s.showB = !s.showB;
                app.graph.setDirtyCanvas(true, true);
                return true;
            }

            if (_origMouseDown) return _origMouseDown.call(this, e, pos);
        };

        const _origResize = nodeType.prototype.onResize;
        nodeType.prototype.onResize = function (size) {
            if (_origResize) _origResize.call(this, size);
            if (this.size[0] < MIN_W) this.size[0] = MIN_W;
            if (this.size[1] < MIN_H) this.size[1] = MIN_H;
        };
    }
});
// --- END OF FILE image_comparer.js ---
