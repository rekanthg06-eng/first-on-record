// node shoot.js <outdir> <fps> [t1,t2,...]   (no times = every frame)
const {chromium}=require('playwright'); const http=require('http'),fs=require('fs'),path=require('path');
const out=process.argv[2], fps=+process.argv[3]||30, times=process.argv[4]?process.argv[4].split(',').map(Number):null;
fs.mkdirSync(out,{recursive:true});
const mime={'.js':'text/javascript','.mjs':'text/javascript','.html':'text/html','.json':'application/json','.glb':'model/gltf-binary'};
const srv=http.createServer((q,res)=>{const p=path.join(__dirname,decodeURIComponent(q.url.split('?')[0]));fs.readFile(p,(e,b)=>{if(e){res.writeHead(404);res.end();return}res.writeHead(200,{'content-type':mime[path.extname(p)]||'application/octet-stream'});res.end(b)})}).listen(8124,async()=>{
 const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const pg=await b.newPage({viewport:{width:1080,height:1920}}); pg.on('pageerror',e=>console.log('ERR',e.message));
 await pg.goto('http://localhost:8124/index.html'); await pg.waitForFunction('window.ready',null,{timeout:120000});
 const D=await pg.evaluate('window.fx.D'); const ts=times||Array.from({length:Math.floor(D*fps)+1},(_,i)=>i/fps);
 const t0=Date.now(); let n=0;
 for(const t of ts){ await pg.evaluate(`window.frame(${t})`); await pg.screenshot({path:path.join(out,times?`t${t.toFixed(2)}.png`:`f${String(n).padStart(5,'0')}.png`)}); n++; if(!times&&n%100==0)console.log(n,'/',ts.length,((Date.now()-t0)/1000).toFixed(0)+'s'); }
 console.log('frames',n,'D',D,'sec',(Date.now()-t0)/1000); await b.close(); srv.close(); });
