"""Hoehenfeld -> geschlossenes, mannigfaltiges Dreiecksnetz (wasserdicht) + Reduktion + Export."""
import numpy as np
import trimesh
import fast_simplification


def heightfield_mesh(Z, mask, X, Y):
    """Oberseite = Raster, Waende entlang der Maskenkante, Boden = Faecher von der Plattenmitte.
    Voraussetzung: Maske sternfoermig zur Mitte (abgerundetes Rechteck erfuellt das)."""
    ny, nx = Z.shape
    idx = -np.ones((ny, nx), np.int64)
    idx[mask] = np.arange(int(mask.sum()))
    top_v = np.column_stack([X[mask], Y[mask], Z[mask]]).astype(np.float64)

    a = idx[:-1, :-1]; b = idx[:-1, 1:]; c = idx[1:, :-1]; d = idx[1:, 1:]
    ok = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
    a, b, c, d = a[ok], b[ok], c[ok], d[ok]
    top_f = np.concatenate([np.column_stack([c, d, a]), np.column_stack([d, b, a])])

    # Randkanten (nur einmal benutzt), Orientierung aus der Oberseite uebernehmen
    e = np.concatenate([top_f[:, [0, 1]], top_f[:, [1, 2]], top_f[:, [2, 0]]])
    key = np.sort(e, axis=1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    bnd = e[cnt[inv.ravel()] == 1]
    bverts = np.unique(bnd)
    n_top = len(top_v)
    bmap = -np.ones(n_top, np.int64)
    bmap[bverts] = n_top + np.arange(len(bverts))
    bot_v = top_v[bverts].copy()
    bot_v[:, 2] = 0.0
    center = n_top + len(bverts)
    verts = np.vstack([top_v, bot_v, [[0.0, 0.0, 0.0]]])

    u, v = bnd[:, 0], bnd[:, 1]
    ub, vb = bmap[u], bmap[v]
    walls = np.concatenate([np.column_stack([u, ub, v]), np.column_stack([v, ub, vb])])
    bottom = np.column_stack([np.full(len(u), center), vb, ub])
    faces = np.vstack([top_f, walls, bottom])
    return verts, faces


def decimate(verts, faces, target_faces):
    red = 1.0 - min(1.0, target_faces / float(len(faces)))
    if red <= 0:
        return verts, faces
    v2, f2 = fast_simplification.simplify(verts.astype(np.float32), faces.astype(np.int64), red, agg=6)
    return v2.astype(np.float64), f2


def to_trimesh(verts, faces):
    """Netz aufbauen und Reduktionsartefakte entfernen (Null-Flaechen-Dreiecke, die als
    gefaltetes Paar eine Kante vierfach belegen koennen)."""
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=True, validate=False)
    m.merge_vertices()
    tri = m.triangles
    area2 = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    keep = area2 > 1e-12
    m.update_faces(keep)
    m.update_faces(m.unique_faces())
    m.remove_unreferenced_vertices()
    return m


def decimate_watertight(verts, faces, target_faces, tries=6):
    """Reduzieren und pruefen; bei Topologiefehlern mit leicht anderem Ziel wiederholen."""
    for k in range(tries):
        tgt = int(target_faces * (1 - 0.03 * k))
        v2, f2 = decimate(verts, faces, tgt)
        m = to_trimesh(v2, f2)
        if m.is_watertight and m.is_winding_consistent and m.is_volume:
            return m
    m = to_trimesh(verts, faces)          # Rueckfall: unreduziertes (sicher geschlossenes) Netz
    return m


def mesh_report(m):
    return dict(faces=int(len(m.faces)), watertight=bool(m.is_watertight),
                winding_consistent=bool(m.is_winding_consistent), volume_ok=bool(m.is_volume),
                volume_cm3=round(float(m.volume) / 1000.0, 2),
                bounds=[[round(float(v), 3) for v in row] for row in m.bounds])


def export(m, path_stem):
    m.export(str(path_stem) + ".stl")
    name = str(path_stem).replace("\\", "/").split("/")[-1]
    trimesh.Scene({name: m}).export(str(path_stem) + ".3mf")
