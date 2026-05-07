import numpy as np
from PIL import Image
from .constants import OBS_RGB


EMPTY = 0
WALL = -1
FUEL = 1
DEPOSIT = 2
VOTING_ROOM = 3


def _player_value(player, key):
    if isinstance(player, dict):
        return player[key]
    return getattr(player, key)


def render_rgb_from_grid(grid, players, viewer_id, fov=11, out_size=(88, 88)):
    """
    Render an RGB observation for a viewer without leaking roles.
    FOV: 11x11 with forward=9, backward=1, left/right=5 relative to orientation.
    """
    gw, gh = grid.shape
    viewer = players[viewer_id]
    vx, vy = _player_value(viewer, 'position')
    ori = _player_value(viewer, 'orientation')

    forward = 9
    backward = 1
    left = 5
    right = 5

    # construct offsets depending on orientation
    if ori == 'N':
        xs = range(vx - left, vx + right + 1)
        ys = range(vy - forward, vy + backward + 1)
    elif ori == 'S':
        xs = range(vx + left, vx - right - 1, -1)
        ys = range(vy + forward, vy - backward - 1, -1)
    elif ori == 'E':
        xs = range(vx - backward, vx + forward + 1)
        ys = range(vy - left, vy + right + 1)
    else:  # W
        xs = range(vx + backward, vx - forward - 1, -1)
        ys = range(vy + right, vy - left - 1, -1)

    patch = np.zeros((fov, fov, 3), dtype=np.uint8) + 30

    for ix, gx in enumerate(xs):
        for iy, gy in enumerate(ys):
            if 0 <= gx < gw and 0 <= gy < gh:
                cell = grid[gx, gy]
                if cell == EMPTY:
                    color = (40, 40, 40)
                elif cell == FUEL:
                    color = (200, 180, 50)
                elif cell == DEPOSIT:
                    color = (80, 180, 80)
                elif cell == VOTING_ROOM:
                    color = (120, 120, 200)
                else:
                    color = (10, 10, 10)
                patch[ix, iy, :] = color

    # overlay players without role info: show active players as same color
    for pl in players:
        if not _player_value(pl, 'active'):
            continue
        px, py = _player_value(pl, 'position')
        # find relative indices if within the xs,ys ranges
        try:
            rx = list(xs).index(px)
            ry = list(ys).index(py)
            # draw a neutral marker (white)
            patch[rx, ry, :] = (220, 220, 220)
        except ValueError:
            continue

    img = Image.fromarray(patch)
    img = img.resize(out_size, Image.NEAREST)
    return np.array(img)
