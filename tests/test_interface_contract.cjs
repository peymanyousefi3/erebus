// Interface customization regression checks maintained by Peyman Yousefi.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../game/plugins/robot_windows/MainSupervisorWindow/MainSupervisorWindow.js'), 'utf8');
const nodes = new Map();
const get = id => { if (!nodes.has(id)) nodes.set(id, {checked:false, value:'', disabled:false}); return nodes.get(id); };
const sent = [];
let download, blob;
const context = {
    document: {getElementById:get, querySelectorAll:() => rows, createElement:() => ({click(){}, remove(){}}), body:{appendChild:a => {download=a;}}},
    robotWindow:{send:message => sent.push(message)},
    updateTestBtnState(){}, setEnableButton:(id, enabled) => {get(id).disabled=!enabled;},
    disableWhileSending(){}, setMatchState(){}, showSourceStatus(){}, closeWorkspace(){},
    Blob, URL:{createObjectURL:b => {blob=b; return 'blob:test';}, revokeObjectURL(){}}, setTimeout(){},
};
context.window=context;
const between = (start,end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
vm.runInNewContext('let matchStarted=false;let dockerStarting=false;'+
    between('function setEnableRemoteBtn()', 'function startup ()')+
    between('window.configChanged = ', 'function calculateTimeRemaining')+
    between('function setDockerStarting(', 'window.pausePressed')+
    between('window.enableRemotePressed = ', 'function enableTestButton')+
    between('window.exportEventCsv = ', 'function resetHistory'),context);
get('remoteMode').checked=true;
context.configChanged();
assert.deepEqual(sent.filter(s=>s==='remoteDisable'),[]);
get('keepRemote').checked=true;context.configChanged('keepRemote');
assert(sent.includes('remoteEnable'));
get('dockerPath').value='C:\\Team, Demo\\path%20literal';context.configChanged();
const fields=sent.filter(s=>s.startsWith('config,')).at(-1).split(',').slice(1);
assert.equal(fields.length,12);assert.equal(decodeURIComponent(fields[6].slice(4)),get('dockerPath').value);
sent.length=0;context.runDockerPressed();context.runDockerPressed();
assert.equal(sent.filter(s=>s.startsWith('runDocker,')).length,1);
assert(get('runDockerButton').disabled);
const rows=[['00:02','Victim, "A"\nidentified'],['00:01','Checkpoint reached']].map(record=>({cells:record.map(text=>({textContent:text}))}));
context.exportEventCsv();
(async()=>{
    const csv=Buffer.from(await blob.arrayBuffer()).toString('utf8');
    assert.equal(csv,'\uFEFF"Timestamp","Event"\r\n"00:01","Checkpoint reached"\r\n"00:02","Victim, ""A""\nidentified"\r\n');
    assert(download.download.endsWith('.csv'));
    console.log('PASS: Remote isolation, Keep Remote, Docker path encoding/pending guard, chronological escaped CSV.');
})().catch(error=>{console.error(error);process.exitCode=1;});
