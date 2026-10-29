// Erebus interface customizations by Peyman Yousefi.
/* Shared by the live supervisor and the self-contained saved review. */
(() => {
    'use strict';
    const $ = id => document.getElementById(id);
    const canvas = $('map'), ctx = canvas.getContext('2d');
    let report = null, turns = 0, scale = 24, fitScale = 24, panX = 0, panY = 0;
    let width = 0, height = 0, selected = null, pointer = null;
    const labels = ['Incorrect', 'Correct', 'Ignored by scoring', 'Unscored / outside comparison'];
    const palette = {'0':'#e2e8ef','1':'#263b60','2':'#323b4a','3':'#af813d','4':'#7d91ad','5':'#008c81','b':'#4267c7','y':'#b69a18','g':'#4c9664','p':'#8a59aa','o':'#c4783e','r':'#b85d5d'};
    function dimensions() {
        const h = report.values.length, w = report.values[0].length;
        return turns % 2 ? [h, w] : [w, h];
    }
    function transformed(row, col) {
        const h = report.values.length, w = report.values[0].length;
        if (turns === 1) return [h - 1 - row, col];
        if (turns === 2) return [w - 1 - col, h - 1 - row];
        if (turns === 3) return [row, w - 1 - col];
        return [col, row];
    }
    function original(x, y) {
        const h = report.values.length, w = report.values[0].length;
        if (turns === 1) return [h - 1 - x, y];
        if (turns === 2) return [h - 1 - y, w - 1 - x];
        if (turns === 3) return [x, w - 1 - y];
        return [y, x];
    }
    function drawMap(context, cell, ox, oy, viewportW, viewportH) {
        const [w,h] = dimensions();
        const x0 = Math.max(0,Math.floor(-ox/cell)), y0 = Math.max(0,Math.floor(-oy/cell));
        const x1 = Math.min(w,Math.ceil((viewportW-ox)/cell)), y1 = Math.min(h,Math.ceil((viewportH-oy)/cell));
        context.save();
        for (let y=y0;y<y1;y++) for(let x=x0;x<x1;x++) {
            const [r,c] = original(x,y), value = report.values[r][c], status = report.status[r][c];
            const outside=status===3 && report.expected[r][c]===null;
            if(outside && (value===null || value==='0'))continue;
            const extra=outside && value!==null && value!=='0';
            const px=ox+x*cell, py=oy+y*cell;
            context.globalAlpha = status === 0 || extra ? 1 : status === 1 ? .08 : .035;
            context.fillStyle = extra ? '#fff1d6' : status === 0 ? (value === null ? '#fff1d6' : '#fbd6d1') : (palette[value] || '#7d9ba6');
            context.fillRect(px,py,cell,cell);
            if (value === null && status !== 0) context.clearRect(px,py,cell,cell);
            context.globalAlpha = 1;
            context.strokeStyle = extra ? '#b5760d' : status === 0 ? (value === null ? '#b5760d' : '#b83732') : '#f0f2f5';
            context.lineWidth = status === 0 || extra ? Math.max(1, Math.min(2,cell/10)) : .5;
            if(status === 0 || extra || cell >= 4) context.strokeRect(px+.5,py+.5,Math.max(0,cell-1),Math.max(0,cell-1));
            if (cell >= 13 && (status === 0 || (value !== null && value !== '0'))) {
                context.globalAlpha = status === 0 || extra ? 1 : .18;
                context.fillStyle = extra ? '#83520a' : status === 0 ? '#862f2a' : '#243655';
                context.font = `600 ${Math.min(16, cell*.43)}px Arial`;
                context.textAlign='center'; context.textBaseline='middle';
                context.fillText(value === null ? '∅' : value,px+cell/2,py+cell/2,cell*.88);
            }
        }
        context.globalAlpha = 1;
        if (selected) {
            const [x,y] = transformed(...selected);
            context.strokeStyle='#007e8b';context.lineWidth=3;
            context.strokeRect(ox+x*cell-1,oy+y*cell-1,cell+2,cell+2);
        }
        context.restore();
    }
    function draw() {
        ctx.clearRect(0,0,width,height);
        if(!report) return;
        drawMap(ctx,scale,panX,panY,width,height);
        $('zoom').textContent = `${Math.round(scale/fitScale*100)}%`;
        $('orientation').textContent = `${turns*90}° clockwise`;
    }
    function fit() {
        if(!report) return;
        closePopup();
        const [w,h] = dimensions();
        scale = fitScale = Math.min((width-48)/w,(height-48)/h);
        panX=(width-w*scale)/2;panY=(height-h*scale)/2;draw();
    }
    function resize() {
        const rect=canvas.getBoundingClientRect(), dpr=window.devicePixelRatio || 1;
        if(rect.width<=0 || rect.height<=0) return;
        width=rect.width;height=rect.height;
        canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
        ctx.setTransform(dpr,0,0,dpr,0,0);fit();
    }
    function zoom(factor, x=width/2, y=height/2) {
        if(!report) return;
        closePopup();
        const next=Math.max(fitScale*.2,Math.min(Math.max(160,fitScale*8),scale*factor));
        const ratio=next/scale;
        panX=x-(x-panX)*ratio;panY=y-(y-panY)*ratio;scale=next;draw();
    }
    function rotate(direction) { if(report){turns=(turns+direction+4)%4;fit();} }
    const names={'0':'Normal floor','1':'Wall','2':'Hole','3':'Swamp','4':'Checkpoint','5':'Start tile','20':'Ignored cell','H':'Victim marker','S':'Victim marker','U':'Victim marker'};
    function description(value) { return value===null ? 'Missing cell' : `${names[value] || 'Map code'} (${value})`; }
    function closePopup(focus=false) {
        $('cellPopup').hidden=true;selected=null;$('selection').textContent='';draw();
        if(focus)canvas.focus({preventScroll:true});
    }
    function inspect(r,c) {
        selected=[r,c];
        const rr=r-report.raw_origin[0], cc=c-report.raw_origin[1], value=report.values[r][c];
        $('cell-title').textContent=value===null?'Missing reported cell':`Row ${rr}, column ${cc}`;
        $('coordinates').textContent=value===null?`Aligned position: ${r}, ${c}`:'Original matrix coordinates (zero-based)';
        $('reported').textContent=description(value);
        $('expected').textContent=report.expected[r][c]===null?'Outside scoring area':description(report.expected[r][c]);
        const outside=report.expected[r][c]===null;
        $('status').textContent=outside?'Outside official comparison (not scored)':labels[report.status[r][c]];
        $('cell-help').textContent=outside?'Erebus does not score this cell. It is shown because the robot reported a non-zero value.':value===null?'The expected map contains this location, but the submitted matrix does not.':'';
        $('selection').textContent=value===null?'Missing reported cell':`Selected cell: ${rr}, ${cc}`;
        const popup=$('cellPopup');popup.hidden=false;
        const [x,y]=transformed(r,c),cx=panX+(x+.5)*scale,cy=panY+(y+.5)*scale;
        const pw=popup.offsetWidth,ph=popup.offsetHeight;
        let left=cx+scale/2+12;
        if(left+pw>width-8) left=cx-scale/2-pw-12;
        left=Math.max(8,Math.min(width-pw-8,left));
        let top=cy-ph/2;
        if(left<cx+scale/2 && left+pw>cx-scale/2) {
            top=cy+scale/2+12;
            if(top+ph>height-8) top=cy-scale/2-ph-12;
        }
        popup.style.left=`${left}px`;
        popup.style.top=`${Math.max(8,Math.min(height-ph-8,top))}px`;
        draw();popup.focus({preventScroll:true});
    }
    $('closeCell').onclick=()=>closePopup(true);
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('cellPopup').hidden){e.preventDefault();closePopup(true);}});
    document.addEventListener('pointerdown',e=>{if(!e.target.closest('#cellPopup')&&e.target!==canvas&&!$('cellPopup').hidden)closePopup();});
    function download(content,name,type) {
        const url=URL.createObjectURL(content instanceof Blob ? content : new Blob([content],{type}));
        const a=document.createElement('a');a.href=url;a.download=name;a.click();
        setTimeout(()=>URL.revokeObjectURL(url),30000);
    }
    function saveImage() {
        if(!report) return;
        const [w,h]=dimensions(), cell=Math.min(30,7800/Math.max(w,h));
        const image=document.createElement('canvas');image.width=Math.max(760,w*cell+64);image.height=h*cell+180;
        const context=image.getContext('2d');context.fillStyle='#f8fafc';context.fillRect(0,0,image.width,image.height);
        context.fillStyle='#1b2b54';context.font='bold 24px Arial';context.fillText('Erebus · Submitted map review',32,38);
        context.font='14px Arial';context.fillText(`${(report.correctness*100).toFixed(2)}% correct · Evaluated at ${report.timestamp} · View ${turns*90}° clockwise`,32,65);
        context.fillText(`${report.counts.incorrect} incorrect · ${report.counts.correct} correct · ${report.counts.ignored} ignored`,32,89);
        const previous=selected;selected=null;drawMap(context,cell,32,112,image.width,image.height);selected=previous;
        context.fillStyle='#52617a';context.font='12px Arial';context.textAlign='left';context.textBaseline='alphabetic';
        context.fillText('Red: scored error · Gold: missing or outside comparison · Faded: correct / ignored · Raw matrix unchanged.',32,image.height-22);
        image.toBlob(blob=>{if(blob)download(blob,'map-review.png','image/png');else $('notice').textContent='Image export failed. Please try again.';},'image/png');
    }
    function trimZeroPadding(data) {
        // Rebuild from the full raw matrix, so even previously cropped reports retain non-zero entries.
        let ay=data.expected.length,ax=data.expected[0].length,ab=0,ar=0;
        for(let r=0;r<data.expected.length;r++) for(let c=0;c<data.expected[r].length;c++) {
            if(data.expected[r][c]!==null){ay=Math.min(ay,r);ax=Math.min(ax,c);ab=Math.max(ab,r+1);ar=Math.max(ar,c+1);}
        }
        if(ab===0)return data;
        const raw=data.reported_matrix,dy=data.raw_origin[0]-ay,dx=data.raw_origin[1]-ax,ah=ab-ay,aw=ar-ax;
        let top=ah,left=aw,bottom=0,right=0;
        for(let r=ay;r<ab;r++) for(let c=ax;c<ar;c++) if(data.expected[r][c]!==null&&data.expected[r][c]!=='0') {
            const y=r-ay,x=c-ax;top=Math.min(top,y);left=Math.min(left,x);bottom=Math.max(bottom,y+1);right=Math.max(right,x+1);
        }
        for(let r=0;r<raw.length;r++) for(let c=0;c<raw[r].length;c++) if(raw[r][c]!=='0') {
            top=Math.min(top,dy+r);left=Math.min(left,dx+c);bottom=Math.max(bottom,dy+r+1);right=Math.max(right,dx+c+1);
        }
        if(bottom<=top||right<=left)return data;
        const view={...data,raw_origin:[dy-top,dx-left],values:[],expected:[],status:[],outside_nonzero:0};
        for(let y=top;y<bottom;y++) {
            const values=[],answers=[],statuses=[];
            for(let x=left;x<right;x++) {
                const rr=y-dy,cc=x-dx,inside=y>=0&&x>=0&&y<ah&&x<aw;
                const value=rr>=0&&cc>=0&&rr<raw.length&&cc<raw[0].length?raw[rr][cc]:null;
                values.push(value);answers.push(inside?data.expected[y+ay][x+ax]:null);statuses.push(inside?data.status[y+ay][x+ax]:3);
                if(!inside&&value!==null&&value!=='0')view.outside_nonzero++;
            }
            view.values.push(values);view.expected.push(answers);view.status.push(statuses);
        }
        return view;
    }
    function load(data) {
        if(!data || !Array.isArray(data.values) || !data.values.length || !data.values[0].length) return;
        data=trimZeroPadding(data);
        report=data;turns=0;selected=null;
        $('correctness').textContent=`${(data.correctness*100).toFixed(2)}%`;
        $('submission').textContent=`${data.values.length} × ${data.values[0].length} displayed; ${data.reported_matrix.length} × ${data.reported_matrix[0].length} submitted. Evaluated at ${data.timestamp}.`;
        for(const key of ['correct','incorrect','ignored']) $(key).textContent=data.counts[key];
        $('outsideCount').textContent=data.outside_nonzero || 0;
        $('outsideSummary').hidden=!data.outside_nonzero;
        $('empty').hidden=true;
        for(const id of ['left','right','out','in','fit','raw','image']) $(id).disabled=false;
        $('notice').textContent=data.warning || 'Click a cell for details. Drag to pan.';
        $('cellPopup').hidden=true;
        for(const id of ['reported','expected','coordinates','status']) $(id).textContent='—';
        $('selection').textContent='';resize();
    }
    $('left').onclick=()=>rotate(-1);$('right').onclick=()=>rotate(1);
    $('out').onclick=()=>zoom(1/1.25);$('in').onclick=()=>zoom(1.25);$('fit').onclick=fit;
    $('raw').onclick=()=>{if(report)download(JSON.stringify(report.reported_matrix,null,2)+'\n','reported-map.json','application/json');};
    $('image').onclick=saveImage;
    canvas.addEventListener('pointerdown',e=>{if(report){pointer={id:e.pointerId,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,moved:false};canvas.setPointerCapture(e.pointerId);canvas.focus({preventScroll:true});}});
    canvas.addEventListener('pointermove',e=>{if(pointer && pointer.id===e.pointerId){if(Math.hypot(e.clientX-pointer.startX,e.clientY-pointer.startY)>4)closePopup();const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;panX+=dx;panY+=dy;pointer.x=e.clientX;pointer.y=e.clientY;pointer.moved ||= Math.hypot(e.clientX-pointer.startX,e.clientY-pointer.startY)>4;draw();}});
    canvas.addEventListener('pointerup',e=>{
        if(!pointer || pointer.id!==e.pointerId) return;
        if(!pointer.moved){const rect=canvas.getBoundingClientRect();const [r,c]=original(Math.floor((e.clientX-rect.left-panX)/scale),Math.floor((e.clientY-rect.top-panY)/scale));if(r>=0&&c>=0&&r<report.values.length&&c<report.values[0].length)inspect(r,c);}
        pointer=null;
    });
    canvas.addEventListener('pointercancel',()=>{pointer=null;});
    canvas.addEventListener('wheel',e=>{if(report){e.preventDefault();const rect=canvas.getBoundingClientRect();zoom(e.deltaY<0?1.1:1/1.1,e.clientX-rect.left,e.clientY-rect.top);}},{passive:false});
    canvas.addEventListener('keydown',e=>{
        if(!report) return;
        if(e.key==='+'||e.key==='=') zoom(1.25);else if(e.key==='-') zoom(1/1.25);
        else if(e.key.toLowerCase()==='r')rotate(e.shiftKey?-1:1);else if(e.key==='Home')fit();
        else if(e.key.startsWith('Arrow')){panX+=e.key==='ArrowLeft'?32:e.key==='ArrowRight'?-32:0;panY+=e.key==='ArrowUp'?32:e.key==='ArrowDown'?-32:0;draw();}else return;
        e.preventDefault();
    });
    new ResizeObserver(resize).observe(canvas.parentElement);
    window.addEventListener('message',event=>{if(event.source===window.parent && event.data?.type==='erebus-map-review')load(event.data.report);});
    const saved=$('saved-review');if(saved)load(JSON.parse(saved.textContent));
})();
