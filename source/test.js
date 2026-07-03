const fs=require('fs'), path=require('path');
const {JSDOM}=require('jsdom');
const INDEX=process.env.INDEX||path.join(__dirname,'..','index.html');
let html=fs.readFileSync(INDEX,'utf8');
// expose internals for testing
html=html.replace('/* ========================= init ========================= */',
  'window.__api={results:()=>results(),DATA:()=>DATA,SESSION:()=>SESSION,addToSession:(id)=>addToSession(id),loadPreset:(id)=>loadPreset(id),calcItem:(it)=>calcItem(it),setView:(v)=>setView(v),applyRemote:(s)=>applyRemoteSession(s),addChat:(m,mine)=>addChat(m,mine),CHAT:()=>CHAT,simulateConnectedDrop:()=>{peerConnected=true;handleDisconnect();},resetCollab:()=>{peerLost=false;peerConnected=false;},clear:()=>{SESSION={meta:{candidate:"",position:"",interviewer:"",date:"2026-01-01",notes:""},items:[]};}};\n/* init */');

let fails=0; const ok=(c,m)=>{ if(c){console.log("  ok -",m);} else {console.log("  FAIL -",m);fails++;} };
const dom=new JSDOM(html,{runScripts:"dangerously",resources:undefined,url:"http://localhost/",pretendToBeVisual:true,
  beforeParse(w){ w.matchMedia=()=>({matches:false,addListener(){},removeListener(){}}); w.confirm=()=>true; w.prompt=()=>'Тестовый пресет'; }});
const w=dom.window, api=w.__api;
setTimeout(()=>{
  try{
    console.log("== init ==");
    ok(!!api,"internals exposed");
    const DATA=api.DATA();
    ok(DATA.questions.length===68,"68 questions loaded ("+DATA.questions.length+")");
    ok(DATA.categories.length===34,"34 categories ("+DATA.categories.length+")");
    ok(w.document.querySelectorAll('#prep-list,.qrow').length>0 || w.document.querySelector('#prepList').children.length>0,"prep list rendered");

    console.log("== scoring: single question ==");
    api.clear();
    const low=DATA.questions.find(q=>q.difficulty==='Low');
    api.addToSession(low.id);
    let S=api.SESSION();
    S.items[0].assessment='Уверенно знает';
    let r=api.results();
    ok(r.sum===1,"1 Low 'Уверенно знает' => sum 1 (got "+r.sum+")");
    S.items[0].corr=2;
    ok(api.calcItem(S.items[0])===3,"corr +2 => calc 3 (got "+api.calcItem(S.items[0])+")");

    console.log("== scoring: reproduce example thresholds 10/15/4 ==");
    api.clear(); S=api.SESSION();
    const pick=(d,n)=>DATA.questions.filter(q=>q.difficulty===d).slice(0,n);
    const sel=[...pick('Low',10),...pick('Medium',15),...pick('High',4)];
    ok(sel.length===29,"selected 29 questions (10/15/4)");
    sel.forEach(q=>api.addToSession(q.id));
    // assess everyone exactly at 'mid' expectation -> sum must equal mid threshold (44)
    const exp=DATA.expectations['mid'];
    api.SESSION().items.forEach(it=>{ it.assessment=exp[it.difficulty]; });
    r=api.results();
    ok(r.thr.jun===12.5 && r.thr.mid===44 && r.thr['mid+']===59 && r.thr.senior===67 && r.thr['senior+']===75,
       "thresholds = 12.5/44/59/67/75 (got "+JSON.stringify(r.thr)+")");
    ok(r.sum===44,"answering at mid-expectation => sum 44 (got "+r.sum+")");
    ok(r.nearest==='mid',"nearest grade = mid (got "+r.nearest+")");

    console.log("== bracket logic ==");
    // bump one High from 'Что-то слышал'(1) to 'Уверенно знает'(5): +4 => 48, between mid(44) and mid+(59)
    const oneHigh=api.SESSION().items.find(it=>it.difficulty==='High');
    oneHigh.assessment='Уверенно знает';
    r=api.results();
    ok(r.sum===48,"sum now 48 (got "+r.sum+")");
    ok(r.lower==='mid'&&r.upper==='mid+',"bracket mid..mid+ (got "+r.lower+".."+r.upper+")");
    ok(r.nearest==='mid',"48 closer to mid than mid+ (got "+r.nearest+")");

    console.log("== unassessed excluded from thresholds ==");
    api.clear();
    const twoLow=pick('Low',2); twoLow.forEach(q=>api.addToSession(q.id));
    api.SESSION().items[0].assessment='Уверенно знает'; // only 1 assessed
    r=api.results();
    ok(r.assessed.length===1 && r.counts.Low===1,"only assessed counts (assessed="+r.assessed.length+", Low="+r.counts.Low+")");
    ok(r.total===2,"total still 2");

    console.log("== render interview DOM ==");
    api.setView('interview');
    ok(w.document.querySelectorAll('#interviewList .icard').length===2,"2 interview cards rendered ("+w.document.querySelectorAll('#interviewList .icard').length+")");
    ok(w.document.querySelector('#resultsPanel .scale')!==null,"results scale rendered");
    const posSel=w.document.querySelector('#m_position');
    ok(posSel && posSel.tagName==='SELECT',"target grade is a <select> ("+(posSel?posSel.tagName:'-')+")");
    ok(posSel && [...posSel.options].some(o=>o.value==='senior+'),"grade dropdown has grade options");

    console.log("== presets ==");
    ok(DATA.presets&&DATA.presets.length>=1,"builtin preset present");
    const base=DATA.presets.find(p=>p.id==='builtin-base');
    ok(!!base && base.questionIds.length===29,"'base' preset has 29 ids ("+(base?base.questionIds.length:'-')+")");
    api.clear();
    api.loadPreset('builtin-base');
    let SP=api.SESSION();
    ok(SP.items.length===29,"loadPreset puts 29 into session ("+SP.items.length+")");
    const pc={Low:0,Medium:0,High:0}; SP.items.forEach(i=>pc[i.difficulty]++);
    ok(pc.Low===9&&pc.Medium===15&&pc.High===5,"preset distribution 9/15/5 (got "+JSON.stringify(pc)+")");
    const allFromBank=SP.items.every(i=>DATA.questions.some(q=>q.id===i.qid));
    ok(allFromBank,"all preset items resolve to bank questions");
    const noDup=new Set(SP.items.map(i=>i.qid)).size===29;
    ok(noDup,"no duplicate questions in preset");

    console.log("== comments & collapse ==");
    api.clear();
    DATA.questions.slice(0,2).forEach(x=>api.addToSession(x.id));
    let SC=api.SESSION();
    SC.items[0].comment='отвечал уверенно';
    SC.items[1].collapsed=true;
    api.setView('interview');
    ok(w.document.querySelector('#m_notes')!==null,"global notes textarea present");
    ok(w.document.querySelectorAll('#interviewList textarea[data-comment]').length===2,"per-question comment fields rendered");
    const firstCmt=w.document.querySelector('#interviewList textarea[data-comment]');
    ok(firstCmt && firstCmt.value==='отвечал уверенно',"comment value rendered into textarea");
    const cards=w.document.querySelectorAll('#interviewList .icard');
    ok(cards[1].classList.contains('collapsed'),"collapsed item gets .collapsed class");
    ok(!cards[0].classList.contains('collapsed'),"non-collapsed item stays expanded");
    ok(w.document.querySelector('.icard .mini [data-mini]')!==null,"collapsed-summary score element present");
    const tgl=w.document.querySelector('#toggleCollapse');
    ok(tgl!==null,"collapse/expand toggle button present");
    tgl.click(); SC=api.SESSION();
    ok(SC.items.every(it=>it.collapsed),"toggle → collapses all");
    ok((tgl.textContent||'').includes('Развернуть'),"toggle label flips to 'Развернуть все'");
    tgl.click(); SC=api.SESSION();
    ok(SC.items.every(it=>!it.collapsed),"toggle → expands all");

    console.log("== mobile nav ==");
    const nt=w.document.querySelector('#navToggle');
    ok(nt!==null,"mobile nav toggle button present");
    nt.click();
    ok(w.document.querySelector('header').classList.contains('nav-open'),"nav toggle opens menu");
    nt.click();
    ok(!w.document.querySelector('header').classList.contains('nav-open'),"nav toggle closes menu");
    nt.click();
    w.document.querySelector('.tab[data-view="bank"]').click();
    ok(!w.document.querySelector('header').classList.contains('nav-open'),"selecting a tab auto-closes menu");

    console.log("== collaboration + chat ==");
    ok(w.document.querySelector('#collabBtn')!==null,"collab button present in header");
    ok(w.document.querySelector('#chatFab')!==null && w.document.querySelector('#chatPanel')!==null,"chat fab + panel present");
    ok(w.document.querySelector('#chatFab').hidden===true,"chat fab hidden until connected");
    api.clear();
    api.applyRemote({meta:{candidate:'Удалённый',position:'mid',interviewer:'',date:'2026-01-01',notes:''},
      items:[{uid:'r1',qid:'q1',category:'Linux',difficulty:'Low',question:'Q1',keyPoints:['','',''],checks:[false,false,false],assessment:'Уверенно знает',corr:0,comment:'',collapsed:false}]});
    SC=api.SESSION();
    ok(SC.items.length===1 && SC.meta.candidate==='Удалённый',"remote session is adopted (two-way sync apply)");
    const n0=api.CHAT().length; api.addChat({name:'Коллега',text:'привет',ts:Date.now()},false);
    ok(api.CHAT().length===n0+1,"incoming chat message stored");
    ok(w.document.querySelector('#chatLog .chat-msg')!==null,"chat message rendered in log");
    const fab=w.document.querySelector('#chatFab'); fab.click();
    ok(w.document.querySelector('#chatPanel').hidden===false,"chat opens via fab");
    w.document.querySelector('#chatMin').click();
    ok(w.document.querySelector('#chatPanel').classList.contains('collapsed'),"minimize collapses chat panel");
    w.document.querySelector('#chatMin').click();
    ok(!w.document.querySelector('#chatPanel').classList.contains('collapsed'),"minimize toggles chat back open");
    w.document.querySelector('#chatClose').click();
    ok(w.document.querySelector('#chatPanel').hidden===true,"close (X) hides chat panel");
    const sb=w.document.querySelector('#chatSoundBtn');
    ok(sb!==null,"chat sound toggle present");
    const beforeIcon=sb.textContent; sb.click();
    ok(sb.textContent!==beforeIcon,"sound toggle flips icon");
    sb.click();
    ok(!/конструктор и оценка грейда/.test(w.document.querySelector('header').textContent),"header subtitle removed");
    api.addChat({name:'Коллега',text:'второе подряд',ts:Date.now()},false);
    const cmsgs=w.document.querySelectorAll('#chatLog .chat-msg');
    ok(cmsgs[cmsgs.length-1].classList.contains('grouped'),"consecutive same-author message is grouped");
    ok(cmsgs[cmsgs.length-1].querySelector('.chat-meta')===null,"grouped message omits repeated sender name");
    ok(cmsgs[0].querySelector('.chat-meta')!==null,"first message keeps sender name");
    w.document.querySelector('#collabBtn').click();
    ok(w.document.querySelector('#collabMyName')!==null,"own-name field present in collab modal");
    ok(/Интервьюер\(ы\)/.test(w.document.querySelector('#view-interview').textContent),"interviewer field labelled for two people");
    api.simulateConnectedDrop();
    ok(w.document.querySelector('#collabBtn').textContent==='🔴',"collab button shows lost state after drop");
    ok(w.document.querySelector('#cbRe')!==null,"reconnect button shown after drop");
    api.resetCollab();
    w.document.querySelector('#collabBtn').click();
    ok(w.document.querySelector('#diagCands')!==null && w.document.querySelector('#diagOut')!==null,"diagnostics panel present in collab modal");
    api.SESSION().resumeNotes=[{id:'rn1',page:2,quote:'Опыт Python 5 лет',comment:'уточнить проекты',ts:1}];
    api.setView('resume');
    ok(w.document.querySelector('#view-resume #resumeUploadBtn')!==null,"resume tab with PDF upload present");
    ok(/Опыт Python 5 лет/.test(w.document.querySelector('#resumeNotesPanel').textContent),"resume comment rendered with quote");
    ok(/уточнить проекты/.test(w.document.querySelector('#resumeNotesPanel').textContent),"resume comment text rendered");
    ok(/^v0\.3\.1/.test(w.document.querySelector('#verBadge').textContent),"version badge shows v0.3.1 ("+w.document.querySelector('#verBadge').textContent+")");
    ok(w.document.querySelector('#view-prep #btnExportCfg')!==null,"data import/export/reset moved to Подготовка");
    ok(w.document.querySelector('#view-matrix #btnExportCfg')===null,"data block removed from Матрицы");
    api.setView('help');
    ok(/История изменений/.test(w.document.querySelector('#view-help').textContent),"changelog section present in help");
    ok(/0\.1\.0/.test(w.document.querySelector('#view-help').textContent),"changelog lists 0.1.0");

    console.log("\n"+(fails===0?"ALL TESTS PASSED ✓":fails+" TEST(S) FAILED ✗"));
    process.exit(fails===0?0:1);
  }catch(e){ console.error("ERROR during test:",e); process.exit(2); }
},500);
