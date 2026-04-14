// --- START OF FILE curves_pro.js ---
// Curves Pro - Orion4d-coder pack  v8
//
// Changements v8 :
//   CurvesPro     : canvas carré 1:1, grille double densité (Photoshop style),
//                   magnétisme de grille, pas d'image en filigrane
//   CurvesProImage: suppression aperçu natif via beforeRegisterNodeDef
//                   (injection de image_upload désactivée), canvas propre

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------
const HISTO_H    = 28;
const SNAP_PX    = 8;
// 3 niveaux de grille : 0=simple(4×4), 1=moyen(4×4+8×8), 2=fin(4×4+16×16)
const GRID_LEVELS = [
    { major:4, minor:1 },
    { major:4, minor:2 },
    { major:4, minor:4 },
];

const CHANNEL_MAP = { RGB:"rgb", Red:"r", Green:"g", Blue:"b" };
const LINE_C  = { rgb:"rgba(255,220,0,1)",     r:"rgba(255,80,80,1)",    g:"rgba(80,230,80,1)",    b:"rgba(80,130,255,1)"    };
const POINT_C = { rgb:"rgba(255,200,0,1)",     r:"rgba(255,60,60,1)",    g:"rgba(60,210,60,1)",    b:"rgba(60,110,255,1)"    };
const HIST_C  = { rgb:"rgba(200,200,200,.55)", r:"rgba(255,100,100,.55)", g:"rgba(100,240,100,.55)", b:"rgba(100,130,255,.55)" };

const DEFAULT_CURVE = () => [{ x:0, y:0 }, { x:1, y:1 }];

// ---------------------------------------------------------------------------
// Preset cache : RETIRÉ en v9. Les presets Curves Pro sont maintenant gérés
// par le système unifié color_fx_presets.js qui ajoute automatiquement les
// widgets preset/Save/Delete/Refresh/Reset à tout node présent dans
// FX_NODE_CONFIG (Curves Pro y est listé).
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Tracé Catmull-Rom
// ---------------------------------------------------------------------------
function drawCatmullRom(ctx, pts, W, H) {
    if (!pts||pts.length<2) return;
    const sp=pts.map(p=>({x:p.x*W, y:(1-p.y)*H}));
    ctx.beginPath(); ctx.moveTo(sp[0].x,sp[0].y);
    for(let i=0;i<sp.length-1;i++){
        const p0=sp[Math.max(0,i-1)],p1=sp[i],p2=sp[i+1],p3=sp[Math.min(sp.length-1,i+2)];
        for(let t=1/20;t<=1+1e-9;t+=1/20){
            const t2=t*t,t3=t2*t;
            ctx.lineTo(
                .5*((2*p1.x)+(-p0.x+p2.x)*t+(2*p0.x-5*p1.x+4*p2.x-p3.x)*t2+(-p0.x+3*p1.x-3*p2.x+p3.x)*t3),
                .5*((2*p1.y)+(-p0.y+p2.y)*t+(2*p0.y-5*p1.y+4*p2.y-p3.y)*t2+(-p0.y+3*p1.y-3*p2.y+p3.y)*t3)
            );
        }
    }
    ctx.stroke();
}

// ---------------------------------------------------------------------------
// Appel API apply
// ---------------------------------------------------------------------------
async function apiApply(srcImage, curvesJson) {
    if (!srcImage||!srcImage.complete||!srcImage.naturalWidth) return null;
    const cv=document.createElement("canvas");
    cv.width=srcImage.naturalWidth; cv.height=srcImage.naturalHeight;
    cv.getContext("2d").drawImage(srcImage,0,0);
    try {
        const res=await api.fetchApi("/orion4d/curves_pro/apply",{
            method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({base_data_b64:cv.toDataURL("image/png").split(",")[1],all_curves_json:curvesJson,base_data_type:"image"}),
        }).then(r=>r.json());
        if(!res.adjusted_image_data) return null;
        return await new Promise(resolve=>{
            const img=new Image(); img.onload=()=>resolve(img);
            img.src="data:image/png;base64,"+res.adjusted_image_data;
        });
    } catch { return null; }
}

// ---------------------------------------------------------------------------
// Navigation dans le graphe
// ---------------------------------------------------------------------------
function findConnectedImageNodes(curveNode) {
    if(!app.graph) return [];
    return Object.values(app.graph.links||{})
        .filter(l=>l&&l.origin_id===curveNode.id)
        .map(l=>app.graph.getNodeById(l.target_id))
        .filter(n=>n?.comfyClass==="PyCodeMax_CurvesProImage");
}

function findCurveProNodes(imgNode) {
    if(!app.graph) return [];
    return (imgNode.inputs||[])
        .filter(inp=>inp.name==="curves_json"&&inp.link!=null)
        .map(inp=>{ const l=app.graph.links[inp.link]; return l&&app.graph.getNodeById(l.origin_id); })
        .filter(n=>n?.comfyClass==="PyCodeMax_CurvesPro");
}


// ============================================================================
//  NŒUD 1 : PyCodeMax_CurvesPro  (éditeur, canvas carré 1:1)
// ============================================================================
function setupCurvesPro(node) {
    const _origConfigure=node.configure?.bind(node);
    const _origSerialize=node.serialize?.bind(node);

    node.activeChannel="rgb";
    node.allCurves={rgb:DEFAULT_CURVE(),r:DEFAULT_CURVE(),g:DEFAULT_CURVE(),b:DEFAULT_CURVE()};
    node.histograms={};
    node._pendingPt=-1;
    node._clickTimer=null;
    node._snapEnabled=true;
    node._gridLevel=1;

    // ── DOM widget : canvas carré + histo ─────────────────────────────────
    const wrap=document.createElement("div");
    wrap.style.cssText="width:100%;display:flex;flex-direction:column;";

    const cvCurve=document.createElement("canvas");
    cvCurve.style.cssText="display:block;width:100%;border-radius:8px 8px 0 0;cursor:crosshair;background:#1a1a1a;";

    // ── Toolbar compacte (snap / grille) ─────────────────────────────────
    const toolbar=document.createElement("div");
    toolbar.style.cssText="display:flex;gap:4px;padding:3px 6px;background:#222;align-items:center;flex-shrink:0;";

    function makeBtn(label,title,onClick){
        const b=document.createElement("button");
        b.textContent=label; b.title=title; b._active=false;
        b.style.cssText="font-size:11px;padding:2px 7px;border-radius:4px;border:1px solid #555;background:#333;color:#ccc;cursor:pointer;line-height:1.4;transition:background .1s;";
        b.onmouseenter=()=>{ if(!b._active) b.style.background="#444"; };
        b.onmouseleave=()=>{ b.style.background=b._active?(b._activeBg||"#1a3a1a"):"#333"; };
        b.onclick=(e)=>{ e.stopPropagation(); onClick(b); };
        return b;
    }
    function setActive(b,on,color,bg){
        b._active=on; b._activeBg=bg||"#1a3a1a";
        b.style.color=on?(color||"#8f8"):"#ccc";
        b.style.background=on?b._activeBg:"#333";
    }

    // Snap
    const btnSnap=makeBtn("⊞ Snap","Magnétisme de grille (aussi clic droit canvas)",()=>{
        node._snapEnabled=!node._snapEnabled;
        setActive(btnSnap,node._snapEnabled,"#8f8","#1a3a1a");
        node.redrawCurve();
    });
    setActive(btnSnap,true,"#8f8","#1a3a1a");

    // Grille (3 niveaux cyclables)
    const GRID_LABELS=["⊡ 4×4","⊞ 8×8","⊟ 16×16"];
    const btnGrid=makeBtn(GRID_LABELS[1],"Densité de grille (cliquer pour cycler)",()=>{
        node._gridLevel=(node._gridLevel+1)%3;
        btnGrid.textContent=GRID_LABELS[node._gridLevel];
        node.redrawCurve();
    });


    toolbar.appendChild(btnSnap);
    toolbar.appendChild(btnGrid);

    const TOOLBAR_H=26;

    const cvHisto=document.createElement("canvas");
    cvHisto.height=HISTO_H;
    cvHisto.style.cssText="display:block;width:100%;background:#161616;border-radius:0 0 6px 6px;";

    wrap.appendChild(cvCurve);
    wrap.appendChild(toolbar);
    wrap.appendChild(cvHisto);

    node.addDOMWidget("curves_canvas","div",wrap,{
        computeSize(w){ return[w, w+TOOLBAR_H+HISTO_H+2]; },
        getValue(){return"";},setValue(){},
    });

    // Synchronise la hauteur du canvas avec sa largeur réelle (1:1)
    function syncSquare(){
        const W=cvCurve.offsetWidth||300;
        if(cvCurve.width!==W||cvCurve.height!==W){
            cvCurve.width=W; cvCurve.height=W;
            cvCurve.style.height=W+"px";
        }
        cvHisto.width=W;
    }

    // ── Dessin courbe ─────────────────────────────────────────────────────
    node.redrawCurve=function(){
        syncSquare();
        const W=cvCurve.width;
        const H=W;
        const ctx=cvCurve.getContext("2d");
        ctx.clearRect(0,0,W,H);
        ctx.fillStyle="#1a1a1a"; ctx.fillRect(0,0,W,H);

        const gl=GRID_LEVELS[this._gridLevel];
        const totalDiv=gl.major*gl.minor;

        // Grille mineure (seulement si minor > 1)
        if(gl.minor>1){
            ctx.strokeStyle="rgba(255,255,255,0.04)"; ctx.lineWidth=1;
            for(let i=1;i<totalDiv;i++){
                if(i%gl.minor===0) continue;
                const x=W*i/totalDiv, y=H*i/totalDiv;
                ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();
                ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();
            }
        }
        // Grille majeure
        ctx.strokeStyle="rgba(255,255,255,0.10)"; ctx.lineWidth=1;
        for(let i=1;i<gl.major;i++){
            const x=W*i/gl.major, y=H*i/gl.major;
            ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();
            ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();
        }

        // Diagonale neutre
        // Mode normal  : (0,0)=bas-gauche → (1,1)=haut-droite  → diagonale ↗
        // Diagonale neutre (bas-gauche → haut-droit)
        ctx.strokeStyle="rgba(255,255,255,0.14)"; ctx.setLineDash([4,4]);
        ctx.beginPath(); ctx.moveTo(0,H); ctx.lineTo(W,0); ctx.stroke();
        ctx.setLineDash([]);

        // ── Conversion point logique → pixel canvas ───────────────────────
        // (utilise la fonction locale toCanvas/fromCanvas définie plus bas)

        const pts=this.allCurves[this.activeChannel];
        const lc=LINE_C[this.activeChannel]||"rgba(255,220,0,1)";
        const pc=POINT_C[this.activeChannel]||"white";

        if(pts?.length>=2){
            const sp=pts.map(p=>toCanvas(p.x,p.y,W,H));

            // Extensions pointillées
            const fade=lc.replace(",1)",",0.25)");
            ctx.strokeStyle=fade;ctx.lineWidth=1;ctx.setLineDash([3,3]);
            if(pts[0].x>0){ctx.beginPath();ctx.moveTo(0,sp[0].y);ctx.lineTo(sp[0].x,sp[0].y);ctx.stroke();}
            if(pts[pts.length-1].x<1){ctx.beginPath();ctx.moveTo(sp[sp.length-1].x,sp[sp.length-1].y);ctx.lineTo(W,sp[sp.length-1].y);ctx.stroke();}
            ctx.setLineDash([]);

            // Courbe — on passe les pts déjà convertis en espace canvas
            ctx.strokeStyle=lc;ctx.lineWidth=2.5;ctx.shadowColor=lc;ctx.shadowBlur=7;
            ctx.beginPath(); ctx.moveTo(sp[0].x,sp[0].y);
            for(let i=0;i<sp.length-1;i++){
                const p0=sp[Math.max(0,i-1)],p1=sp[i],p2=sp[i+1],p3=sp[Math.min(sp.length-1,i+2)];
                for(let t=1/20;t<=1+1e-9;t+=1/20){
                    const t2=t*t,t3=t2*t;
                    ctx.lineTo(
                        .5*((2*p1.x)+(-p0.x+p2.x)*t+(2*p0.x-5*p1.x+4*p2.x-p3.x)*t2+(-p0.x+3*p1.x-3*p2.x+p3.x)*t3),
                        .5*((2*p1.y)+(-p0.y+p2.y)*t+(2*p0.y-5*p1.y+4*p2.y-p3.y)*t2+(-p0.y+3*p1.y-3*p2.y+p3.y)*t3)
                    );
                }
            }
            ctx.stroke(); ctx.shadowBlur=0;

            // Points
            for(let i=0;i<sp.length;i++){
                const pending=(i===this._pendingPt);
                ctx.beginPath();ctx.arc(sp[i].x,sp[i].y,pending?10:5,0,Math.PI*2);
                ctx.fillStyle=pending?"rgba(255,80,80,1)":pc;
                ctx.strokeStyle="rgba(255,255,255,0.85)";ctx.lineWidth=1.5;
                ctx.fill();ctx.stroke();
            }
        }

        // Labels axes
        ctx.font="9px Arial"; ctx.fillStyle="rgba(255,255,255,0.3)";
        ctx.textAlign="left";  ctx.textBaseline="bottom"; ctx.fillText("Noir",3,H-3);
        ctx.textAlign="right"; ctx.textBaseline="top";    ctx.fillText("Blanc",W-3,3);

        // Histogramme
        const hctx=cvHisto.getContext("2d");
        hctx.fillStyle="#161616";hctx.fillRect(0,0,W,HISTO_H);
        const hd=this.histograms[this.activeChannel];
        if(hd?.length){
            hctx.fillStyle=HIST_C[this.activeChannel]||"rgba(200,200,200,.55)";
            const bw=W/256;
            for(let i=0;i<256;i++){const bh=hd[i]*HISTO_H;hctx.fillRect(i*bw,HISTO_H-bh,bw,bh);}
        }
    };

    // ── Histogramme ───────────────────────────────────────────────────────
    node.updateHistogram=async function(){
        // Source d'image prioritaire : _hybridSourceImage (mode hybride,
        // reçue via WS quand image_in est branché). Sinon fallback sur
        // l'image chargée dans un CurvesProImage connecté en aval.
        let src=this._hybridSourceImage;
        if(!src||!src.complete||!src.naturalWidth){
            const imgNode=findConnectedImageNodes(this)[0];
            src=imgNode?._sourceImage;
        }
        if(!src||!src.complete||!src.naturalWidth) return;
        const cv=document.createElement("canvas");cv.width=src.naturalWidth;cv.height=src.naturalHeight;
        cv.getContext("2d").drawImage(src,0,0);
        const chW=this.widgets?.find(w=>w.name==="channel");
        try{
            const res=await api.fetchApi("/orion4d/curves_pro/get_histogram",{
                method:"POST",headers:{"Content-Type":"application/json"},
                body:JSON.stringify({base_data_b64:cv.toDataURL("image/png").split(",")[1],channel_mode:chW?.value??"RGB"}),
            }).then(r=>r.json());
            if(res.histogram){this.histograms[this.activeChannel]=res.histogram;this.redrawCurve();}
        }catch(e){}
    };

    // ── Propagation courbes ───────────────────────────────────────────────
    node.propagateCurves=async function(){
        const curvesW=this.widgets?.find(w=>w.name==="all_curves_json");
        if(!curvesW) return;
        const ser={};
        for(const k in this.allCurves) ser[k]=this.allCurves[k].map(p=>[p.x,p.y]);
        const cj=JSON.stringify(ser);
        curvesW.value=cj;
        for(const imgNode of findConnectedImageNodes(this)){
            imgNode.applyLiveCurves?.(cj);
        }
    };

    // ── Transformées coordonnées (pures, prennent W/H en arg) ────────────
    // y=0 → bas canvas (noir),  y=1 → haut canvas (blanc)
    function toCanvas(px, py, W, H) {
        return { x:px*W, y:(1-py)*H };
    }
    function fromCanvas(cx, cy, W, H) {
        return { x:cx/W, y:1-cy/H };
    }

    // ── Magnétisme ────────────────────────────────────────────────────────
    function applySnap(x, y) {
        if(!node._snapEnabled) return {x,y};
        const W=cvCurve.width;
        const gl=GRID_LEVELS[node._gridLevel];
        const totalDiv=gl.major*gl.minor;
        const step=1/totalDiv;
        const tol=SNAP_PX/W;
        const sx=Math.round(x/step)*step;
        const sy=Math.round(y/step)*step;
        return {
            x: Math.abs(x-sx)<tol ? sx : x,
            y: Math.abs(y-sy)<tol ? sy : y,
        };
    }

    // ── Interaction souris ────────────────────────────────────────────────
    let dragging=-1, dragged=false;

    function pt2c(e){
        const r=cvCurve.getBoundingClientRect();
        const W=cvCurve.width, H=cvCurve.height;
        return[(e.clientX-r.left)*W/r.width, (e.clientY-r.top)*H/r.height];
    }
    function hitTest(mx,my){
        const W=cvCurve.width, H=cvCurve.height;
        const pts=node.allCurves[node.activeChannel];
        for(let i=0;i<pts.length;i++){
            const cp=toCanvas(pts[i].x,pts[i].y,W,H);
            if(Math.hypot(mx-cp.x, my-cp.y)<14) return i;
        }
        return -1;
    }

    cvCurve.addEventListener("mousedown",(e)=>{
        if(e.button!==0) return; e.stopPropagation();
        const [mx,my]=pt2c(e);
        const W=cvCurve.width, H=cvCurve.height;
        const h=hitTest(mx,my);
        if(h!==-1){
            if(node._pendingPt===h){
                clearTimeout(node._clickTimer); node._clickTimer=null;
                const pts=node.allCurves[node.activeChannel];
                if(h>0&&h<pts.length-1) pts.splice(h,1);
                node._pendingPt=-1;
                node.redrawCurve(); node.propagateCurves();
            } else {
                node._pendingPt=h; dragging=h; dragged=false;
                clearTimeout(node._clickTimer);
                node._clickTimer=setTimeout(()=>{node._pendingPt=-1;node.redrawCurve();},800);
                node.redrawCurve();
            }
        } else {
            node._pendingPt=-1; clearTimeout(node._clickTimer); node._clickTimer=null;
            let {x:nx,y:ny}=fromCanvas(mx,my,W,H);
            nx=Math.max(0,Math.min(1,nx)); ny=Math.max(0,Math.min(1,ny));
            const snapped=applySnap(nx,ny);
            nx=snapped.x; ny=snapped.y;
            const pts=node.allCurves[node.activeChannel];
            const idx=pts.findIndex(p=>p.x>nx);
            pts.splice(idx===-1?pts.length:idx,0,{x:nx,y:ny});
            dragging=idx===-1?pts.length-1:idx; dragged=false;
            node.redrawCurve();
        }
    });

    cvCurve.addEventListener("mousemove",(e)=>{
        if(e.buttons!==1||dragging===-1) return; e.stopPropagation();
        dragged=true;
        const [mx,my]=pt2c(e);
        const W=cvCurve.width, H=cvCurve.height;
        const pts=node.allCurves[node.activeChannel];
        const pt=pts[dragging];

        const isFirst=(dragging===0);
        const isLast=(dragging===pts.length-1);
        const minX=isFirst ? 0 : pts[dragging-1].x+0.001;
        const maxX=isLast  ? 1 : pts[dragging+1].x-0.001;

        let {x:nx,y:ny}=fromCanvas(mx,my,W,H);
        ny=Math.max(0,Math.min(1,ny));
        nx=Math.max(minX,Math.min(maxX,nx));

        const snapped=applySnap(nx,ny);
        pt.x=Math.max(minX,Math.min(maxX,snapped.x));
        pt.y=snapped.y;

        node.redrawCurve();
        clearTimeout(node._debounce);
        node._debounce=setTimeout(()=>node.propagateCurves(),60);
    });

    cvCurve.addEventListener("mouseup",(e)=>{
        if(dragged&&dragging!==-1) node.propagateCurves();
        dragging=-1;dragged=false;
    });
    cvCurve.addEventListener("mouseleave",(e)=>{
        if(e.buttons!==1){dragging=-1;dragged=false;}
    });

    // Clic droit → toggle magnétisme
    cvCurve.addEventListener("contextmenu",(e)=>{
        e.preventDefault(); e.stopPropagation();
        node._snapEnabled=!node._snapEnabled;
        node.redrawCurve();
    });

    // ResizeObserver pour le carré 1:1
    new ResizeObserver(()=>requestAnimationFrame(()=>{ syncSquare(); node.redrawCurve(); })).observe(wrap);

    // ── Widgets boutons ───────────────────────────────────────────────────
    // Les anciens boutons "Preset Name / Save Preset / Reset" ont été retirés
    // en v9 au profit du système unifié color_fx_presets.js qui injecte ses
    // propres widgets (preset / Save / Delete / Refresh / Reset) sur tout node
    // présent dans FX_NODE_CONFIG. On expose ici les helpers dont a besoin
    // ce système générique pour dialoguer avec notre canvas.
    function buildWidgets(){
        if(!node.widgets) return;

        // Le widget all_curves_json est invisible : c'est le canvas qui en
        // contrôle la valeur, l'utilisateur n'a pas à le voir.
        const cjw=node.widgets.find(w=>w.name==="all_curves_json");
        if(cjw){cjw.type="hidden";cjw.hidden=true;cjw.computeSize=()=>[0,-4];}

        const chW=node.widgets.find(w=>w.name==="channel");
        node.activeChannel=CHANNEL_MAP[chW?.value]??"rgb";

        // Nettoyage des anciens widgets preset custom s'ils persistent dans
        // un workflow chargé (compat ascendante)
        const KILL=["Preset Name","Save Preset","Reset"];
        for(let i=node.widgets.length-1;i>=0;i--){
            if(KILL.includes(node.widgets[i].name)) node.widgets.splice(i,1);
        }

        if(chW){
            chW.callback=(value)=>{
                node.activeChannel=CHANNEL_MAP[value]??"rgb";
                node.updateHistogram();node.redrawCurve();
            };
        }
        setTimeout(()=>{ syncSquare(); node.redrawCurve(); },80);
    }

    // ── Helpers exposés pour color_fx_presets.js ──────────────────────────
    // Ces méthodes permettent au système unifié de presets de lire et
    // restaurer l'état du canvas quand on charge un preset Curves Pro.

    // Retourne le JSON courant des courbes (format {rgb, r, g, b}) sous forme
    // de string, exactement comme le widget all_curves_json le contient.
    node._curvesProGetJson=function(){
        const out={};
        for(const k of ["rgb","r","g","b"]){
            const pts=this.allCurves[k]||DEFAULT_CURVE();
            out[k]=pts.map(p=>[p.x,p.y]);
        }
        return JSON.stringify(out);
    };

    // Reload : appelé par color_fx_presets.js après applyParams() pour
    // resynchroniser le canvas avec la nouvelle valeur du widget
    // all_curves_json (que le système générique vient d'écrire).
    node._curvesProReloadFromJson=function(){
        const cjw=this.widgets?.find(w=>w.name==="all_curves_json");
        if(!cjw||!cjw.value) return;
        try{
            const data=JSON.parse(cjw.value);
            if(!data||typeof data!=="object") return;
            const next={rgb:DEFAULT_CURVE(),r:DEFAULT_CURVE(),g:DEFAULT_CURVE(),b:DEFAULT_CURVE()};
            for(const k of ["rgb","r","g","b"]){
                const pts=data[k];
                if(Array.isArray(pts)&&pts.length>=2){
                    // Tolère les deux formats : [[x,y],...] ou [{x,y},...]
                    next[k]=pts.map(p=>Array.isArray(p)?{x:p[0],y:p[1]}:{x:p.x,y:p.y});
                }
            }
            this.allCurves=next;
            this._pendingPt=-1;
            this.redrawCurve();
            this.propagateCurves?.();
            this.updateHistogram?.();
        }catch(e){
            console.warn("[CurvesPro] reload from json failed:",e);
        }
    };

    node.serialize=function(){
        const d=_origSerialize?_origSerialize.call(this):{};
        d.curves_pro_curves=node.allCurves;
        d.curves_snap=node._snapEnabled;
        d.curves_grid=node._gridLevel;
        return d;
    };
    node.configure=function(data){
        if(_origConfigure) _origConfigure.call(this,data);
        buildWidgets();
        if(data?.curves_pro_curves){
            Object.assign(node.allCurves,data.curves_pro_curves);
            ["luma","sat","mask"].forEach(k=>delete node.allCurves[k]);
            const cjw=this.widgets?.find(w=>w.name==="all_curves_json");
            if(cjw){const s={};for(const k in node.allCurves) s[k]=node.allCurves[k].map(p=>[p.x,p.y]);cjw.value=JSON.stringify(s);}
        }
        if(data?.curves_snap!=null){
            node._snapEnabled=data.curves_snap;
            setActive(btnSnap,node._snapEnabled,"#8f8","#1a3a1a");
        }
        if(data?.curves_grid!=null){
            node._gridLevel=data.curves_grid;
            btnGrid.textContent=GRID_LABELS[node._gridLevel];
        }
    };
    buildWidgets();
}


// ============================================================================
//  NŒUD 2 : PyCodeMax_CurvesProImage
//  UI en 2 onglets [Original / Modifié] au-dessus d'un canvas unique.
//  Le switch entre onglets ne recharge rien, il change juste ce qui est peint.
// ============================================================================
function setupCurvesProImage(node) {
    const _origConfigure=node.configure?.bind(node);

    node._sourceImage  = null;
    node._previewImage = null;
    node._displayMode  = "preview";   // "source" | "preview"

    function calcHeight(nodeW,iw,ih){ return(!iw||!ih)?180:Math.max(120,Math.round(nodeW*ih/iw)); }

    // ── DOM : onglets + canvas ─────────────────────────────────────────────
    const wrap=document.createElement("div");
    wrap.style.cssText="width:100%;overflow:hidden;display:flex;flex-direction:column;gap:4px;";

    // Barre d'onglets (2 boutons pilule)
    const tabs=document.createElement("div");
    tabs.style.cssText="display:flex;gap:4px;padding:4px 6px 0;flex-shrink:0;";

    function makeTab(label, mode){
        const b=document.createElement("button");
        b.textContent=label;
        b.dataset.mode=mode;
        b.style.cssText="flex:1;font-size:11px;padding:4px 10px;border-radius:14px;border:1px solid #555;background:#2b2b2b;color:#aaa;cursor:pointer;transition:background .15s,color .15s;";
        b.onmouseenter=()=>{ if(node._displayMode!==mode) b.style.background="#3a3a3a"; };
        b.onmouseleave=()=>{ if(node._displayMode!==mode) b.style.background="#2b2b2b"; };
        b.onclick=(e)=>{
            e.stopPropagation();
            node._displayMode=mode;
            updateTabs();
            node.redrawPreview();
        };
        return b;
    }

    const tabSource=makeTab("Original","source");
    const tabPreview=makeTab("Modifié","preview");
    tabs.appendChild(tabSource);
    tabs.appendChild(tabPreview);

    function updateTabs(){
        for(const b of [tabSource, tabPreview]){
            if(b.dataset.mode===node._displayMode){
                b.style.background="#1a3a5a";
                b.style.color="#cfe6ff";
                b.style.borderColor="#3a6080";
            } else {
                b.style.background="#2b2b2b";
                b.style.color="#aaa";
                b.style.borderColor="#555";
            }
        }
    }

    const cv=document.createElement("canvas");
    cv.style.cssText="display:block;width:100%;border-radius:8px;";

    wrap.appendChild(tabs);
    wrap.appendChild(cv);

    const TABS_H=28;

    const domWidget=node.addDOMWidget("preview_canvas","div",wrap,{
        computeSize(nodeW){
            const src=(node._displayMode==="preview"?node._previewImage:node._sourceImage)||node._sourceImage;
            const h=calcHeight(nodeW,src?.naturalWidth||0,src?.naturalHeight||0);
            cv.style.height=h+"px";
            return[nodeW,h+TABS_H+4];
        },
        getValue(){return"";},setValue(){},
    });

    node.redrawPreview=function(){
        const W=cv.offsetWidth||300;
        // En mode "preview" on affiche _previewImage, fallback sur source si pas encore calculé.
        // En mode "source" on affiche toujours _sourceImage.
        let src=null;
        let badge="";
        if(this._displayMode==="preview"){
            src=this._previewImage||this._sourceImage;
            badge=this._previewImage?"Modifié":"(en attente)";
        } else {
            src=this._sourceImage;
            badge="Original";
        }

        if(src&&src.complete&&src.naturalWidth){
            const iw=src.naturalWidth,ih=src.naturalHeight;
            const dispH=calcHeight(W,iw,ih);
            cv.width=W; cv.height=dispH; cv.style.height=dispH+"px";
            const ctx=cv.getContext("2d");
            ctx.clearRect(0,0,W,dispH);
            const sc=Math.min(W/iw,dispH/ih);
            const dw=iw*sc,dh=ih*sc;
            ctx.drawImage(src,(W-dw)/2,(dispH-dh)/2,dw,dh);

            // Badge en bas : dimensions + statut
            ctx.font="11px Arial";
            ctx.fillStyle="rgba(0,0,0,0.55)";
            const label=`${iw} × ${ih}  •  ${badge}`;
            const tw=ctx.measureText(label).width;
            ctx.fillRect((W-tw)/2-4, dispH-18, tw+8, 15);
            ctx.fillStyle="rgba(255,255,255,0.8)";
            ctx.textAlign="center";ctx.textBaseline="bottom";
            ctx.fillText(label,W/2,dispH-4);

            domWidget.computeSize?.(W);
            app.graph?.setDirtyCanvas(true,true);
        } else {
            cv.width=W;cv.height=180;cv.style.height="180px";
            const ctx=cv.getContext("2d");
            ctx.clearRect(0,0,W,180);
            ctx.font="13px Arial";ctx.fillStyle="rgba(150,150,150,0.6)";
            ctx.textAlign="center";ctx.textBaseline="middle";
            ctx.fillText("Sélectionnez une image",W/2,90);
        }
    };

    node.loadSourceImage=function(filename){
        if(!filename||filename==="(aucune image)") return;
        this._sourceImage=null;this._previewImage=null;
        this.redrawPreview();
        const img=new Image();
        img.onload=()=>{
            this._sourceImage=img;this._previewImage=null;
            this.redrawPreview();
            this._applyCurrentCurves();
        };
        img.onerror=()=>console.warn("[CurvesProImage] image non trouvée:",filename);
        img.src=`/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=`;
    };

    node._applyCurrentCurves=function(){
        const curveNodes=findCurveProNodes(this);
        for(const cn of curveNodes){
            const cjw=cn.widgets?.find(w=>w.name==="all_curves_json");
            if(cjw?.value) this.applyLiveCurves(cjw.value);
        }
        if(!curveNodes.length) this.redrawPreview();
    };

    node.applyLiveCurves=async function(curvesJson){
        if(!this._sourceImage) return;
        clearTimeout(this._liveDebounce);
        this._liveDebounce=setTimeout(async()=>{
            const result=await apiApply(this._sourceImage,curvesJson);
            if(result){
                this._previewImage=result;this.redrawPreview();
                for(const cn of findCurveProNodes(this)){
                    cn.updateHistogram?.();cn.redrawCurve?.();
                }
            }
        },60);
    };

    // Hook sur le widget image — intercept callback + masque widget natif
    function hookImageWidget(){
        // Masquer les widgets de type "image" résiduel (Node 1.0)
        if(node.widgets){
            for(const w of node.widgets){
                if((w.type==="image"||(w.type==="DOM"&&w.name!=="preview_canvas"))&&w.element){
                    w.element.style.cssText="display:none!important;height:0!important;";
                    w.computeSize=()=>[0,-4]; w.hidden=true;
                }
            }
        }
        const imgW=node.widgets?.find(w=>w.name==="image");
        if(!imgW) return;
        const prev=imgW.callback;
        imgW.callback=function(value){
            if(prev) prev.call(this,value);
            node.loadSourceImage(value);
        };
        if(imgW.value&&imgW.value!=="(aucune image)"){
            setTimeout(()=>node.loadSourceImage(imgW.value),200);
        }
    }

    new ResizeObserver(()=>requestAnimationFrame(()=>node.redrawPreview())).observe(wrap);

    node.configure=function(data){
        if(_origConfigure) _origConfigure.call(this,data);
        setTimeout(()=>{hookImageWidget();updateTabs();node.redrawPreview();},200);
    };
    updateTabs();
    setTimeout(()=>{hookImageWidget();node.redrawPreview();},200);
}


// ============================================================================
//  Enregistrement
// ============================================================================
app.registerExtension({
    name:"Orion4d.CurvesPro",

    async beforeRegisterNodeDef(nodeType,nodeData){
        // Note : en v9, le widget "preset" ComfyUI a disparu du Python.
        // Les presets sont gérés par color_fx_presets.js qui injecte ses
        // propres widgets. Pas de pré-peuplement à faire ici.

        // Pour CurvesProImage : supprimer l'aperçu natif en retirant le
        // onNodeCreated d'origine (qui injecte le widget image_upload preview)
        // et en remplaçant par notre propre setup.
        if(nodeData.name==="PyCodeMax_CurvesProImage"){
            // On intercepte onDrawBackground pour ne pas dessiner l'aperçu natif
            const origOnDrawBg=nodeType.prototype.onDrawBackground;
            nodeType.prototype.onDrawBackground=function(ctx){
                // Ne pas appeler l'original qui dessine l'image LiteGraph native
                // (uniquement si notre canvas DOM est présent)
                const hasOurWidget=this.widgets?.find(w=>w.name==="preview_canvas");
                if(!hasOurWidget && origOnDrawBg) origOnDrawBg.call(this,ctx);
            };
        }
    },

    nodeCreated(node){
        if(node.comfyClass==="PyCodeMax_CurvesPro")      setupCurvesPro(node);
        if(node.comfyClass==="PyCodeMax_CurvesProImage") setupCurvesProImage(node);
    },
});


// ============================================================================
//  Réception preview WS (après exécution Python)
//
//  Le message "orion4d.curves_pro_preview" est envoyé par deux nodes :
//   - CurvesProImage : quand une image est chargée, pour permettre au canvas
//                      CurvesPro source (en amont) de faire ses previews live
//   - CurvesPro      : en mode hybride, quand image_in est branché, pour que
//                      son propre canvas puisse faire ses previews live sans
//                      dépendre d'un CurvesProImage en aval
// ============================================================================
api.addEventListener("orion4d.curves_pro_preview",({detail})=>{
    if(!app.graph||!detail.image_data) return;
    const targetNode=app.graph.getNodeById(detail.node_id);
    if(!targetNode) return;

    const img=new Image();
    img.onload=async()=>{
        // Cas 1 : la cible est un CurvesProImage (mode legacy)
        if(targetNode.comfyClass==="PyCodeMax_CurvesProImage"){
            targetNode._sourceImage=img;
            targetNode._previewImage=null;
            targetNode.redrawPreview?.();
            for(const cn of findCurveProNodes(targetNode)){
                await cn.updateHistogram?.();
                cn.redrawCurve?.();
                const cjw=cn.widgets?.find(w=>w.name==="all_curves_json");
                if(cjw?.value) targetNode.applyLiveCurves?.(cjw.value);
            }
            return;
        }

        // Cas 2 : la cible est un CurvesPro en mode hybride. Le canvas
        // stocke l'image source directement et met à jour son histogramme.
        if(targetNode.comfyClass==="PyCodeMax_CurvesPro"){
            targetNode._hybridSourceImage=img;
            // Déclenche l'histogramme (la fonction updateHistogram lit
            // _hybridSourceImage en priorité, voir patch dans setupCurvesPro)
            targetNode.updateHistogram?.();
            targetNode.redrawCurve?.();
            return;
        }
    };
    img.src="data:image/png;base64,"+detail.image_data;
});

// --- END OF FILE curves_pro.js ---