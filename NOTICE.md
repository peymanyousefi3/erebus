# Attribution and licensing

## Original project

This repository is a fork of [RoboCupJunior Erebus](https://github.com/robocup-junior/erebus), based on the official [`v26.1` tag](https://github.com/robocup-junior/erebus/tree/v26.1), commit `a53a7965c8c0c594196aad111b486ca979e063a2`.

Erebus and its original simulator, rules implementation, robot model generation, maps, examples and documentation remain the work of the RoboCupJunior Erebus maintainers and their contributors. Webots is developed by Cyberbotics. This fork is independently maintained and is not an official RoboCupJunior release or endorsement.

## 2027 reference implementation

The 2027 integration draws on the official Erebus `2027_WebotsR2025a` branch and the battery implementation supplied by [Sebastián Britez and contributors](https://github.com/sebybritez/Bater-a-PRUEBA/tree/Webots_2025a). Their existing code, field and asset contributions retain their original attribution. Competition behavior follows the September 2026 [2027 draft rules](https://junior.robocup.org/wp-content/uploads/2026/09/RCJRescueSimulation2027-draft.pdf), including the five-second contact-tile stop.

## Fork modifications

The additional supervisor, replay, HUD, map-review and interface functionality in this edition is maintained by **Peyman Yousefi**. Custom contributions are identified in the source and described in the README and changelog. Attribution to Peyman Yousefi applies to these modifications, not to the entire upstream project.

## Licence status

At the inspected `v26.1` baseline, upstream includes no repository-wide `LICENSE` or `COPYING` file. **No new blanket licence is applied to this fork.** Public availability should not be read as a new permission grant for upstream code or assets. Existing source and asset notices remain in effect; obtain clarification from the relevant rights holders before redistribution or reuse requiring additional permission.

Bundled third-party interface assets retain their own notices:

- IBM Plex Sans: [SIL Open Font License](game/plugins/robot_windows/MainSupervisorWindow/assets/OFL-IBM-Plex.txt).
- DSEG: [SIL Open Font License](game/plugins/robot_windows/MainSupervisorWindow/assets/OFL-DSEG.txt).
- Lucide icons, including inherited Feather notices: [bundled licence](game/plugins/robot_windows/MainSupervisorWindow/assets/LICENSE-Lucide.txt).
- Original interface fonts: [upstream font licence](game/plugins/robot_windows/MainSupervisorWindow/fonts/LICENSE.txt).
- Webots models and other upstream assets: retain their embedded source notices.
