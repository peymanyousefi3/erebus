const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('game/plugins/robot_windows/MainSupervisorWindow/MainSupervisorWindow.js','utf8');
const native=[],requests=[];
class RobotWindow {constructor(){this.socket={};this.connect();}connect(){this.send('init robot window');}send(message){native.push(message);}}
const context={RobotWindow,window:{erebusReferee:{base:'/private-session/'}},fetch:async(url,options)=>{requests.push([url,options.body]);return {ok:true};},showSourceStatus(){throw Error('Unexpected transport failure');}};
const Referee=vm.runInNewContext(source.slice(source.indexOf('class RefereeRobotWindow'),source.indexOf('let matchStarted'))+';RefereeRobotWindow',context);
(async()=>{const referee=new Referee();referee.send('config,normal');referee.send('run');referee.send('pause');await referee.commandQueue;
assert.deepEqual(native,['init robot window']);
assert.deepEqual(requests,[['/private-session/commands','config,normal'],['/private-session/commands','run'],['/private-session/commands','pause']]);
assert(source.includes('if (!window.erebusReferee)'));
assert(!source.includes('http://127.0.0.1:60520/'));
console.log('PASS: private referee command transport preserves order; only WebSocket initialization uses Webots; uploads stay on the authenticated origin.');
})().catch(error=>{console.error(error);process.exitCode=1;});
