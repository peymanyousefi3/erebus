// Erebus interface customizations by Peyman Yousefi.
import RobotWindow from 'https://cyberbotics.com/wwi/R2023a/RobotWindow.js';

let matchStarted = false;
let dockerStarting = false;

function setMatchState(state) {
    const labels = {connecting: 'Connecting', ready: 'Ready', starting: 'Starting', running: 'Running', pausing: 'Pausing', paused: 'Paused', resetting: 'Resetting', finished: 'Finished'};
    const status = document.getElementById('matchState');
    status.textContent = labels[state];
    status.setAttribute('data-state', state);
}

function setFileState(id, message, loaded) {
    const field = document.getElementById(id === 0 ? 'controllerFileState' : 'robotFileState');
    field.textContent = message;
    field.title = message;
    field.setAttribute('data-loaded', String(loaded));
}

let selectedWorld = '';

const preparationPanels = {
    setup: ['setup', 'setup-panel'],
    settings: ['advancedSetup', 'settings-panel'],
    worlds: ['worlds', 'worlds-panel']
};
let activePanel = null;

function setPreparationPanel(name) {
    for (const [key, [buttonId, panelId]] of Object.entries(preparationPanels)) {
        const panel = document.getElementById(panelId);
        const button = document.getElementById(buttonId);
        const open = key === name;
        if (!open && panel.contains(document.activeElement)) button.focus({preventScroll: true});
        panel.hidden = !open;
        panel.inert = !open;
        button.setAttribute('aria-expanded', String(open));
    }
    activePanel = name;
    document.querySelector('.preparation').dataset.active = name || '';
    document.querySelector('.preparation-reveal').dataset.expanded = String(!!name);
}
window.closeWorkspace = function () { setPreparationPanel(null); };
window.togglePanel = function (name) {
    setPreparationPanel(activePanel === name ? null : name);
};

window.filterWorlds = function () {
    const query = document.getElementById('worldSearch').value.trim().toLowerCase();
    const buttons = document.querySelectorAll('#worlds_div .world-button');
    let visible = 0;
    for (const button of buttons) {
        button.hidden = !button.textContent.toLowerCase().includes(query);
        if (!button.hidden) visible++;
    }
    document.getElementById('worldsEmpty').hidden = visible !== 0;
    document.getElementById('worldResults').textContent = visible + (visible === 1 ? ' world' : ' worlds') + (query ? ' matching your search' : ' available');
};

window.selectWorld = function (name) {
    selectedWorld = name;
    document.getElementById('selectedWorldName').textContent = name.replace(/\.wbt$/, '').replace(/_/g, ' ');
    document.getElementById('loadSelectedWorld').disabled = false;
    for (const button of document.querySelectorAll('#worlds_div .world-button')) button.setAttribute('aria-pressed', String(button.getAttribute('data-world') === name));
};

window.loadSelectedWorld = function () {
    if (!selectedWorld) return;
    window.robotWindow.send('loadWorld,' + selectedWorld);
    window.closeWorkspace();
};

function showSourceStatus(message, error = false) {
    const status = document.getElementById("sourceReloadStatus");
    status.textContent = message;
    if (error) { window.closeWorkspace(); setSetupExpanded(true); }
    status.classList.toggle("source-error", error);
    status.setAttribute("role", error ? "alert" : "status");
}

function receive (message){
	//Receive message from the python supervisor
	//Split on comma
	var parts = message.split(",");
	console.log(parts);

	//If there is a message
	if (parts.length > 0){			
		switch (parts[0]){
			case "startup":
				//Call for set up the robot window
				startup();
				break;
			case "update":
				//Update the information on the robot window every frame (of game time)
				update(parts.slice(1,parts.length + 1));
				break;
            case "mapReviewAvailable":
                document.getElementById('viewMapReview').disabled = false;
                document.getElementById('mapReviewNotice').textContent = 'Map evaluated. Use Save and open map result at any time, including after the match.';
                document.getElementById('mapReviewNotice').setAttribute('role', 'status');
                break;
            case "mapReviewSaved":
                document.getElementById('viewMapReview').disabled = false;
                document.getElementById('mapReviewNotice').textContent = 'Map result saved: ' + parts.slice(1).join(',');
                document.getElementById('mapReviewNotice').setAttribute('role', 'status');
                break;
            case "mapReviewError":
                document.getElementById('viewMapReview').disabled = false;
                document.getElementById('mapReviewNotice').textContent = parts.slice(1).join(',');
                document.getElementById('mapReviewNotice').setAttribute('role', 'alert');
                break;
            case "config":
				//Load config data
				updateConfig(parts.slice(1,parts.length + 1));
				break;
            case "sourcePath":
                if (parts[1] === '0') document.getElementById("controllerSource").value = decodeURIComponent(parts.slice(2).join(','));
                break;
            case "sourceReloadStatus":
                showSourceStatus(parts.slice(1).join(','));
                break;
            case "sourceFileError":
                showSourceStatus(parts.slice(1).join(','), true);
                setFileState(1, 'Robot JSON could not be loaded', false);
                break;
            case "sourceReloadError":
                matchStarted = false;
                setMatchState('ready');
                setEnableButton("recording", true);
                showSourceStatus(parts.slice(1).join(','), true);
                setEnableButton("runButton", true);
                setEnableButton("load0", true);
                setEnableButton("unload0", true);
                setEnableButton("load1", true);
                setEnableButton("unload1", true);
                setEnableButton("pauseButton", false);
                setEnableButton("runDockerButton", true);
                setEnableButton("remoteMode", true);
                setEnableButton("dockerPath", true);
                setEnableButton("giveupB", false);
                setEnableButton("lopButton", false);
                break;
			case "unloaded0":
				//Robot 0's controller has been unloaded
				unloadedController(0);
				break;
			case "unloaded1":
				//Robot 1's controller has been unloaded
				unloadedController(1);
				break;
			case "loaded0":
				//Robot 0's controller has been unloaded
				loadedController(0);
				break;
			case "loaded1":
				//Robot 1's controller has been unloaded
				loadedController(1);
				break;
			case "ended":
				//The game is over
				endGame();
				break;
			case "historyUpdate":
				let history0 = message.split(",").slice(1,message.length-1)
				updateHistory(history0)
				break;
			case "latest":
				document.getElementById("versionInfo").style.color = "#236648";
				document.getElementById("versionInfo").innerHTML = `Ver. ${parts[1]} — Match Studio (Latest)`;
				break;
			case "version":
				document.getElementById("versionInfo").innerHTML = `Ver. ${parts[1]} — Match Studio`;
				break;
			case "outdated":
				document.getElementById("versionInfo").style.color = "#a3273b";
				document.getElementById("versionInfo").innerHTML = `Ver. ${parts[1]} — Match Studio (Outdated)`;
				document.getElementById("newVersion").innerHTML = `New version: ${parts[2]} is available. Please update it!`;
				break;
			case "unreleased":
				document.getElementById("versionInfo").style.color = "#9c5313";
				document.getElementById("versionInfo").innerHTML = `Ver. ${parts[1]} — Match Studio`;
				break;
				
			case "worlds":
				updateWorld(parts.slice(1));
				break;

			// Older running supervisors may replay these UI actions on refresh.
			// Only a user's Load click should open a file picker.
			case "loadControllerPressed":
			case "unloadControllerPressed":
				break;
			case "runPressed":
				preRun();
                setMatchState('running');
				break;
			case "runDockerPressed":
				preRun();
                setMatchState('running');
				break;
			case "pausedPressed":
                setMatchState('paused');
				setEnableButton("pauseButton", false);
                setEnableButton("runButton", true);
                setEnableButton("lopButton", false);
				break;
			case "remoteEnabled":
				if (!matchStarted) {
                    setEnableButton("load0", false);
                    setEnableButton("unload0", false);
                }
                setDisableRemoteBtn();
				break;
			case "remoteDisabled":
				if (!matchStarted) {
                    setEnableButton("load0", true);
                    setEnableButton("unload0", true);
                }
                setEnableRemoteBtn();
				break;
            case "dockerError":
                setDockerStarting(false);
                setMatchState('ready');
                showSourceStatus(parts.slice(1).join(','), true);
                break;
			case "dockerSuccess":
				preRun();
                setMatchState('running');
				break;
			case "currentWorld":
				enableTestButton(parts[1]);
                document.getElementById('currentWorldName').textContent = parts.slice(1).join(',').replace(/\.wbt$/, '').replace(/_/g, ' ');
				break;
		}
	}
}

function updateWorld(worlds) {
    const container = document.getElementById('worlds_div');
    container.replaceChildren();
    const names = String(worlds).split(',').filter(name => name.trim());
    if (!names.includes(selectedWorld)) {
        selectedWorld = '';
        document.getElementById('selectedWorldName').textContent = 'Choose a world above';
        document.getElementById('loadSelectedWorld').disabled = true;
    }
    if (!names.length) {
        const empty = document.createElement('p');
        empty.textContent = 'No worlds are available. Try Reload worlds.';
        container.appendChild(empty);
        window.filterWorlds();
        return;
    }
    for (const name of names) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'world-button';
        button.setAttribute('data-world', name);
        button.setAttribute('aria-pressed', String(selectedWorld === name));
        button.onclick = () => window.selectWorld(name);
        const thumbnail = document.createElement('img');
        thumbnail.src = './thumbnails/' + name.replace(/\.[^/.]+$/, '') + '.png';
        thumbnail.alt = '';
        thumbnail.width = 68; thumbnail.height = 52;
        thumbnail.loading = 'lazy';
        thumbnail.onerror = () => {
            thumbnail.onerror = null;
            thumbnail.src = './thumbnails/missing.png';
        };
        const label = document.createElement('span');
        label.textContent = name.replace(/\.wbt$/, '').replace(/_/g, ' ');
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('class', 'icon');
        icon.setAttribute('aria-hidden', 'true');
        const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
        use.setAttribute('href', '#i-check');
        icon.appendChild(use);
        button.append(thumbnail, label, icon);
        container.appendChild(button);
    }
    window.filterWorlds();
}

function updateEventScrollHint() {
    const region = document.getElementById('historyRegion');
    document.getElementById('eventScrollHint').hidden = region.hidden || region.scrollHeight <= region.clientHeight + 1;
}

function updateHistory(history) {
    if (!history[0] || !history[0].includes(':')) return;
    const message = history.slice(1).join(',');
    const row = document.createElement('tr');
    const tone = message.includes('WARNING') ? 'warning' : message.includes('+') ? 'positive' : message.includes('-') ? 'negative' : 'neutral';
    row.setAttribute('data-tone', tone);
    for (const text of [history[0], message]) {
        const cell = document.createElement('td');
        cell.textContent = text;
        row.appendChild(cell);
    }
    const body = document.getElementById('history');
    body.prepend(row);
    const count = body.children.length;
    document.getElementById('exportEventCsv').disabled = false;
    document.getElementById('eventCount').textContent = count + (count === 1 ? ' event' : ' events');
    document.getElementById('historyEmpty').hidden = true;
    document.getElementById('historyRegion').hidden = false;
    updateEventScrollHint();
}

window.exportEventCsv = function () {
    const rows = [...document.querySelectorAll('#history tr')].reverse();
    if (!rows.length) return;
    const records = [['Timestamp', 'Event'], ...rows.map(row => [...row.cells].map(cell => cell.textContent))];
    const csv = '\uFEFF' + records.map(record => record.map(value => '"' + value.replace(/"/g, '""') + '"').join(',')).join('\r\n') + '\r\n';
    const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'erebus-events-' + new Date().toISOString().replace(/[:.]/g, '-') + '.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
};

function resetHistory() {
    document.getElementById('exportEventCsv').disabled = true;
    document.getElementById('history').replaceChildren();
    document.getElementById('eventCount').textContent = '0 events';
    document.getElementById('historyEmpty').hidden = false;
    document.getElementById('historyRegion').hidden = true;
    updateEventScrollHint();
}

function loadedController(id){
    showSourceStatus("");
	//A controller has been loaded into a robot id is 0 or 1 and name is the name of the robot
	//Set name and toggle to unload button for robot 0
	if (document.getElementById("keepRemote").checked && id == 0) return
    const filename = document.getElementById('robot' + id + 'Controller').files?.[0]?.name;
    setFileState(id, filename || (id === 0 ? 'Controller loaded' : 'Robot JSON loaded'), true);
	document.getElementById("load"+ id).style.display = "none";
	document.getElementById("unload"+ id).style.display = "inline-block";
	if (id == 0)
		disableWhileSending(false);
}

function unloadedController(id){
    setFileState(id, id === 0 ? 'No controller loaded' : 'No robot JSON loaded', false);
	//A controller has been unloaded for robot of the given id
	//Reset name and toggle to load button for robot 0
	document.getElementById("robot"+ id +"Controller").value = "";
	document.getElementById("unload"+ id).style.display = "none";
	document.getElementById("load"+ id).style.display = "inline-block";
}

function setEnableRemoteBtn() {
    document.getElementById('remoteMode').checked = false;
}
function setDisableRemoteBtn() {
    document.getElementById('remoteMode').checked = true;
}

function startup (){
    dockerStarting = false;
    setMatchState('ready');
    setEnableButton("recording", true);
    matchStarted = false;
    showSourceStatus("");
	resetHistory();
	unloadedController(0);
	unloadedController(1);
	//Turn on the run button and reset button when the program has loaded
	setEnableButton("runButton", true);
	setEnableButton("runDockerButton", true);

	setEnableButton("pauseButton", false);
	setEnableButton('lopButton', false)

	setEnableButton("load0", true);
	setEnableButton("unload0", true);
	setEnableButton("load1", true);
	setEnableButton("unload1", true);
	setEnableButton("giveupB", false);

	setEnableButton("remoteMode", true);
	setEnableButton("dockerPath", true);
	setEnableRemoteBtn();
	getWorlds();
}

window.getWorlds = function() {
	console.log("Getting worlds...")
	window.robotWindow.send('getWorlds');
}

function update (data){
	//Update the ui each frame of the simulation
	//Sets the the timer
	const score = String(data[0]);
    const displayScore = score.includes('.') ? score : score + '.00';
    document.getElementById("score0").textContent = displayScore;
    document.getElementById('score0').setAttribute('data-digits', displayScore.length > 6 ? 'long' : 'short');

	//The total time at the start
	let maxTime = 8 * 60; 
	if (data[2]) { // is this necessary?
		maxTime = data[2]
	}
	maxTime = parseInt(maxTime);
	let maxRealTime = Math.max(maxTime + 60, maxTime * 1.25);
	document.getElementById("timer").innerHTML = calculateTimeRemaining(data[1], maxTime);
	document.getElementById("realWorldTimer").textContent = calculateTimeRemaining(data[3], maxRealTime);
    document.getElementById('simulationLimit').textContent = calculateTimeRemaining(0, maxTime) + ' total';
    document.getElementById('realWorldLimit').textContent = calculateTimeRemaining(0, maxRealTime) + ' total';
    const simulationRemaining = Math.max(0, maxTime - Math.floor(Number(data[1]) || 0));
    const realRemaining = Math.max(0, maxRealTime - Math.floor(Number(data[3]) || 0));
    const difference = realRemaining - simulationRemaining;
    document.getElementById('realWorldAllowance').textContent = (difference < 0 ? '−' : '+') + calculateTimeRemaining(0, Math.abs(difference));
    document.getElementById('allowanceLabel').textContent = difference < 0 ? 'Real-world time shorter by' : 'Real-world allowance';
    document.getElementById('realWorldAllowance').title = 'Real-world remaining: ' + calculateTimeRemaining(0, realRemaining);

}

function updateTestBtnState(state) {
	setEnableButton("test",!state);
}

function updateConfig (data){
	//Update the config ui
	document.getElementById("autoRemoveFiles").checked = Boolean(Number(data[0]));
	document.getElementById("autoLoP").checked = Boolean(Number(data[1]));
	document.getElementById("recording").checked = Boolean(Number(data[2]));
	document.getElementById("autoCam").checked = Boolean(Number(data[3]));
	if (data.length >= 5) {
		document.getElementById("keepRemote").checked = Boolean(Number(data[4]));
		document.getElementById("enableDebugging").checked = Boolean(Number(data[5]))
		const dockerPath = String(data[6] || "");
        document.getElementById("dockerPath").value = dockerPath.startsWith("uri:") ? decodeURIComponent(dockerPath.slice(4)) : dockerPath;
	}

    document.getElementById("autoReloadSources").checked = data[7] === '1';
    document.getElementById("controllerSource").value = decodeURIComponent(data[8] || '');
    document.getElementById("showHud").checked = data[10] !== '0';
    document.getElementById("generateMapReview").checked = data[11] === '1';
	updateTestBtnState(Boolean(Number(data[0])))
}

window.configChanged = function(changedSetting){
	let data = [0,0,0,0,0,0,""];
	data[0] = String(Number(document.getElementById("autoRemoveFiles").checked));
	data[1] = String(Number(document.getElementById("autoLoP").checked));
	data[2] = String(Number(document.getElementById("recording").checked));
	data[3] = String(Number(document.getElementById("autoCam").checked));
	data[4] = String(Number(document.getElementById("keepRemote").checked));
	data[5] = String(Number(document.getElementById("enableDebugging").checked))
	data[6] = "uri:" + encodeURIComponent(document.getElementById("dockerPath").value)
    if (!matchStarted && changedSetting === 'keepRemote') {
        if (document.getElementById("keepRemote").checked) window.enableRemotePressed();
        else window.disableRemotePressed();
    }

	updateTestBtnState(document.getElementById("autoRemoveFiles").checked)
    data[7] = String(Number(document.getElementById("autoReloadSources").checked));
    data[8] = encodeURIComponent(document.getElementById("controllerSource").value.trim());
    data[9] = ''; // Preserve the HUD index; JSON is loaded only through its browser button.
    data[10] = String(Number(document.getElementById("showHud").checked));
    data[11] = String(Number(document.getElementById("generateMapReview").checked));
    window.robotWindow.send(`config,${data.join(',')}`);
}

function calculateTimeRemaining(done, maxTime){
	//Create the string for the time remaining (mm:ss) given the amount of time elapsed
	//Convert to an integer
	done = Math.floor(done);
	//Calculate number of seconds remaining
	var remaining = Math.max(0, maxTime - done);
	//Calculate seconds part of the time
	var seconds = Math.floor(remaining % 60);
	//Calculate the minutes part of the time
	var mins = Math.floor((remaining - seconds) / 60);
	//Convert parts to strings
	mins = String(mins)
	seconds = String(seconds)

	//Add leading 0s if necessary
	for (var i = 0; i < 2 - seconds.length; i++){
		seconds = "0" + seconds;
	}

	for (var i = 0; i < 2 - mins.length ; i++){
		mins = "0" + mins;
	}

	//Return the time string
	return mins + ":" + seconds;
}

function preRun() {
    dockerStarting = false;
    window.closeWorkspace();
    setSetupExpanded(false);
    setEnableButton("recording", false);
    matchStarted = true;
	//Disable all the loading buttons (cannot change loaded controllers once simulation starts)
	setEnableButton("load0", false);
	setEnableButton("unload0", false);
	
	setEnableButton("load1", false);
	setEnableButton("unload1", false);
	//When the run button is pressed
	//Disable the run button
	setEnableButton("runButton", false);
	setEnableButton("runDockerButton", false);
	//Send a run command
	//Enable the pause button
	setEnableButton("pauseButton", true);
	
	// setEnableButton('quit0', true)
	setEnableButton('lopButton', true)

	setEnableButton("giveupB", true);

	setEnableButton("remoteMode", false);

	setEnableButton("dockerPath", false);
}

window.runPressed = function(){
    setMatchState('starting');
    showSourceStatus("");
	preRun();
	window.robotWindow.send("run");
}

function setDockerStarting(starting) {
    dockerStarting = starting;
    disableWhileSending(starting);
    for (const id of ['runDockerButton', 'dockerPath', 'remoteMode']) setEnableButton(id, !starting);
    if (!starting && document.getElementById('remoteMode').checked) {
        setEnableButton('load0', false);
        setEnableButton('unload0', false);
    }
}
window.runDockerPressed = function(){
    if (dockerStarting || matchStarted) return;
    const path = document.getElementById('dockerPath').value.trim();
    if (!path) { showSourceStatus('Enter a Docker project folder before starting Docker.', true); return; }
    showSourceStatus('');
    setDockerStarting(true);
    setMatchState('starting');
    window.closeWorkspace();
    window.robotWindow.send('runDocker,' + path);
}

window.pausePressed = function(){
    setMatchState('pausing');
	//When the pause button is pressed
	//Turn off pause button, on run button and send signal to pause
	setEnableButton("pauseButton", false);
	setEnableButton("runButton", true);
	setEnableButton('lopButton', false)
	window.robotWindow.send("pause");
}

window.resetPressed = function(){
    setMatchState('resetting');
	//When the reset button is pressed
	//Disable all buttons
	setEnableButton("runButton", false);
	setEnableButton("pauseButton", false);
	setEnableButton('lopButton', false);
	//Send signal to reset everything
	window.robotWindow.send("reset");
}

window.testPressed = function() {
	preRun();
	window.robotWindow.send("loadTest");
	window.robotWindow.send("runTest");
}

window.giveupPressed = function(){
	if(document.getElementById("giveupB").className == "btn-giveup"){
		window.robotWindow.send("quit,0");
		setEnableButton("runButton", false)
		setEnableButton("pauseButton", false);
		setEnableButton('lopButton', false)
		setEnableButton('giveupB', false)
	}
}

window.openLoadController = function(id){
	//When a load button is pressed - opens the file explorer window
	const input = document.getElementById("robot"+id+"Controller");
	input.value = ""; // Allow selecting the same file again after an upload error.
	input.click();
}

function setEnableButton(name, state){
	//Set the disabled state of a button (state is if it is enabled as a boolean)
	document.getElementById(name).disabled = !state;
	if(name == "giveupB"){
		if(state) document.getElementById(name).className = "btn-giveup"
		else document.getElementById(name).className = "btn-giveupD"
	}
}

//Set the onload command for the window
window.onload = function(){
	//Connect the window
    // Match actions return the interface to its live view before running their existing handler.
    document.getElementById('match-controls').addEventListener('click', event => {
        if (event.target.closest('button:not(:disabled)')) {
            window.closeWorkspace();
            setSetupExpanded(false);
        }
    }, true);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') window.closeWorkspace();
    });
    document.querySelector('.preparation-tabs').addEventListener('keydown', event => {
        const buttons = [...event.currentTarget.querySelectorAll('button')];
        const index = buttons.indexOf(document.activeElement);
        const next = event.key === 'ArrowRight' ? (index + 1) % buttons.length :
            event.key === 'ArrowLeft' ? (index + buttons.length - 1) % buttons.length :
            event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : -1;
        if (next >= 0) { event.preventDefault(); buttons[next].focus(); }
    });
    const historyObserver = new ResizeObserver(updateEventScrollHint);
    historyObserver.observe(document.getElementById('historyRegion'));
	window.robotWindow = new RobotWindow();
	//Set the title
	window.robotWindow.setTitle('Erebus Simulation Controls');
	//Set which function handles the recieved messages
	window.robotWindow.receive = receive;
	//Set timer to inital time value
	document.getElementById("timer").textContent = '--:--'
    setMatchState('connecting');
	window.robotWindow.send("rw_reload");
};

function endGame(){
    setMatchState('finished');
    setEnableButton('giveupB', false);
    setEnableButton("recording", true);
	//Once the game is over turn off both the run and pause buttons
	setEnableButton("runButton", false)
	setEnableButton("pauseButton", false);
	setEnableButton('lopButton', false)
}

window.unloadPressed = function(id){
	//Unload button pressed
	//Send the signal for an unload for the correct robot
	window.robotWindow.send("robot"+id+"Unload");
}

function disableWhileSending(disabled) {
	setEnableButton("load0", !disabled);
	setEnableButton("unload0", !disabled);
	
	setEnableButton("load1", !disabled);
	setEnableButton("unload1", !disabled);
	
	setEnableButton("runButton", !disabled);
}


window.fileOpened = function(filesId, acceptTypes, location, id){
	//When file 0 value is changed
	//Get the files
	var files = document.getElementById(filesId).files;

	//If there are files
	if (files.length > 0){
		//Get the first file only
		var file = files[0];
		//Split at the .
		var nameParts = file.name.split(".");

		//If there are parts to the name
		if (nameParts.length >= 1){
			//If the file extension is valid
			if(nameParts.length == 1 || acceptTypes.includes(nameParts[nameParts.length - 1].toLowerCase()) ){
				const fd = new FormData();
				for (let i = 0; i < files.length; i++) {
					const f = files[i];
					fd.append(`file${(i+1)}`, f, f.name);
				}

				let xmlhttp = new XMLHttpRequest();
				xmlhttp.onreadystatechange = function () {
					if (xmlhttp.readyState == 4 && xmlhttp.status != 200) {
						disableWhileSending(false);
						showSourceStatus(xmlhttp.responseText || "Controller upload failed. Please try again.", true);
                        setFileState(id, 'Controller upload failed', false);
					}
					if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
						loadedController(id);
						window.robotWindow.send("controllerUploaded," + id);
					}
				};
                setFileState(id, 'Uploading controller…', false);
				disableWhileSending(true);
				xmlhttp.open("POST", "http://127.0.0.1:60520/"+location+"/", true);
				xmlhttp.send(fd);
			}else{
				//Tell the user to select a program
				showSourceStatus("Please select a controller with a valid file type: .py, .exe, .class, .jar, .bsg, .m or no extension.", true);
			}
		}else{
			//Tell the user to select a program
			showSourceStatus("Please select a controller program.", true);
		}

	}
}

window.openJsonFile = function(){
	//When file 0 value is changed
	//Get the files
	var files = document.getElementById("robot1Controller").files;
	
	//If there are files
	if (files.length > 0){
		//Get the first file only
		var file = files.item(0);
		//Split at the .
		var nameParts = file.name.split(".");
		
		//If there are parts to the name
		if (nameParts.length > 1){
			//If the last part is "json" - a json file
			if(nameParts[nameParts.length - 1].toLowerCase() == "json"){
				//Create a file reader
				var reader = new FileReader();
				
				//Set the function of the reader when it finishes loading
				reader.onload = (function(reader){
					return function(){
						//Send the signal to the supervisor with the data from the file
						window.robotWindow.send("robotJson," + reader.result);
					}
				})(reader);
				
				reader.onerror = () => {showSourceStatus("The JSON file could not be read. Please select it again.", true);setFileState(1, 'Robot JSON could not be read', false);};
				//Read the file as UTF-8 text
				setFileState(1, 'Loading robot JSON…', false);
                reader.readAsText(file);
			}else{
				//Tell the user to select a json file
				showSourceStatus("Please select a JSON file.", true);
			}
		}else{
			//Tell the user to select a json file
			showSourceStatus("Please select a JSON file.", true);
		}
		
	}
}

window.relocate = function(id){
	window.robotWindow.send("relocate,"+id.toString());
}

window.quit = function(id){
	unloadPressed(id);
	window.robotWindow.send("quit,"+id.toString());
}

window.enableRemotePressed = function() {
	setEnableButton("load0", false);
	setEnableButton("unload0", false);
	setDisableRemoteBtn();
	window.robotWindow.send("remoteEnable");
}
window.disableRemotePressed = function() {
	setEnableButton("load0", true);
	setEnableButton("unload0", true);
	setEnableRemoteBtn();
	let keep_before = document.getElementById("keepRemote").checked
	document.getElementById("keepRemote").checked = false
	if (keep_before) configChanged()
	window.robotWindow.send("remoteDisable");
}

function enableTestButton(world_name) {
	if (world_name != ".Tests"){ 
		document.getElementById("dev-tests").style.display = "none";
        document.getElementById("dev-tests").hidden = true;
		return;
	}
	document.getElementById("dev-tests").style.display = "block";
    document.getElementById("dev-tests").hidden = false;
}

// Save and open on the computer running Webots; never send a Run or Reset.
window.openMapReview = function () {
    document.getElementById('viewMapReview').disabled = true;
    document.getElementById('mapReviewNotice').textContent = 'Saving map result…';
    window.robotWindow.send('showMapReview');
};

// Browser-native popup request; the browser retains control of window placement.
let compactWindow = null;
window.openCompactWindow = function () {
    if (compactWindow && !compactWindow.closed) {
        compactWindow.focus();
        return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set('compact', '1');
    const width = Math.min(740, window.screen.availWidth);
    const height = Math.min(900, window.screen.availHeight);
    compactWindow = window.open(url.href, '_blank', `popup=yes,width=${width},height=${height},resizable=yes,scrollbars=yes`);
    const status = document.getElementById('compactWindowStatus');
    if (compactWindow) {
        compactWindow.opener = null;
        compactWindow.focus();
        status.textContent = 'Compact supervisor opened in a separate window.';
    } else {
        status.textContent = 'The browser blocked the window. Allow popups for this Webots address, then try again. You can keep using this page.';
    }
};
if (new URL(window.location.href).searchParams.get('compact') === '1') {
    document.getElementById('openCompact').hidden = true;
}

function setSetupExpanded(expanded) {
    if (expanded) setPreparationPanel('setup');
    else if (activePanel === 'setup') setPreparationPanel(null);
}
