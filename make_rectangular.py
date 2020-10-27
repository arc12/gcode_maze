from gcode_maze import RectangularMazeMaker

maker = RectangularMazeMaker(rows=10, cols=20, cell_step=5, end_type="side", centre_void=None,
                             straight_on_bias=1, compass_bias={"N": 5})
maker.make_maze()

# output the gcode
maker.make_gcode("maze.nc",
                 step_size=5,  # mm
                 origin_centre=True,
                 doc_steps=[0.5],  # maybe several passes
                 clearance_height=2,  # mm
                 spindle_speed=8200,  # RPM
                 plunge=300,
                 feed=300  # mm/min
                 )