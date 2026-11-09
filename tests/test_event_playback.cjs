// Run with Node.js; checks the exported callback without a browser or simulation.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const page = fs.readFileSync(process.argv[2], 'utf8');
const events = JSON.parse(page.match(/id="match-event-data">(.*?)<\/script>/s)[1]);
const script = page.match(/<script>\n(.*?)<\/script>/s)[1];
const output = {textContent: ''};
let callback;
vm.runInNewContext(script, {
  document: {
    getElementById: id => id === 'match-event-data' ? {textContent: JSON.stringify(events)} : output,
    querySelector: () => ({isConnected: true, setAnimationStepCallback: fn => {callback = fn; return true;}})
  },
  customElements: {whenDefined: () => ({then: fn => fn()})}
});
for (const time of [0, 56000, 200000, 419456, 10000, 330000, 0]) {
  callback(time);
  const expected = events.filter(e => e.playback_time_ms <= time).at(-1);
  assert.equal(output.textContent, expected ? `${expected.timestamp} — ${expected.text}` : 'No events yet');
}
// Boundaries include the event at its timestamp and the last entry at a shared timestamp.
for (const event of events) {
  for (const time of [event.playback_time_ms - 1, event.playback_time_ms]) {
    callback(time);
    const expected = events.filter(e => e.playback_time_ms <= time).at(-1);
    assert.equal(output.textContent, expected ? `${expected.timestamp} — ${expected.text}` : 'No events yet');
  }
}
console.log('PASS: forward/backward seeks, restart, timestamp boundaries and simultaneous events.');
