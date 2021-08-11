from compas.geometry import Point, Line, Polyline, Bezier
from compas_occ.geometry import NurbsCurve
from compas.utilities import pairwise

from compas_view2.app import App
from compas_view2.objects import Collection

points = [Point(0, 0, 0), Point(3, 6, 0), Point(6, -3, 3), Point(10, 0, 0)]
bezier = Bezier(points)
points = bezier.locus(10)

curve = NurbsCurve.from_interpolation(points)

print(curve)

# ==============================================================================
# Visualisation
# ==============================================================================

view = App()

view.add(Polyline(curve.locus()), linewidth=3)
view.add(Collection(curve.points), size=20, color=(1, 0, 0))

for a, b in pairwise(curve.points):
    view.add(Line(a, b), linewidth=1, linecolor=(0.3, 0.3, 0.3))

view.run()