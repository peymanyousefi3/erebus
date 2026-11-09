# Erebus customizations by Peyman Yousefi; original RoboCupJunior credits retained.
from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from MainSupervisor import Erebus


class Recorder:
    """Live HUD labels also captured by Webots HTML replay export."""

    ID_SCORE: int = 0
    ID_CLOCK: int = 1
    ID_EVENTS: int = 2

    @staticmethod
    def update_hud(erebus: Erebus):
        """Display match score and elapsed/maximum time live and in HTML replays."""
        elapsed = max(0, min(int(erebus.time_elapsed), int(erebus.max_time)))
        minutes, seconds = divmod(elapsed, 60)
        max_minutes, max_seconds = divmod(int(erebus.max_time), 60)
        score = f"Score: {erebus.robot_obj.get_score():.2f}"
        clock = f"Time: {minutes:02d}:{seconds:02d} / {max_minutes:02d}:{max_seconds:02d}"
        # Webots renders each line at half the label size; leave a 0.005 gap.
        Recorder.set_label(erebus, Recorder.ID_SCORE, score, 0.02, 0.02, 0.13, 0xffffff, 0, "Arial")
        Recorder.set_label(erebus, Recorder.ID_CLOCK, clock, 0.02, 0.09, 0.11, 0xffffff, 0, "Arial")

        Recorder.update_events(erebus)

    @staticmethod
    def update_events(erebus: Erebus):
        """Keep the latest three timestamped events visible, newest first."""
        text = Recorder.event_text(erebus.robot_obj.history.master_history)
        Recorder.set_label(erebus, Recorder.ID_EVENTS, text, 0.02, 0.15, 0.055,
                        0xfbc531, 0, "Arial")

    @staticmethod
    def event_text(history):
        """Use the same three-event layout live and in the final exported frame."""
        return "\n".join(textwrap.fill(f"[{stamp}] {text}", width=64,
                                     subsequent_indent="        ", break_long_words=False,
                                     break_on_hyphens=False)
                         for stamp, text in reversed(history[-3:])) or "No events yet"

    @staticmethod
    def set_label(erebus: Erebus, label_id, text, x, y, size, color,
                  transparency=0, font="Arial"):
        # Transparent labels preserve the replay clock/event timeline when hidden.
        if not erebus.config.show_hud:
            transparency = 1
        erebus.setLabel(label_id, text, x, y, size, color, transparency, font)
