<div align="center">

# Erebus Match Studio

**Match Studio 26.2 · Webots R2023b · RoboCupJunior Rescue Simulation 2026**

[![Edition: 26.2 preview](docs/media/badges/edition.svg)](docs/releases/26.2-studio.1.md) [![Based on official Erebus 26.1](docs/media/badges/upstream.svg)](https://github.com/robocup-junior/erebus/tree/v26.1) [![Webots R2023b](docs/media/badges/webots.svg)](https://cyberbotics.com/) [![Python 3.10](docs/media/badges/python.svg)](#quick-start) [![Licence status: see NOTICE](docs/media/badges/license.svg)](NOTICE.md)

<h3><a href="#quick-start">Quick start · Install &amp; run</a></h3>

[Branch guide](#branch-guide) · [Features](#match-studio-features) · [Changelog](CHANGELOG.md) · [Report an issue](https://github.com/peymanyousefi3/erebus/issues)

</div>

---

Match Studio combines the Erebus competition environment with an updated supervisor interface, interactive replays and submitted-map review. This **26.2 edition** uses **Webots R2023b** and the **2026 competition rules**.

<table width="100%">
<tr>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/bot.svg" width="24" height="24" alt=""><br>
<strong><a href="#match-focused-supervisor">Match controls</a></strong><br>
Score, clocks, events and referee actions in one compact window.
</td>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/settings.svg" width="24" height="24" alt=""><br>
<strong><a href="#advanced-setup">Setup and world selection</a></strong><br>
Organized Robot Setup, Advanced Setup and field previews.
</td>
</tr>
<tr>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/play.svg" width="24" height="24" alt=""><br>
<strong><a href="#automatic-html-recording">Interactive 3D replays</a></strong><br>
Playback, timeline seeking, camera controls and a final score breakdown.
</td>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/map.svg" width="24" height="24" alt=""><br>
<strong><a href="#submitted-map-review">Submitted-map review</a></strong><br>
Compare reported and expected cells, inspect errors and export a PNG or the original matrix.
</td>
</tr>
<tr>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/activity.svg" width="24" height="24" alt=""><br>
<strong><a href="#export-match-events-as-csv">Events and HUD</a></strong><br>
Timestamped match history, CSV export and events synchronized with replay playback.
</td>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/code.svg" width="24" height="24" alt=""><br>
<strong><a href="#keep-files-and-reload-before-run">Controller file handling</a></strong><br>
Keep uploaded files after Reset and optionally reload local source before each match.
</td>
</tr>
</table>

## Branch guide

Choose the branch that matches your competition and Webots installation.

| Branch | Rules | Webots | Use this for |
| --- | --- | --- | --- |
| **[`2026_webots2023b`](https://github.com/peymanyousefi3/erebus/tree/2026_webots2023b)** (this branch) | 2026 | R2023b | Match Studio 26.2: match supervision, replay and map review. |
| [`2027_webots2025a`](https://github.com/peymanyousefi3/erebus/tree/2027_webots2025a) | 2027 draft | R2025a | Match Studio with battery consumption, cyan contact tiles and smiley victims. |
| [`2028_webots2025a`](https://github.com/peymanyousefi3/erebus/tree/2028_webots2025a) | Future development | R2025a | Robot Designer and component library; under development. |

**[Quick start](#quick-start)** · [Features](#match-studio-features) · [Match files](#match-files) · [PDF guide](docs/README-2026.pdf)

<p align="center">
  <img src="docs/media/supervisor-overview.png" width="900" alt="Erebus Match Studio overview: narrow supervisor, interactive replay and submitted-map review">
</p>

<p align="center"><sub>Match supervision, interactive replay and submitted-map review</sub></p>

*Example views of the supervisor, replay and map-review tools. Setup screenshots and the sample map use illustrative data.*

## Match Studio features

| Feature | What you can do |
| --- | --- |
| Interactive HTML replay | Replay a saved match in 3D, seek through the timeline and change the camera view. |
| Match results | Review the final score breakdown, remaining time and playback-synchronized events. |
| Webots HUD | Show score, time and the latest three events independently of recording. |
| Submitted-map review | Inspect the accepted map and compare reported and expected values for each cell. |
| Supervisor interface | View match controls and readouts together, and open setup panels as needed. |
| Controller source refresh | Reload a local controller from its original file before starting a new match. |
| File handling | Retain loaded files after Reset and receive clear messages for missing files or invalid robot JSON. |
| External controllers | Connect using Remote mode or the Docker controls. |
| Event export | Save the complete timestamped event history as CSV. |

Recording, the HUD and map review work with your existing robot controller. Scoring follows the 2026 Erebus rules.

## Quick start

### What you need

| Software | Version | Download / setup |
| --- | --- | --- |
| **Webots** | **R2023b** | [Download](https://github.com/cyberbotics/webots/releases/tag/R2023b) · [Setup](https://cyberbotics.com/doc/guide/installation-procedure?version=R2023b) |
| **Erebus Match Studio** | **2026** | [Download ZIP](https://github.com/peymanyousefi3/erebus/archive/refs/heads/2026_webots2023b.zip) |
| **Python** | **3.10 · 64-bit** | [Download](https://www.python.org/downloads/release/python-31011/) · [Select in Webots](https://cyberbotics.com/doc/guide/using-python?version=R2023b) |
| **Python packages** | [requirements.txt](requirements.txt) | [Install below](#install-python-packages) |

On Windows, enable **Add Python to PATH** during installation. Select Python 3.10 in **Webots preferences → General → Python command**.

### Install Python packages

Extract the Erebus ZIP. Open a terminal in the extracted folder.

**Windows**

```powershell
py -3.10 -m pip install -r requirements.txt
```

**macOS / Linux**

```sh
python3.10 -m pip install -r requirements.txt
```

**Packages:** [NumPy](https://pypi.org/project/numpy/) · [Requests](https://pypi.org/project/requests/) · [termcolor](https://pypi.org/project/termcolor/) · [overrides](https://pypi.org/project/overrides/) · [Pillow](https://pypi.org/project/pillow/) · [OpenCV](https://pypi.org/project/opencv-python/)

### Start Erebus

1. Open a [world file](game/worlds/mapping_example_1.wbt) from **game/worlds** in Webots.
2. If Match Studio does not open automatically, right-click **Main Supervisor** in the Webots toolbar and select **Show Robot Window**. Match Studio opens in your default browser.
3. In **Match Studio → Robot Setup**, load your robot program and robot JSON.
4. Press **Run match**.

[Example programs](player_controllers/) · [Robot customizer](https://v25.robot.erebus.rcj.cloud/)

## Match-focused supervisor

**Score, clocks, match controls and events stay together on the main page.** Robot Setup, Advanced Setup and Worlds share a connected selector row; setup starts collapsed and only one panel opens at a time.

- Read the score with decimal precision.
- Monitor remaining simulation time and the real-world time allowance.
- Resize the window to keep match controls and events visible alongside Webots.
- The battery display stays at **100%** in this edition. Battery consumption is available in the 2027 branch.
- **Open Compact Window** opens a separate, resizable browser window. Allow browser popups if it does not open.

<p align="center">
  <img src="docs/media/setup-walkthrough.gif" width="900" alt="Supervisor setup demonstration at narrow browser width">
</p>

### Keep Files and Reload Before Run

**Keep Files** controls whether the loaded controller and robot JSON copies survive Reset. **Reload Before Run** reads a saved controller program from the manually entered original-file path before a new local match.

<p align="center">
  <img src="docs/media/source-refresh.png" width="900" alt="Robot Setup at narrow width: browser file loading, source refresh and external-controller options">
</p>

| Keep Files | Reload Before Run | Behavior |
| --- | --- | --- |
| Off | Off | Reset removes loaded copies. Load the controller and JSON again before the next match. |
| On | Off | Retained copies are used. Editing the original controller does not update the loaded copy. |
| Off | On | The controller can be copied from its original path for the next match, but robot JSON still needs normal loading after Reset. |
| On | On | Copies are retained; the controller is refreshed from the original path for each new local match. |

The path is on the **computer running Webots**. Relative paths start in the Erebus project folder. Browser file pickers supply file contents, not a portable original full path, so enter the source path manually when using refresh.

The same formats are supported by browser upload and source refresh: `.py`, `.exe`, `.class`, `.jar`, `.bsg`, `.m`, or an executable without an extension. C/C++ programs must already be compiled. **Pause/resume, Remote mode and Docker do not use local source refresh.** **Robot JSON keeps its normal browser loading workflow.**

If a file or source path is missing, follow the error message in Robot Setup before starting the match. Check controller errors in the Webots console.

### Advanced Setup

Use Advanced Setup to configure display, exports and diagnostics. Default settings:

| Option | Default |
| --- | --- |
| Keep Files | On |
| Reload Before Run | Off |
| HTML replay recording | On |
| Webots HUD | On |
| Automatically save/open map result | Off |
| Automatic camera | Off |
| Keep Remote on Reset | Off |
| Disable automatic LoP / Enable debugging | Off / Off |

<p align="center">
  <img src="docs/media/advanced-settings.png" width="900" alt="Advanced Setup at narrow width: Display, Exports and Diagnostics">
</p>

## Automatic HTML recording

**Record an interactive 3D match, then rotate the scene, zoom in or out and replay it in a browser.** Recording size depends on the scene assets, movement and match duration.

Replay uses a WebGL-capable browser and loads the viewer from Cyberbotics. See the [Webots animation viewer documentation](https://cyberbotics.com/doc/guide/web-animation).

Enable **HTML replay recording** before starting the match. Recording starts after the robot and initial HUD are ready. On completion, give-up, timeout or reset, the supervisor finalizes the recording before removing the robot.

Recordings are saved as interactive HTML replays, including the final score and event history.

The recording contains:

- Interactive 3D playback, with play/pause, timeline seeking and camera movement.
- Final score, field score, exit bonus, map bonus and remaining match time.
- Timestamped events. Events follow the playback position when seeking forward or backward.
- A ZIP archive beside the unpacked replay files.

![Real Webots replay with play/pause controls, HUD and final-result summary](docs/media/replay-playback.gif)

`replay.html` can be opened directly from disk in a supported browser. Keep the complete recording folder for archival and upload. The exported page embeds its scene, animation and local assets; it still needs internet access to load the Webots viewer and a working WebGL implementation.

### Embed a replay on a website

Upload the recording folder, preserve its filenames, and serve its `replay.html` over HTTP(S):

```html
<iframe
  src="/matches/example/recording/replay.html"
  title="Erebus match replay"
  loading="lazy"
  allowfullscreen
  style="width:100%; height:720px; border:0">
</iframe>
```

The final score and synchronized event display are part of the replay page itself. A website may additionally read `match-result.json` for its own score cards. The ZIP contains a `recording/` directory; extract it without flattening that structure. Configure access permissions on the website where you publish recordings.

## Webots HUD

**Show head-up display** controls the simulation's score, elapsed/maximum match time and latest three events. An event stays visible until newer events replace it. The same labels are captured by HTML recording, while final result metadata includes the completed score and event history.

The HUD and recording switches are independent. Replay events stay synchronized with playback even when the visible HUD is off.

![Webots HUD close-up with arrows identifying score, elapsed and maximum time, and timestamped events](docs/media/webots-hud.png)

## Submitted-map review

**At the end of a match, inspect the actual map data submitted by the robot, its correctness result and exactly which reported cells are wrong.** Compare reported and expected values, then export the review and raw matrix for further development. The review is available after the supervisor evaluates a submitted map.

The review shows the correctness result used for match scoring.

- **Correct cells fade; incorrect reports stay prominent.**
- **Select a cell** for its raw matrix position, **reported value**, **expected value** and comparison status.
- Rotate left/right in 90° steps, zoom, fit the map or drag to pan.
- Save a PNG of the review, or export the original reported matrix as JSON.
- The initial view fits the useful map automatically. Only an outer margin that is zero in **both** the reference and reported map is cropped.
- Nonzero content in either map remains visible. Cells outside the scorer's comparison are marked separately as **outside comparison**, not silently counted as scored errors.

![Animated map review with cell detail, rotation, zoom and fit](docs/media/map-review.gif)

**Automatic map result** saves and opens the review when a map is accepted. With that option off, **Save map** still saves and opens the accepted result, including after the robot is removed. The button is unavailable until an evaluated map exists. Repeated saves use the same match folder, and later rejected submissions do not replace the accepted map.

The saved map-review page includes its data and interface assets, so you can reopen it independently.

## Export match events as CSV

Press **Export CSV** in Match Events to download the complete history with `Timestamp` and `Event` columns, oldest first.

Export is available during and after the match when events exist. Reset clears the history and disables export until new events arrive. The timestamp is match time, not wall-clock time.

<p align="center">
  <img src="docs/media/event-csv.png" width="900" alt="Export CSV button outlined and indicated by an arrow, with example chronological CSV rows">
</p>

## Match files

Each match uses one start-time folder under the project root:

```text
match-results/
└── 2026-10-29_14-30-00-123456/
    ├── recording/                   # When HTML recording is enabled
    │   ├── replay.html
    │   ├── replay.json
    │   ├── replay.x3d
    │   ├── replay.css
    │   ├── replay.jpg
    │   ├── match-result.json
    │   ├── textures/                # Exported local assets, when present
    │   └── 2026-10-29_14-30-00-123456.zip
    └── map/                         # When automatic or manual map save is used
        ├── map-review.html
        ├── map-result.json
        └── reported-map.json
```

Other scene dependencies may also be exported. The recording ZIP packages the recording, not the separate map-review directory. Map reviews and recordings are saved independently when their respective options are used.

## Credits and licensing

- **Original simulator:** [RoboCupJunior Erebus and its contributors](https://github.com/robocup-junior/erebus).
- **Fork modifications and maintenance:** [Peyman Yousefi](https://github.com/peymanyousefi3).
- **Simulation platform:** [Webots by Cyberbotics](https://cyberbotics.com/).
- **Competition rules:** [RoboCupJunior Rescue Simulation](https://junior.robocup.org/rcj-rescue-sim/).
- **Interface assets:** IBM Plex Sans, DSEG, Lucide and original upstream fonts, with their bundled notices retained.

This is an independent edition of Erebus maintained by Peyman Yousefi. See [NOTICE.md](NOTICE.md) for source and asset licensing, including the bundled [IBM Plex Sans](game/plugins/robot_windows/MainSupervisorWindow/assets/OFL-IBM-Plex.txt), [DSEG](game/plugins/robot_windows/MainSupervisorWindow/assets/OFL-DSEG.txt) and [Lucide/Feather](game/plugins/robot_windows/MainSupervisorWindow/assets/LICENSE-Lucide.txt) notices.

See the [changelog](CHANGELOG.md), [release notes](docs/releases/26.2-studio.1.md) and [contributing guide](CONTRIBUTING.md). Include your Webots version, operating system and steps to reproduce when [reporting an issue](https://github.com/peymanyousefi3/erebus/issues).
