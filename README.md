<div align="center">

# Erebus 2027 · Match Studio

**Match Studio for Webots R2025a · RoboCupJunior Rescue Simulation 2027 draft rules**

[![Edition: 27.0.0-draft.2](docs/media/badges/edition.svg)](https://github.com/peymanyousefi3/erebus/releases/tag/v27.0.0-draft.2) [![Webots R2025a](docs/media/badges/webots.svg)](https://cyberbotics.com/) [![Based on official Erebus 26.1](docs/media/badges/upstream.svg)](https://github.com/robocup-junior/erebus/tree/v26.1) [![Python 3.10](docs/media/badges/python.svg)](#quick-start) [![Licence status](docs/media/badges/license.svg)](NOTICE.md)

<h3><a href="#quick-start">Quick start · Install &amp; run</a></h3>

**[Download 27.0.0-draft.2](https://github.com/peymanyousefi3/erebus/releases/download/v27.0.0-draft.2/Erebus-Match-Studio-27.0.0-draft.2-Webots-R2025a.zip)** · [Release notes](https://github.com/peymanyousefi3/erebus/releases/tag/v27.0.0-draft.2)

[Match Studio](#match-studio) · [2027 rules](#2027-rules) · [Branch guide](#branch-guide) · [PDF guide](docs/README-2027.pdf)

</div>

Match Studio brings the **RoboCupJunior Rescue Simulation 2027 draft rules** to the customized Erebus referee interface, with **Webots R2025a** support on Windows, macOS and Linux.

<table width="100%">
<tr>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/bot.svg" width="24" height="24" alt=""><br>
<strong><a href="#match-studio">Referee interface</a></strong><br>
Score, clocks, live battery and match controls in one compact window.
</td>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/settings.svg" width="24" height="24" alt=""><br>
<strong><a href="#advanced-setup-defaults">Setup and world selection</a></strong><br>
Organized Robot Setup, Advanced Setup and searchable field previews.
</td>
</tr>
<tr>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/play.svg" width="24" height="24" alt=""><br>
<strong><a href="#interactive-3d-replay">Interactive 3D replays</a></strong><br>
Playback, timeline seeking, camera controls and a final score breakdown.
</td>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/map.svg" width="24" height="24" alt=""><br>
<strong><a href="#submitted-map-review">Submitted-map review</a></strong><br>
Cell-by-cell comparison, error highlighting, PNG export and the original matrix.
</td>
</tr>
<tr>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/activity.svg" width="24" height="24" alt=""><br>
<strong><a href="#events-hud-and-saved-files">Events and HUD</a></strong><br>
Timestamped match history, CSV export and replay-synchronized events.
</td>
<td width="50%" valign="top">
<img src="docs/media/feature-icons/code.svg" width="24" height="24" alt=""><br>
<strong><a href="#keep-files-and-reload-before-run">Controller file handling</a></strong><br>
Keep files after Reset and optionally reload local source before each match.
</td>
</tr>
<tr>
<td colspan="2" valign="top">
<img src="docs/media/feature-icons/flag.svg" width="24" height="24" alt=""><br>
<strong><a href="#2027-rules">2027 rules</a></strong><br>
Motor-based battery consumption, configurable replacement on cyan tiles, smiley victims and updated scoring.
</td>
</tr>
</table>

## Branch guide

Choose the branch that matches your competition and Webots installation.

| Branch | Rules | Webots | Use this for |
| --- | --- | --- | --- |
| [`2026_webots2023b`](https://github.com/peymanyousefi3/erebus/tree/2026_webots2023b) | 2026 | R2023b | Match Studio 26.2: match supervision, replay and map review. |
| **[`2027_webots2025a`](https://github.com/peymanyousefi3/erebus/tree/2027_webots2025a)** (this branch) | 2027 draft | R2025a | Match Studio with battery consumption, cyan contact tiles and smiley victims. |

![Current 2027 Match Studio supervisor, captured at 360 CSS pixels with setup and match controls](docs/media/supervisor-overview.png)

*Example views of the supervisor, replay and map-review tools. Setup and battery readings are illustrative; the sample map includes three reporting errors.*

## Match Studio

Match Studio keeps score, battery, clocks, controls and events together. Setup panels open only when selected, leaving the match view compact.

| Feature | What the referee can do |
| --- | --- |
| Match console | Read decimal scores, live battery, simulation remaining time and the real-world allowance. |
| Connected setup panels | Open **Robot Setup**, **Advanced Setup** or **Worlds**; only one panel expands at a time. Search, preview, select and load a bundled field. |
| Match controls | Run, pause, relocate, reset, give up and save the accepted map. |
| Interactive HTML replay | Play, pause, seek, rotate and zoom a recorded 3D match in a browser; share its ZIP and final-score summary. |
| Submitted-map review | Select cells to compare reported and expected values, rotate, zoom, pan, fit, save PNG and export the original matrix. |
| Match events | Follow timestamped events and export the complete history as chronological CSV. |
| Webots HUD | Independently show score, time and the latest three events, including in the replay. |
| File handling | Retain uploaded files after Reset, optionally refresh a local controller source before Run, and recover from missing files or invalid robot JSON. |
| External controllers | Use the existing remote controls, with visible connection errors and duplicate-start protection. |

![Updated setup walkthrough: Robot Setup, controller source refresh, Advanced Setup and cyan-field search](docs/media/setup-walkthrough.gif)

### Keep Files and Reload Before Run

These switches are independent:

| Keep Files | Reload Before Run | Result |
| --- | --- | --- |
| Off | Off | Reset removes loaded copies; load the controller and JSON again. |
| On | Off | Reuse the retained copies. Editing the original source does not update them. |
| Off | On | Refresh the controller from its saved path for the next match; JSON still uses normal loading after Reset. |
| On | On | Retain the copies and refresh the controller for each new local match. |

The source path belongs to the **computer running Webots**. Relative paths start in the Erebus project folder. Enter it manually: browser file pickers provide contents, not a portable original full path. Robot JSON keeps its normal browser-loading workflow.

Refresh applies to a **new local Run**, not pause/resume or Remote mode. Supported entries are `.py`, `.exe`, `.class`, `.jar`, `.bsg`, `.m`, or a compiled executable without an extension. C/C++ must already be compiled. Check Robot Setup for missing-file messages and the Webots console for controller errors.

### Advanced Setup defaults

| Setting | Default |
| --- | --- |
| Keep Files | On |
| HTML replay recording / Webots HUD | On / On |
| Reload Before Run / Automatic map result | Off / Off |
| Automatic camera / Keep Remote on Reset | Off / Off |
| Disable automatic LoP / Enable debugging | Off / Off |

Use **Open Compact Window** for a separate, resizable browser window. Allow browser popups if it does not open.

## Interactive 3D replay

Recording starts after robot setup and the initial HUD are ready. At completion, timeout, give-up or Reset, Erebus finalizes the recording before removing the robot. Matches are saved as **interactive HTML/W3D replays** with the final score and event history.

![Actual R2025a match replay: forward seeking, rewind and 3D scene inspection](docs/media/replay-playback.gif)

The replay includes the 3D scene and animation, final score, field/exit/map breakdown, remaining time and playback-synchronized events. Events follow the playback position when seeking forward or backward.

Open **`recording/replay.html`** directly in a supported browser, or serve it over HTTP(S). Keep the complete recording folder for archival; the accompanying ZIP contains a `recording/` directory. Scene, animation and exported local assets are embedded, but the Cyberbotics viewer still requires internet access and WebGL.

To embed a hosted recording:

```html
<iframe src="/matches/example/recording/replay.html"
        title="Erebus match replay" loading="lazy" allowfullscreen
        style="width:100%;height:720px;border:0"></iframe>
```

A hosting website can read `match-result.json` to display score cards. Configure access permissions on the website where you publish recordings.

## Submitted-map review

Review the **accepted map submission**, its correctness result and each reported-versus-expected cell. The review is available after the supervisor evaluates a submitted map.

![2027 map review: inspect a missing cyan contact tile, rotate, zoom and fit](docs/media/map-review.gif)

- Correct cells fade; incorrect reports stay prominent. Nonzero content in either map remains visible.
- Select a cell for its original matrix coordinates, reported value, expected value and comparison status.
- Rotate in 90-degree steps, zoom, pan or fit. Save a PNG or export the untouched reported matrix as JSON.
- Only outer margins that are zero in both maps are cropped. Cells outside the scored comparison are marked separately.

**Automatic map result** saves and opens the review when a map is accepted. With it off, **Save map** still works after evaluation, including after robot removal. Repeated saves use the same match folder; rejected later submissions do not replace the accepted result. Save before Reset.

## Events, HUD and saved files

**Export CSV** downloads all events, oldest first, with `Timestamp` and `Event` columns. UTF-8 and CSV quoting preserve commas, quotation marks and multiline entries. It is available during or after a match when events exist; Reset clears the history. Times are match times, not wall-clock timestamps.

The HUD switch is independent of recording. It controls score, elapsed/maximum time and the latest three events in Webots. Turning visible labels off retains the timing information needed to synchronize replay events.

Each match has its own start-time folder:

```text
match-results/<start-time>/
├── recording/
│   ├── replay.html, replay.w3d, replay.json, replay.css, replay.jpg
│   ├── match-result.json
│   ├── textures/                  # When exported
│   └── <start-time>.zip
└── map/
    ├── map-review.html
    ├── map-result.json
    └── reported-map.json
```

Recordings and map reviews are saved independently. The recording ZIP contains the `recording/` folder; archive the `map/` folder separately to keep the map review.

## 2027 rules

See the [RoboCupJunior Rescue Simulation 2027 draft rules](https://junior.robocup.org/wp-content/uploads/2026/09/RCJRescueSimulation2027-draft.pdf) for the full competition requirements. Key match settings and reporting requirements are summarized below.

| Rule area | Match behavior |
| --- | --- |
| Battery consumption | The supervisor measures wheel movement and updates the live battery meter. Additional driven wheels count separately. |
| Cyan contact tiles | Remain continuously stationary on the **same tile for 5 seconds** to replace the battery. Movement, leaving the tile or relocation resets the interval. The duration is organizer-configurable. |
| Swamps | Increase battery consumption; **the match clock keeps its normal pace**. |
| Empty battery | Ends the run. An empty battery cannot be revived by remaining on a contact tile. |
| Victim appearance | **H = harmed/sad, S = stable/neutral, U = unharmed/happy** smileys. Three-dimensional decoys do not score. Victim signs are 20 mm square; cognitive targets are 50 mm across. |
| Token reporting | Requires at least **one second stopped**, with the robot and reported position within **60 mm** of the sign. Wrong-category and duplicate reports are handled by the scoring rules. |
| Mapping | Cyan contact tiles use **`k`**. Map review uses the accepted submission and the same scorer as the supervisor. |
| Match duration | Up to **480 simulated seconds**, with a **600-second real-world limit**. Exit, give-up or battery depletion can end a run earlier. |
| Match ending | Exit eligibility, map bonus and rounding are evaluated by the supervisor. The final map award is included in the completed score. |

![Current battery display showing remaining energy, low battery and replacement](docs/media/battery-2027.gif)

*Example battery display: remaining charge, low battery and replacement on a cyan tile.*

### Organizer battery configuration

Edit [`sensorEnergyConfig.txt`](game/controllers/MainSupervisor/sensorEnergyConfig.txt) in the MainSupervisor folder and restart the supervisor after changing values:

```ini
ChangeBatteryTime = 5
Motor_Drain_Per_Step = 0.02,
Motor_Max_Velocity = 6.28,
Battery_Per_Step = 0.00,
SwampMultiplier = 5
```

Set `ChangeBatteryTime` to the required stationary duration in seconds. The default is **5 seconds**.

At the default settings, a two-wheel pair running at 6.28 rad/s consumes 0.02 battery percentage points per reference 16 ms. Additional driven wheels contribute separately. `SwampMultiplier = 5` applies five times the normal consumption in swamps. Passive and sensor consumption default to zero; organizers can adjust these values in the configuration file.

### Map scoring

The mapping multiplier is **`1 + 1.2 × correctness`**, where correctness ranges from 0 to 1. A fully correct map gives a multiplier of **2.2**. Use **Save map** to review the accepted submission and its correctness result.

### Competition graphics profile

Set these Webots preferences consistently on competition machines: **Ambient Occlusion Low**, **Texture Quality Low**, **Max Texture Filtering 4**, **Shadows Disabled**, **Anti-aliasing Disabled**.

### Battery in the controller interface

A normal **`G` game-info request** receives a 20-byte packet:

```python
kind, score, simulation_remaining, real_remaining, battery_percent = \
    struct.unpack('c f i i f', packet)
```

Battery percentage is appended to the original fields. Older readers that require exactly 16 bytes need updating. The supplied [`GetGameInfo.py`](player_controllers/GetGameInfo.py) accepts both packet sizes. Use the standard reporting messages to report victims, submit maps and request game information.

## Quick start

### What you need

| Software | Version | Download / setup |
| --- | --- | --- |
| **Webots** | **R2025a** | [Download](https://github.com/cyberbotics/webots/releases/tag/R2025a) · [Setup](https://cyberbotics.com/doc/guide/installation-procedure?version=R2025a) |
| **Erebus Match Studio** | **27.0.0-draft.2** | [Download ZIP](https://github.com/peymanyousefi3/erebus/releases/download/v27.0.0-draft.2/Erebus-Match-Studio-27.0.0-draft.2-Webots-R2025a.zip) · [Release notes](https://github.com/peymanyousefi3/erebus/releases/tag/v27.0.0-draft.2) |
| **Python** | **3.10 · 64-bit** | [Download](https://www.python.org/downloads/release/python-31011/) · [Select in Webots](https://cyberbotics.com/doc/guide/using-python?version=R2025a) |
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

1. Open a [world file](game/worlds/mapping_example_1_cyan_tiles.wbt) from **game/worlds** in Webots.
2. If Match Studio does not open automatically, right-click **Main Supervisor** in the Webots toolbar and select **Show Robot Window**. Match Studio opens in your default browser.
3. In **Match Studio → Robot Setup**, load your robot program and robot JSON.
4. Press **Run match**.

[Example programs](player_controllers/) · [Robot customizer](https://v25.robot.erebus.rcj.cloud/)

## Robot configuration

Use the existing robot customizer with a **3,000-point component budget** for this edition.

## Credits and licensing

- **Original Erebus:** [RoboCupJunior Erebus maintainers and contributors](https://github.com/robocup-junior/erebus), based on [`v26.1`](https://github.com/robocup-junior/erebus/tree/v26.1).
- **Fork modifications and maintenance:** [Peyman Yousefi](https://github.com/peymanyousefi3).
- **2027 reference work:** the official 2027 branch and [sebybritez/Bater-a-PRUEBA contributors](https://github.com/sebybritez/Bater-a-PRUEBA/tree/Webots_2025a).
- **Simulation platform:** [Cyberbotics Webots](https://cyberbotics.com/).
- **Interface assets:** IBM Plex Sans and DSEG under their bundled SIL Open Font Licenses; Lucide and inherited Feather notices under the bundled ISC notices. Original fonts and Webots models retain their notices.

This is an independent edition of Erebus maintained by Peyman Yousefi. See [NOTICE.md](NOTICE.md) and the bundled [asset notices](game/plugins/robot_windows/MainSupervisorWindow/assets/) for licensing and attribution.

[Changelog](CHANGELOG.md) · [Release notes](https://github.com/peymanyousefi3/erebus/releases/tag/v27.0.0-draft.2) · [Contributing](https://github.com/peymanyousefi3/erebus/blob/v27.0.0-draft.2/CONTRIBUTING.md) · [Report an issue in this fork](https://github.com/peymanyousefi3/erebus/issues)
