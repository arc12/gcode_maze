import numpy as np

# GCODE job settings
SPINDLE_SPEED = 8200
PLUNGE = 300  # mm/min
FEED = 300
DOC_STEPS = [0.5]
CLEARANCE_HEIGHT = 2
ORIGIN_CENTRE = True  # otherwise the origin is a maze corner

# maze size and options
rows = 20
cols = 20
CELL_STEP = 5  # mm for GCODE
end_type = "side"  # side or centre
centre_void = None  # None or a tuple. if None and end_type is "centre" then a minimum size centre void will be created.
# valid directions are NSEWABCD, with ABCD being the compass points NE, SE, SW, NW. Not required to have all compass points; you can make it wierd!
# TODO fix: there is no crossing detection, so using the full set of all valid directions will cause cross-overs. try only AC or BD
use_directions = "NSEW"
# TODO bias randomisation towards either an absolute or a relative (stright on.. ) step
straight_on_bias = 1  # no of additional "move forwards" options (e.g. if last move was S and the options are SW, randomly select from SWS)
# additional options if any of these are found as possibles. missing entries = np bias = same as 0 entry
compass_bias = {"N": 5}

# operational stuff which is affected by the options
# all permitted values
check_points_all = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, 1), (1, -1), (-1, -1)]  # row, col offsets in cells
compass_points_all = "NSWEABCD"  # order to match check_points
# constrain
pairs = [pr for pr in zip(compass_points_all, check_points_all) if pr[0] in use_directions]
dir_to_delta = {d: delta for (d, delta) in pairs}
compass_points = [p[0] for p in pairs]
check_points = [p[1] for p in pairs]


class PathPart(object):
    def __init__(self, start_cell, origin=(0, 0)):  # origin is in GCODE space (x, y)
        self.start_cell = start_cell
        self.origin = origin
        self.steps = []

    def add_step(self, direction):
        """

        :param direction: NSEW
        :type direction:
        :return:
        :rtype:
        """
        if len(self.steps) == 0:
            self.steps = [direction]
        elif self.steps[-1][-1] == direction:
            self.steps[-1] += direction  # e.g. get EEE for 3 consecutive cells travel eastwards
        else:
            self.steps.append(direction)

    def as_gcode(self, step_size, doc):
        """

        :param step_size: in mm
        :type step_size:
        :param doc: depth of cut
        :return:
        :rtype:
        """
        # !! these better match check_points_all. increasing row = increasing Y (and col for X)
        gcode_steps = {"N": "Y-{length}", "S": "Y{length}", "E": "X{length}", "W": "X-{length}",
                       "A": "X{length} Y-{length}", "B": "X{length} Y{length}", "C": "X-{length} Y{length}", "D": "X-{length} Y-{length}"}

        if len(self.steps) > 0:
            y, x = step_size * (self.start_cell[0] - 1) - self.origin[1], step_size * (self.start_cell[1] - 1) - self.origin[0]
            gcode = ["G90", f"G0 Z{CLEARANCE_HEIGHT}", f"G0 X{x} Y{y}", f"G1 Z{doc} F{PLUNGE}", "G91", f"F{FEED}"]
            print(self.steps)
            for step in self.steps:
                gcode.append("G1 " + gcode_steps[step[0]].format(length=step_size * (len(step))))
            print(gcode)
            # play it safe
            gcode += ["G90", f"G0 Z{CLEARANCE_HEIGHT}"]
        else:
            gcode = []

        return gcode


def cell_step(direction):
    paths[-1].add_step(direction)
    dr, dc = dir_to_delta[direction]
    from_cell = stack[-1]
    to_cell = (from_cell[0] + dr, from_cell[1] + dc)
    stack.append(to_cell)
    cells[to_cell] = 1


def grow():
    global found_exit
    global last_move
    direction_options = ""
    current_cell = stack[-1]
    # if we've just found the exit is adjacent then the path ends, we backtrack, as if we'd hit a dead end
    backtrack = False
    if not found_exit:
        for i, offset in enumerate(check_points):
            if cells[current_cell[0] + offset[0], current_cell[1] + offset[1]] == 2:
                backtrack = True
                found_exit = True
                paths[-1].add_step(compass_points[i])  # show the exit with a stump
                print("Found exit. Stack length is: {}".format(len(stack)))
                break

    # usual case - check for move options
    if not backtrack:
        for i, offset in enumerate(check_points):
            if cells[current_cell[0] + offset[0], current_cell[1] + offset[1]] == 0:
                pt = compass_points[i]
                direction_options += pt * (compass_bias.get(pt, 0) + 1)
        if len(direction_options) > 0:
            # add extra options for a straight on move if appropriate
            if (straight_on_bias > 0) and (last_move in direction_options):
                direction_options += last_move * straight_on_bias
            # choose a direction and move!
            move = np.random.choice(list(direction_options))
            cell_step(move)
            last_move = move
            # moved forwards
            return True
    # could not move
    return False


def make_maze():
    working = True
    while working:
        forwards = True
        while forwards:
            forwards = grow()

        # if we get here either we found the exit, or there were no options, or we "recursed" and returned, which means no options
        # create a new path fragment, except when we've got to backtrack more than one step
        backtracking = True
        while backtracking:
            if len(stack) == 2:
                working = False
                break
            check_cell = stack[-1]
            for offset in check_points:
                if cells[check_cell[0] + offset[0], check_cell[1] + offset[1]] == 0:
                    backtracking = False
                    paths.append(PathPart(check_cell, origin))
                    break
            # step back
            if backtracking:
                stack.pop()


# setup cells
# row/col [0] and [-1] are boundaries, prefilled except for the entrance/exit
# cell values: 0=unvisited, 1=visited, 2=exit
cells = np.zeros((rows + 2, cols + 2))
cells[0, :] = 1
cells[:, 0] = 1
cells[rows + 1, :] = 1
cells[:, cols + 1] = 1

mid_col = (cols + 1) // 2
entrance_cell = (0, mid_col)
entry_direction = "S"

if centre_void is not None or end_type == "centre":
    if centre_void is None:
        centre_void = (2 + rows % 2, 2 + cols % 2)
    top_row = (rows - centre_void[0]) // 2 + 1
    left_col = (cols - centre_void[1]) // 2 + 1
    for rr in range(centre_void[0]):
        r = top_row + rr
        for cc in range(centre_void[1]):
            c = left_col + cc
            cells[r, c] = 1

if end_type == "centre":
    exit_cell = (top_row + centre_void[0] - 1, mid_col)
else:
    exit_cell = (rows + 1, mid_col + (cols - 1) % 2)  # stagger the exit if an even no of cols

cells[exit_cell] = 2

# set origin
if ORIGIN_CENTRE:
    origin = (cols - 1) / 2.0 * CELL_STEP, (rows - 1) / 2.0 * CELL_STEP
else:
    origin = (0, 0)

# build the maze
stack = [entrance_cell]
paths = [PathPart(entrance_cell, origin)]
found_exit = False
last_move = ""
cell_step(entry_direction)
make_maze()

# output the gcode
start_gcode = ["G21", "G90", f"G0 X0 Y0 Z{CLEARANCE_HEIGHT}", f"M3 S{SPINDLE_SPEED}"]
with open("maze.nc", "w") as f:
    # setup
    f.write('\n'.join(start_gcode))
    f.write('\n')
    # carve paths
    for doc in DOC_STEPS:
        for p in paths:
            f.write('\n'.join(p.as_gcode(CELL_STEP, doc)))
            f.write('\n')
        # add a pause for dust clearance and quality checking
        f.write("M0\n")
    # park neatly
    f.write(f"G90\nG0 Z{CLEARANCE_HEIGHT}\nG0 X0 Y0\nM5\nM30")
