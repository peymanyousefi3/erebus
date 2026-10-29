# Erebus customizations by Peyman Yousefi; original RoboCupJunior credits retained.
"""Optional map diagnostics. Scoring remains owned by MapScorer."""
import json
import math
import webbrowser
from threading import Thread
from ConsoleLog import Console
from datetime import datetime
from pathlib import Path

import numpy as np
import MapScorer


def build_review(answer, submitted, official_score, elapsed_seconds):
    raw = np.asarray(submitted).copy()
    rotated = np.asarray(answer).copy()
    best = None
    turns = 0
    # Follow the scorer's cumulative rotations, including its first-best tie order.
    for i in range(4):
        rotated = np.rot90(rotated, k=i, axes=(1, 0))
        turns = (turns + i) % 4
        aligned = MapScorer._align(rotated, raw)
        score, mask = MapScorer._calculate_completeness(rotated, aligned)
        if best is None or score > best[0]:
            best = (score, rotated.copy(), mask.copy(), turns)
    score, expected, mask, turns = best
    if not math.isclose(float(score), float(official_score), abs_tol=1e-12):
        raise ValueError("Map review disagrees with the accepted correctness score")
    offset = MapScorer._get_start_instance(expected) - MapScorer._get_start_instance(raw)
    dy, dx = map(int, offset)
    rows, cols = raw.shape
    ah, aw = expected.shape
    # Crop only an outer border that is zero in BOTH the reference and submission.
    top, left, bottom, right = ah, aw, 0, 0
    for matrix, oy, ox in ((expected, 0, 0), (raw, dy, dx)):
        nonzero = np.argwhere(matrix != '0')
        if nonzero.size:
            low, high = nonzero.min(axis=0), nonzero.max(axis=0)
            top, left = min(top, oy + int(low[0])), min(left, ox + int(low[1]))
            bottom, right = max(bottom, oy + int(high[0]) + 1), max(right, ox + int(high[1]) + 1)
    if bottom <= top or right <= left:
        top, left, bottom, right = 0, 0, 1, 1
    values, answers, statuses = [], [], []
    outside_nonzero = 0
    usable_mask = mask.shape == expected.shape
    for y in range(top, bottom):
        value_row, answer_row, status_row = [], [], []
        for x in range(left, right):
            in_raw = dy <= y < dy + rows and dx <= x < dx + cols
            in_answer = 0 <= y < ah and 0 <= x < aw
            value = str(raw[y-dy, x-dx]) if in_raw else None
            value_row.append(value)
            answer_row.append(str(expected[y, x]) if in_answer else None)
            status_row.append(int(mask[y, x]) if in_answer and usable_mask else 3)
            if not in_answer and value is not None and value != '0':
                outside_nonzero += 1
        values.append(value_row)
        answers.append(answer_row)
        statuses.append(status_row)
    seconds = max(0, float(elapsed_seconds))
    return {
        'schema_version': 1,
        'created_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'elapsed_seconds': seconds,
        'timestamp': f'{int(seconds)//60:02d}:{int(seconds)%60:02d}',
        'correctness': float(official_score),
        'reported_matrix': raw.tolist(),
        'answer_clockwise_degrees': turns * 90,
        'raw_origin': [dy - top, dx - left],
        'outside_nonzero': outside_nonzero,
        'values': values, 'expected': answers, 'status': statuses,
        'counts': {'correct': int(np.count_nonzero(mask == 1)),
                   'incorrect': int(np.count_nonzero(mask == 0)),
                   'ignored': int(np.count_nonzero(mask == 2))},
        'warning': '' if usable_mask else 'The scorer returned no cell-level comparison. Cells are shown as unscored.',
    }


def save_review(report, folder, assets=None):
    assets = Path(assets) if assets is not None else Path(__file__).resolve().parents[2] / 'plugins/robot_windows/MainSupervisorWindow'
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'reported-map.json').write_text(json.dumps(report['reported_matrix'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (folder / 'map-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    html = (assets / 'MapReview.html').read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="MapReview.css">', '<style>' + (assets / 'MapReview.css').read_text(encoding='utf-8') + '</style>')
    data = json.dumps(report, ensure_ascii=True).replace('<', r'\u003c')
    script = '<script type="application/json" id="saved-review">' + data + '</script>'
    script += '<script>' + (assets / 'MapReview.js').read_text(encoding='utf-8') + '</script>'
    html = html.replace('<script src="MapReview.js"></script>', script)
    (folder / 'map-review.html').write_text(html, encoding='utf-8')
    return folder


def open_review(path):
    """Hand off to the default browser without holding up the simulation loop."""
    path = Path(path).resolve()
    def launch():
        try:
            if not webbrowser.open_new_tab(path.as_uri()):
                Console.log_err(f"Could not open the map review browser. Open this file manually: {path}")
        except Exception as error:
            Console.log_err(f"Could not open the map review browser: {error}. Open this file manually: {path}")
    try:
        Thread(target=launch, daemon=True).start()
    except RuntimeError as error:
        Console.log_err(f"Could not start the map review browser: {error}. Open this file manually: {path}")
