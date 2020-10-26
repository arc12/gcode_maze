# GCode Maze
Generate some mazes using DFS and back-tracking, generating the output as CNC GCode.

Motivations:
- most maze generators produce walls, but for a CNC router, paths are more useful.
- GCode generation from SVG doesn't work nicely as the output is lines, and moset GCode generators expect closed shapes.
- those points make for boring faffing about and I'd rather write some code to save that PITA

This is quite rough and ready at the moment and would benefit from rework to make it "nicer".

TODOs:
- write documentation (this is mostly obvious from the code comments
- circular mazes
