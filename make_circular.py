from gcode_maze import CircularMazeMaker

maker = CircularMazeMaker(layers=3, inner_layer_cells=6, centre_void=1)
maker.make_maze()
maker.make_gcode("cmaze.nc",
                 step_size=5,  # mm
                 doc_steps=[0.5],  # maybe several passes
                 clearance_height=2,  # mm
                 spindle_speed=8200,  # RPM
                 plunge=300,
                 feed=300  # mm/min
                 )