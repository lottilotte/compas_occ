from typing import List

import compas.geometry
import compas.datastructures

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.geometry import Point
from compas.datastructures import Mesh

from OCC.Core.gp import gp_Pnt
from OCC.Core.gp import gp_Dir
from OCC.Core.gp import gp_Ax2

from OCC.Core.TopoDS import TopoDS_Shell
from OCC.Core.TopoDS import TopoDS_Shape

from OCC.Core.TopExp import TopExp_Explorer

from OCC.Core.TopAbs import TopAbs_VERTEX
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopAbs import TopAbs_WIRE
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopAbs import TopAbs_Orientation
from OCC.Core.TopAbs import TopAbs_ShapeEnum

from OCC.Core.BRep import BRep_Builder

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert

# from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Sewing

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse

from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location

from OCC.Core.STEPControl import STEPControl_Writer
from OCC.Core.STEPControl import STEPControl_AsIs
from OCC.Core.Interface import Interface_Static_SetCVal
from OCC.Core.IFSelect import IFSelect_RetDone

from OCC.Core.ShapeFix import ShapeFix_Shell
from OCC.Core.BRepCheck import BRepCheck_Shell
from OCC.Core.BRepCheck import BRepCheck_Status

from compas_occ.conversions import triangle_to_face
from compas_occ.conversions import quad_to_face
from compas_occ.conversions import ngon_to_face
from compas_occ.conversions import points1_from_array1

from compas_occ.geometry import OCCNurbsCurve
from compas_occ.geometry import OCCNurbsSurface

from compas_occ.brep import BRepVertex
from compas_occ.brep import BRepEdge
from compas_occ.brep import BRepLoop
from compas_occ.brep import BRepFace


class BRep(Data):
    """Class for Boundary Representation of geometric entities.

    Attributes
    ----------
    vertices : list[:class:`~compas_occ.brep.BRepVertex`], read-only
        The vertices of the BRep.
    edges : list[:class:`~compas_occ.brep.BRepEdge`], read-only
        The edges of the BRep.
    loops : list[:class:`~compas_occ.brep.BRepLoop`], read-only
        The loops of the BRep.
    faces : list[:class:`~compas_occ.brep.BRepFace`], read-only
        The faces of the BRep.
    frame : :class:`~compas.geometry.Frame`, read-only
        The local coordinate system of the BRep.
    area : float, read-only
        The surface area of the BRep.
    volume : float, read-only
        The volume of the regions contained by the BRep.

    Other Attributes
    ----------------
    occ_shape : ``TopoDS_Shape``
        The underlying OCC shape of the BRep.
    type : {TopAbs_COMPOUND, TopAbs_COMPSOLID, TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SHAPE}, read-only
        The type of BRep shape.
    orientation : {TopAbs_FORWARD, TopAbs_REVERSED, TopAbs_INTERNAL, TopAbs_EXTERNAL}, read-only
        Orientation of the shape.

    Examples
    --------
    Constructors

    >>> brep = BRep.from_corners([0, 0, 0], [1, 0, 0], [1, 1, 1], [1, 1, 0])

    >>> from compas.geometry import Box
    >>> box = Box.from_width_height_depth(1, 1, 1)
    >>> vertices, faces = box.to_vertices_and_faces()
    >>> polygons = [[vertices[index] for index in face] for face in faces]
    >>> brep = BRep.from_polygons(polygons)

    >>> from compas.geometry import Box
    >>> box = Box.from_width_height_depth(1, 1, 1)
    >>> brep = BRep.from_box(box)

    >>> from compas.geometry import Box, Sphere
    >>> box = Box.from_width_height_depth(1, 1, 1)
    >>> sphere = Sphere([1, 1, 1], 0.5)
    >>> A = BRep.from_box(box)
    >>> B = BRep.from_sphere(sphere)
    >>> brep = BRep.from_boolean_union(A, B)

    Booleans

    >>> from compas.geometry import Box, Sphere
    >>> box = Box.from_width_height_depth(1, 1, 1)
    >>> sphere = Sphere([1, 1, 1], 0.5)
    >>> A = BRep.from_box(box)
    >>> B = BRep.from_sphere(sphere)
    >>> C = A + B
    >>> D = A - B
    >>> E = A & B

    """

    def __init__(self) -> None:
        super().__init__()
        self._occ_shape = None

    # ==============================================================================
    # Data
    # ==============================================================================

    @property
    def data(self):
        faces = []
        for face in self.faces:
            boundary = []
            for edge in face.loops[0].edges:
                curvedata = edge.nurbscurve.data
                boundary.append(curvedata)
            holes = []
            for loop in face.loops[1:]:
                pass
            surfacedata = face.nurbssurface.data
            faces.append({"boundary": boundary, "surface": surfacedata, "holes": holes})
        return {"faces": faces}

    @data.setter
    def data(self, data):
        faces = []
        for j, facedata in enumerate(data["faces"]):
            # underlying geometry
            surface = OCCNurbsSurface.from_data(facedata["surface"])
            # boundary loop from edge curves
            edges = []
            for curvedata in facedata["boundary"]:
                curve = OCCNurbsCurve.from_data(curvedata)
                edge = BRepEdge.from_curve(curve)
                edges.append(edge)
            loop = BRepLoop.from_edges(edges)
            # boundary loop of the first face needs to be flipped
            # store orientation?
            # reverse based on orientation info?
            # if j == 0:
            #     loop.occ_wire.Reverse()
            # face from surface and boundary
            face = BRepFace.from_surface(surface, loop=loop)
            # add holes
            for hole in facedata["holes"]:
                pass
            # collect
            faces.append(face)
        # recreate shape
        self.occ_shape = BRep.from_faces(faces).occ_shape
        # self.sew()
        # self.fix()

    # ==============================================================================
    # Customization
    # ==============================================================================

    def __add__(self, other):
        """Compute the boolean union using the "+" operator of this BRep and another.

        Parameters
        ----------
        other : :class:`compas_occ.brep.BRep`
            The BRep to add.

        Returns
        -------
        :class:`compas_occ.brep.BRep`
            The resulting BRep.

        """
        return BRep.from_boolean_union(self, other)

    def __sub__(self, other):
        """Compute the boolean difference using the "-" operator of this shape and another.

        Parameters
        ----------
        other : :class:`compas_occ.brep.BRep`
            The BRep to subtract.

        Returns
        -------
        :class:`compas_occ.brep.BRep`
            The resulting BRep.

        """
        return BRep.from_boolean_difference(self, other)

    def __and__(self, other):
        """Compute the boolean intersection using the "&" operator of this shape and another.

        Parameters
        ----------
        other : :class:`compas_occ.brep.BRep`
            The BRep to intersect with.

        Returns
        -------
        :class:`compas_occ.brep.BRep`
            The resulting BRep.

        """
        return BRep.from_boolean_intersection(self, other)

    # ==============================================================================
    # Properties
    # ==============================================================================

    @property
    def occ_shape(self) -> TopoDS_Shape:
        return self._occ_shape

    @occ_shape.setter
    def occ_shape(self, shape: TopoDS_Shape) -> None:
        self._occ_shape = shape

    @property
    def type(self) -> TopAbs_ShapeEnum:
        return self.occ_shape.ShapeType()

    @property
    def points(self) -> List[Point]:
        points = []
        for vertex in self.vertices:
            points.append(vertex.point)
        return points

    @property
    def curves(self) -> List[OCCNurbsCurve]:
        curves = []
        for edge in self.edges:
            curves.append(edge.nurbscurve)
        return curves

    @property
    def surfaces(self) -> List[OCCNurbsSurface]:
        surfaces = []
        for face in self.faces:
            surfaces.append(face.nurbssurface)
        return surfaces

    @property
    def vertices(self) -> List[BRepVertex]:
        vertices = []
        explorer = TopExp_Explorer(self.occ_shape, TopAbs_VERTEX)
        while explorer.More():
            vertex = explorer.Current()
            vertices.append(BRepVertex(vertex))
            explorer.Next()
        return vertices

    @property
    def edges(self) -> List[BRepEdge]:
        edges = []
        explorer = TopExp_Explorer(self.occ_shape, TopAbs_EDGE)
        while explorer.More():
            edge = explorer.Current()
            edges.append(BRepEdge(edge))
            explorer.Next()
        return edges

    @property
    def loops(self) -> List[BRepLoop]:
        loops = []
        explorer = TopExp_Explorer(self.occ_shape, TopAbs_WIRE)
        while explorer.More():
            wire = explorer.Current()
            loops.append(BRepLoop(wire))
            explorer.Next()
        return loops

    @property
    def faces(self) -> List[BRepFace]:
        faces = []
        explorer = TopExp_Explorer(self.occ_shape, TopAbs_FACE)
        while explorer.More():
            face = explorer.Current()
            faces.append(BRepFace(face))
            explorer.Next()
        return faces

    @property
    def orientation(self) -> TopAbs_Orientation:
        return TopAbs_Orientation(self.occ_shape.Orientation())

    @property
    def frame(self) -> compas.geometry.Frame:
        location = self.occ_shape.Location()
        transformation = location.Transformation()
        T = Transformation(
            matrix=[[transformation.Value(i, j) for j in range(4)] for i in range(4)]
        )
        frame = Frame.from_transformation(T)
        return frame

    @property
    def area(self) -> float:
        pass

    @property
    def volume(self) -> float:
        pass

    # ==============================================================================
    # Constructors
    # ==============================================================================

    @classmethod
    def from_polygons(cls, polygons: List[compas.geometry.Polygon]) -> "BRep":
        """Construct a BRep from a set of polygons.

        Parameters
        ----------
        polygons : list[:class:`~compas.geometry.Polygon`]

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        shell = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(shell)
        for points in polygons:
            if len(points) == 3:
                builder.Add(shell, triangle_to_face(points))
            elif len(points) == 4:
                builder.Add(shell, quad_to_face(points))
            else:
                builder.Add(shell, ngon_to_face(points))
        brep = cls()
        brep.occ_shape = shell
        brep.sew()
        brep.fix()
        return brep

    @classmethod
    def from_curves(cls, curves: List[compas.geometry.NurbsCurve]) -> "BRep":
        """Construct a BRep from a set of curves.

        Parameters
        ----------
        curves : list[:class:`~compas.geometry.NurbsCurve`]

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        raise NotImplementedError

    @classmethod
    def from_box(cls, box: compas.geometry.Box) -> "BRep":
        """Construct a BRep from a COMPAS box.

        Parameters
        ----------
        box : :class:`~compas.geometry.Box`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        xaxis = box.frame.xaxis.scaled(-0.5 * box.xsize)
        yaxis = box.frame.yaxis.scaled(-0.5 * box.ysize)
        zaxis = box.frame.zaxis.scaled(-0.5 * box.zsize)
        frame = box.frame.transformed(Translation.from_vector(xaxis + yaxis + zaxis))
        ax2 = gp_Ax2(gp_Pnt(*frame.point), gp_Dir(*frame.zaxis), gp_Dir(*frame.xaxis))
        brep = cls()
        brep.occ_shape = BRepPrimAPI_MakeBox(
            ax2, box.xsize, box.ysize, box.zsize
        ).Shape()
        return brep

    @classmethod
    def from_sphere(cls, sphere: compas.geometry.Sphere) -> "BRep":
        """Construct a BRep from a COMPAS sphere.

        Parameters
        ----------
        sphere : :class:`~compas.geometry.Sphere`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        brep = cls()
        brep.occ_shape = BRepPrimAPI_MakeSphere(
            gp_Pnt(*sphere.point), sphere.radius
        ).Shape()
        return brep

    @classmethod
    def from_cylinder(cls, cylinder: compas.geometry.Cylinder) -> "BRep":
        """Construct a BRep from a COMPAS cylinder.

        Parameters
        ----------
        cylinder : :class:`~compas.geometry.Cylinder`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        plane = cylinder.circle.plane
        height = cylinder.height
        radius = cylinder.circle.radius
        frame = Frame.from_plane(plane)
        frame.transform(Translation.from_vector(frame.zaxis * (-0.5 * height)))
        ax2 = gp_Ax2(gp_Pnt(*frame.point), gp_Dir(*frame.zaxis), gp_Dir(*frame.xaxis))
        brep = cls()
        brep.occ_shape = BRepPrimAPI_MakeCylinder(ax2, radius, height).Shape()
        return brep

    @classmethod
    def from_cone(cls, cone: compas.geometry.Cone) -> "BRep":
        """Construct a BRep from a COMPAS cone.

        Parameters
        ----------
        cone : :class:`~compas.geometry.Cone`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        raise NotImplementedError

    @classmethod
    def from_torus(cls, torus: compas.geometry.Torus) -> "BRep":
        """Construct a BRep from a COMPAS torus.

        Parameters
        ----------
        torus : :class:`~compas.geometry.Torus`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        raise NotImplementedError

    @classmethod
    def from_mesh(cls, mesh: compas.datastructures.Mesh) -> "BRep":
        """Construct a BRep from a COMPAS mesh.

        Parameters
        ----------
        mesh : :class:`~compas.datastructures.Mesh`

        Returns
        -------
        :class:`BRep`

        """
        shell = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(shell)
        for face in mesh.faces():
            points = mesh.face_coordinates(face)
            if len(points) == 3:
                builder.Add(shell, triangle_to_face(points))
            elif len(points) == 4:
                builder.Add(shell, quad_to_face(points))
            else:
                builder.Add(shell, ngon_to_face(points))
        brep = cls()
        brep.occ_shape = shell
        brep.sew()
        brep.fix()
        return brep

    @classmethod
    def from_faces(cls, faces: List[BRepFace]) -> "BRep":
        """Make a BRep from a list of BRep faces forming an open or closed shell.

        Parameters
        ----------
        faces : list[:class:`BRepFace`]

        Returns
        -------
        :class:`BRep`

        """
        shell = TopoDS_Shell()
        builder = BRep_Builder()
        builder.MakeShell(shell)
        for face in faces:
            if not face.is_valid():
                face.fix()
            builder.Add(shell, face.occ_face)
        brep = cls()
        brep.occ_shape = shell
        brep.sew()
        brep.fix()
        return brep

    @classmethod
    def from_extrusion(cls, curve, vector) -> "BRep":
        pass

    @classmethod
    def from_sweep(cls, profile, path) -> "BRep":
        pass

    # create pipe
    # create patch
    # create offset

    # ==============================================================================
    # Boolean Constructors
    # ==============================================================================

    @classmethod
    def from_boolean_difference(cls, A: "BRep", B: "BRep") -> "BRep":
        """Construct a BRep from the boolean difference of two other BReps.

        Parameters
        ----------
        A : :class:`~compas_occ.brep.BRep`
        B : :class:`~compas_occ.brep.BRep`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        cut = BRepAlgoAPI_Cut(A.occ_shape, B.occ_shape)
        if not cut.IsDone():
            raise Exception("Boolean difference operation could not be completed.")
        brep = cls()
        brep.occ_shape = cut.Shape()
        return brep

    @classmethod
    def from_boolean_intersection(cls, A: "BRep", B: "BRep") -> "BRep":
        """Construct a BRep from the boolean intersection of two other BReps.

        Parameters
        ----------
        A : :class:`~compas_occ.brep.BRep`
        B : :class:`~compas_occ.brep.BRep`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        common = BRepAlgoAPI_Common(A.occ_shape, B.occ_shape)
        if not common.IsDone():
            raise Exception("Boolean intersection operation could not be completed.")
        brep = cls()
        brep.occ_shape = common.Shape()
        return brep

    @classmethod
    def from_boolean_union(cls, A: "BRep", B: "BRep") -> "BRep":
        """Construct a BRep from the boolean union of two other BReps.

        Parameters
        ----------
        A : :class:`~compas_occ.brep.BRep`
        B : :class:`~compas_occ.brep.BRep`

        Returns
        -------
        :class:`~compas_occ.brep.BRep`

        """
        fuse = BRepAlgoAPI_Fuse(A.occ_shape, B.occ_shape)
        if not fuse.IsDone():
            raise Exception("Boolean union operation could not be completed.")
        brep = cls()
        brep.occ_shape = fuse.Shape()
        return brep

    # ==============================================================================
    # Converters
    # ==============================================================================

    def to_json(self, filepath: str):
        """Export the BRep to a JSON file.

        Parameters
        ----------
        filepath : str
            Location of the file.

        Returns
        -------
        None

        """
        with open(filepath, "w") as f:
            self.occ_shape.DumpJson(f)

    def to_step(self, filepath: str, schema: str = "AP203", unit: str = "MM") -> None:
        """Write the BRep shape to a STEP file.

        Parameters
        ----------
        filepath : str
            Location of the file.
        schema : str, optional
            STEP file format schema.
        unit : str, optional
            Base units for the geometry in the file.

        Returns
        -------
        None

        """
        step_writer = STEPControl_Writer()
        Interface_Static_SetCVal("write.step.schema", schema)
        Interface_Static_SetCVal("write.step.unit", unit)
        step_writer.Transfer(self.occ_shape, STEPControl_AsIs)
        status = step_writer.Write(filepath)
        assert status == IFSelect_RetDone, "STEP writing failed."

    def to_tesselation(self, linear_deflection: float = 1e-3) -> Mesh:
        """Create a tesselation of the shape for visualisation.

        Parameters
        ----------
        linear_deflection : float, optional
            Allowable deviation between curved geometry and mesh discretisation.

        Returns
        -------
        :class:`~compas.datastructures.Mesh`

        """
        mesh = Mesh()
        BRepMesh_IncrementalMesh(self.occ_shape, linear_deflection)
        bt = BRep_Tool()
        for face in self.faces:
            location = TopLoc_Location()
            triangulation = bt.Triangulation(face.occ_face, location)
            nodes = triangulation.Nodes()
            vertices = points1_from_array1(nodes)
            faces = []
            triangles = triangulation.Triangles()
            for i in range(1, triangulation.NbTriangles() + 1):
                triangle = triangles.Value(i)
                u, v, w = triangle.Get()
                faces.append([u - 1, v - 1, w - 1])
            other = Mesh.from_vertices_and_faces(vertices, faces)
            mesh.join(other)
        return mesh

    def to_meshes(self, u=16, v=16):
        """Convert the faces of the BRep shape to meshes.

        Parameters
        ----------
        u : int, optional
            The number of mesh faces in the U direction of the underlying surface geometry of every face of the BRep.
        v : int, optional
            The number of mesh faces in the V direction of the underlying surface geometry of every face of the BRep.

        Returns
        -------
        list[:class:`~compas.datastructures.Mesh`]

        """
        converter = BRepBuilderAPI_NurbsConvert(self.occ_shape, False)
        brep = BRep()
        brep.occ_shape = converter.Shape()
        meshes = []
        for face in brep.faces:
            srf = OCCNurbsSurface.from_face(face.occ_face)
            mesh = srf.to_tesselation()
            meshes.append(mesh)
        return meshes

    # make meshes from the loops
    # use gmsh to generate proper mesh

    # ==============================================================================
    # Methods
    # ==============================================================================

    # def make_solid(self):
    #     """Convert the current shape to a solid.

    #     Returns
    #     -------
    #     None

    #     """
    #     self.occ_shape = BRepBuilderAPI_MakeSolid(self.occ_shape).Solid()

    def check(self):
        """Check the shape.

        Returns
        -------
        None

        """
        if self.type == TopAbs_ShapeEnum.TopAbs_SHELL:
            check = BRepCheck_Shell(self.occ_shape)
            print(BRepCheck_Status(check.Closed()))
            print(BRepCheck_Status(check.Orientation()))

    def sew(self):
        """Sew together the individual parts of the shape.

        Returns
        -------
        None

        """
        if len(self.faces) > 1:
            sewer = BRepBuilderAPI_Sewing()
            sewer.Load(self.occ_shape)
            sewer.Perform()
            self.occ_shape = sewer.SewedShape()

    def fix(self):
        """Fix the shell.

        Returns
        -------
        None

        """
        if self.type == TopAbs_ShapeEnum.TopAbs_SHELL:
            fixer = ShapeFix_Shell(self.occ_shape)
            fixer.Perform()
            self.occ_shape = fixer.Shell()

    def is_orientable(self) -> bool:
        """Check if the shape is orientable.

        Returns
        -------
        bool

        """
        return self.occ_shape.Orientable()

    def is_closed(self) -> bool:
        """Check if the shape is closed.

        Returns
        -------
        bool

        """
        return self.occ_shape.Closed()

    def is_infinite(self) -> bool:
        """Check if the shape is infinite.

        Returns
        -------
        bool

        """
        return self.occ_shape.Infinite()

    def is_convex(self) -> bool:
        """Check if the shape is convex.

        Returns
        -------
        bool

        """
        return self.occ_shape.Convex()

    def is_manifold(self) -> bool:
        """Check if the shape is manifold.

        Returns
        -------
        bool

        Notes
        -----
        A BRep is non-manifold if at least one edge is shared by more than two faces.

        """
        pass

    def is_solid(self) -> bool:
        """Check if the shape is a solid.

        Returns
        -------
        bool

        """
        pass

    def is_surface(self) -> bool:
        """Check if the shape is a surface.

        Returns
        -------
        bool

        """
        pass

    def cull_unused_vertices(self) -> None:
        """Remove all unused vertices.

        Returns
        -------
        None

        """
        pass

    def cull_unused_edges(self) -> None:
        """Remove all unused edges.

        Returns
        -------
        None

        """
        pass

    def cull_unused_loops(self) -> None:
        """Remove all unused loops.

        Returns
        -------
        None

        """
        pass

    def cull_unused_faces(self) -> None:
        """Remove all unused faces.

        Returns
        -------
        None

        """
        pass

    # flip
    # join
    # join edges
    # join naked edges
    # merge coplanar faces
    # remove fins
    # remove holes
    # repair
    # rotate
    # scale
    # split
    # trim
    # transform
    # rotate
    # translate
    # unjoin edges

    def contours(
        self, planes: List[compas.geometry.Plane]
    ) -> List[List[compas.geometry.Polyline]]:
        """Generate contour lines by slicing the BRep shape with a series of planes.

        Parameters
        ----------
        planes : list[:class:`~compas.geometry.Plane`]
            The slicing planes.

        Returns
        -------
        list[list[:class:`~compas.geometry.Polyline`]]
            A list of polylines per plane.

        """
        pass
