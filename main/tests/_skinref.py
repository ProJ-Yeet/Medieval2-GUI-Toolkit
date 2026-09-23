"""The skin written out longhand in Python, for the suites that check a skin.

``test_v3anim`` holds the page's skin to it and ``test_modelexport`` holds
Blender's import of a ``.glb`` to it: one reference, so the two cannot drift.
"""
from unittransfer import casanim


def reference_skin(msh, anim, t, lift):
    """The skin, written out longhand: v' = R(v - bind) + p, over two weights."""
    def mat(q):
        x, y, z, w = q
        return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    def ap(a, v):
        return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]

    loc = casanim.sample(anim, t)
    R, P, B = [], [], []
    for tr, k in zip(anim.tracks, loc):
        r = mat(k["rot"])
        if tr.parent < 0:
            R.append(r), P.append(list(k["pos"])), B.append(list(tr.pivot))
            continue
        R.append(mul(R[tr.parent], r))
        P.append([a + b for a, b in zip(P[tr.parent], ap(R[tr.parent], k["pos"]))])
        B.append([a + b for a, b in zip(B[tr.parent], tr.pivot)])
    names = {tr.name.lower(): i for i, tr in enumerate(anim.tracks)}
    hub = next(i for i, tr in enumerate(anim.tracks) if tr.parent == 0)
    bm = [names.get(b.lower(), hub) for b in msh.bones]
    out, nrm = [], []
    for v in range(msh.vertices):
        p = msh.positions[v * 3:v * 3 + 3]
        n = msh.normals[v * 3:v * 3 + 3]
        acc, nac = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        for s, byte in ((0, 2), (1, 1)):
            w = msh.weights[v * 2 + s]
            if w <= 0:
                continue
            j = bm[msh.bone_ids[v * 4 + byte]]
            r = ap(R[j], [p[c] - B[j][c] for c in range(3)])
            rn = ap(R[j], n)
            for c in range(3):
                acc[c] += w * (r[c] + P[j][c] + (lift if c == 1 else 0.0))
                nac[c] += w * rn[c]
        out.append(acc)
        nrm.append(nac)
    return out, nrm
