const fs=require('fs'), path=require('path');
const {JSDOM}=require('jsdom');
const INDEX=process.env.INDEX||path.join(__dirname,'..','index.html');
let html=fs.readFileSync(INDEX,'utf8');
// expose internals for testing
html=html.replace('/* ========================= init ========================= */',
  'window.__api={results:()=>results(),DATA:()=>DATA,SESSION:()=>SESSION,addToSession:(id)=>addToSession(id),loadPreset:(id)=>loadPreset(id),calcItem:(it)=>calcItem(it),setView:(v)=>setView(v),clear:()=>{SESSION={meta:{candidate:"",position:"",interviewer:"",date:"2026-01-01",notes:""},items:[]};}};\n/* init */');

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

    console.log("\n"+(fails===0?"ALL TESTS PASSED ✓":fails+" TEST(S) FAILED ✗"));
    process.exit(fails===0?0:1);
  }catch(e){ console.error("ERROR during test:",e); process.exit(2); }
},500);
