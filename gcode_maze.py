import numpy as np


class PathPart(object):
    def __init__(self, start_cell):
        self.start_cell = start_cell
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


class MazeMakerBase(object):
    def __init__(self):
        # the specialised classes handle the settings
        self.cells = np.ndarray((0, 0))
        self.stack = list()
        self.paths = list()

        self.found_exit = False
        self.last_move = ""

    def _cell_step(self, direction):
        self.paths[-1].add_step(direction)
        dr, dc = self.dir_to_delta[direction]
        from_cell = self.stack[-1]
        to_cell = (from_cell[0] + dr, from_cell[1] + dc)
        self.stack.append(to_cell)
        self.cells[to_cell] = 1

    def _grow(self):
        direction_options = ""
        current_cell = self.stack[-1]
        # if we've just found the exit is adjacent then the path ends, we backtrack, as if we'd hit a dead end
        backtrack = False
        if not self.found_exit:
            for i, offset in enumerate(self.check_points):
                if self.cells[current_cell[0] + offset[0], current_cell[1] + offset[1]] == 2:
                    backtrack = True
                    self.found_exit = True
                    self.paths[-1].add_step(self.compass_points[i])  # show the exit with a stump
                    print("Found exit. Stack length is: {}".format(len(self.stack)))
                    break

        # usual case - check for move options
        if not backtrack:
            for i, offset in enumerate(self.check_points):
                if self.cells[current_cell[0] + offset[0], current_cell[1] + offset[1]] == 0:
                    pt = self.compass_points[i]
                    if self.compass_bias is None:
                        direction_options += pt
                    else:
                        direction_options += pt * (self.compass_bias.get(pt, 0) + 1)
            if len(direction_options) > 0:
                # add extra options for a straight on move if appropriate
                if (self.straight_on_bias > 0) and (self.last_move in direction_options):
                    direction_options += self.last_move * self.straight_on_bias
                # choose a direction and move!
                move = np.random.choice(list(direction_options))
                self._cell_step(move)
                self.last_move = move
                # moved forwards
                return True
        # could not move
        return False

    def _make_maze(self):
        self.found_exit = False
        self.last_move = ""
        working = True
        while working:
            forwards = True
            while forwards:
                forwards = self._grow()

            # if we get here either we found the exit, or there were no options, or we "recursed" and returned, which means no options
            # create a new path fragment, except when we've got to backtrack more than one step
            backtracking = True
            while backtracking:
                if len(self.stack) == 2:
                    working = False
                    break
                check_cell = self.stack[-1]
                for offset in self.check_points:
                    if self.cells[check_cell[0] + offset[0], check_cell[1] + offset[1]] == 0:
                        backtracking = False
                        self.paths.append(PathPart(check_cell))
                        break
                # step back
                if backtracking:
                    self.stack.pop()

    def _make_gcode(self, file_path, step_size, doc_steps, clearance_height, spindle_speed, plunge, feed, origin_offset=(0, 0)):
        """

        :param file_path:
        :type file_path: str
        :type step_size:
        :param doc_steps: depth of cut, multiple passes
        :type doc_steps: list
        :param clearance_height: z height for moves, in mm
        :type clearance_height:
        :param spindle_speed:
        :type spindle_speed:
        :param plunge: in mm/min
        :type plunge:
        :param feed: in mm/min
        :type feed:
        :param origin_offset: for rectangular mazes, this may be used to adjust the origin to the centre of the maze
        :param step_size: in mm
        :return:
        :rtype:
        """

        # !! these better match check_points_all. increasing row = increasing Y (and col for X)
        gcode_steps = {"N": "Y-{length}", "S": "Y{length}", "E": "X{length}", "W": "X-{length}",
                       "A": "X{length} Y-{length}", "B": "X{length} Y{length}", "C": "X-{length} Y{length}", "D": "X-{length} Y-{length}"}

        start_gcode = ["G21", "G90", f"G0 X0 Y0 Z{clearance_height}", f"M3 S{spindle_speed}"]

        def encode_rect_path(rect_path):
            if len(rect_path.steps) > 0:
                y, x = step_size * (rect_path.start_cell[0] - 1) - origin_offset[1], step_size * (rect_path.start_cell[1] - 1) - origin_offset[0]
                gcode = ["G90", f"G0 Z{clearance_height}", f"G0 X{x} Y{y}", f"G1 Z{doc} F{plunge}", "G91", f"F{feed}"]
                print(rect_path.steps)
                for step in rect_path.steps:
                    gcode.append("G1 " + gcode_steps[step[0]].format(length=step_size * (len(step))))
                print(gcode)
                # play it safe
                gcode += ["G90", f"G0 Z{clearance_height}"]
            else:
                gcode = []

            return gcode

        with open(file_path, "w") as f:
            # setup
            f.write('\n'.join(start_gcode))
            f.write('\n')
            # carve paths
            path_type_rect = self.paths[0].steps[0] in "NSEW"
            for doc in doc_steps:
                for p in self.paths:
                    if path_type_rect:
                        f.write('\n'.join(encode_rect_path(p)))
                    else:
                        pass  # circular
                    f.write('\n')
                # add a pause for dust clearance and quality checking
                f.write("M0\n")
            # park neatly
            f.write(f"G90\nG0 Z{clearance_height}\nG0 X0 Y0\nM5\nM30")


class RectangularMazeMaker(MazeMakerBase):
    def __init__(self, rows, cols, cell_step, end_type="side", centre_void=None, straight_on_bias=0, compass_bias=None):
        """

        :param rows:
        :type rows: int
        :param cols:
        :type cols: int
        :param cell_step: mm for GCODE
        :type cell_step:
        :param end_type: side or centre
        :type end_type: str
        :param centre_void: None or a tuple of rows, cols. if None and end_type is "centre" then a minimum size centre void will be created.
        :type centre_void:
        :param straight_on_bias: no of additional "move forwards" options (e.g. if last move was S and the options are SW, randomly select from SWS)
        :type straight_on_bias: int
        :param compass_bias: # additional options if any of these are found as possibles. missing entries = np bias = same as 0 entry
        :type compass_bias: dict|None
        """
        MazeMakerBase.__init__(self)
        self.rows = rows
        self.cols = cols
        self.cell_step = cell_step
        self.end_type = end_type
        self.centre_void = centre_void
        self.straight_on_bias = straight_on_bias
        self.compass_bias = compass_bias

        # operational stuff which is affected by the options
        self.check_points = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # row, col offsets in cells
        self.compass_points = "NSWE"  # order to match check_points
        self.dir_to_delta = {d: delta for (d, delta) in zip(self.compass_points, self.check_points)}

    def make_maze(self):
        """
        Create a random maze using the prescribed settings. The idea is that we might want to create several and choose the one which comes out "best"
        :return:
        :rtype:
        """
        # setup cells
        # row/col [0] and [-1] are boundaries, prefilled except for the entrance/exit
        # cell values: 0=unvisited, 1=visited, 2=exit
        self.cells = np.zeros((self.rows + 2, self.cols + 2))
        self.cells[0, :] = 1
        self.cells[:, 0] = 1
        self.cells[self.rows + 1, :] = 1
        self.cells[:, self.cols + 1] = 1

        mid_col = (self.cols + 1) // 2
        entrance_cell = (0, mid_col)
        entry_direction = "S"

        if self.centre_void is not None or self.end_type == "centre":
            if self.centre_void is None:
                centre_void = (2 + self.rows % 2, 2 + self.cols % 2)
            else:
                centre_void = self.centre_void
            top_row = (self.rows - centre_void[0]) // 2 + 1
            left_col = (self.cols - centre_void[1]) // 2 + 1
            for rr in range(centre_void[0]):
                r = top_row + rr
                for cc in range(centre_void[1]):
                    c = left_col + cc
                    self.cells[r, c] = 1

        if self.end_type == "centre":
            exit_cell = (top_row + centre_void[0] - 1, mid_col)
        else:
            exit_cell = (self.rows + 1, mid_col + (self.cols - 1) % 2)  # stagger the exit if an even no of cols

        self.cells[exit_cell] = 2

        # start the maze
        self.stack = [entrance_cell]
        self.paths = [PathPart(entrance_cell)]
        self._cell_step(entry_direction)

        # continue using base class
        self._make_maze()

    def make_gcode(self, file_path, step_size, doc_steps, clearance_height, spindle_speed, plunge, feed, origin_centre=True):
        """
        Write out the GCode for a previously prepared make_maze(). The idea is that we might create multiple tool-paths for a maze

        :param file_path:
        :type file_path:
        :param step_size:
        :type step_size:
        :param doc_steps:
        :type doc_steps:
        :param clearance_height:
        :type clearance_height:
        :param spindle_speed:
        :type spindle_speed:
        :param plunge:
        :type plunge:
        :param feed:
        :type feed:
        :param origin_centre: whether the GCODE origin will be in the centre
        :type origin_centre: bool
        :return:
        :rtype:
        """
        # set origin - origin is in GCODE space (x, y)
        if origin_centre:
            origin_offset = (self.cols - 1) / 2.0 * self.cell_step, (self.rows - 1) / 2.0 * self.cell_step
        else:
            origin_offset = (0, 0)

        self._make_gcode(file_path, step_size, doc_steps, clearance_height, spindle_speed, plunge, feed, origin_offset=origin_offset)

