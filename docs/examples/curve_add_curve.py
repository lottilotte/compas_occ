from compas.geometry import Point
from compas.geometry import Polyline, Bezier
from compas_occ.geometry import OCCNurbsCurve
from compas_view2.app import App
from compas_view2.objects import Collection


points = [Point(0, 0, 0), Point(3, 0, 0), Point(6, -3, 0), Point(10, 0, 0)]
curve = OCCNurbsCurve.from_interpolation(points)

vector = curve.tangent_at(0)
pt = Point(*(Point(0, 0, 0) - vector))
points1 = [pt, Point(0, 0, 0)]
points1 = [Point(-4, 3, 0), Point(0, 0, 0)]
curve1 = OCCNurbsCurve.from_interpolation(points1)

curve_new = curve.joined(curve1)

# print(curve.add_curve(curve1))

# ==============================================================================
# Visualisation
# ==============================================================================

view = App()

view.add(Polyline(curve.locus()), linewidth=3)
view.add(Polyline(curve_new.locus()), linewidth=3)
# view.add(Polyline(curve1.locus()), linewidth=3)
view.add(Collection(points))
view.add(Collection(points1))

view.run()
