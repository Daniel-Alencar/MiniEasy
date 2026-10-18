#!/usr/bin/env python3
"""Monta a PCB do altimetro a partir do esquematico.

Uso:
  python3 build_pcb.py place  <dir-projeto> <dir-trabalho>
  python3 build_pcb.py finish <dir-projeto> <dir-trabalho>

'place' cria <trabalho>/altimetro.kicad_pcb com footprints posicionados, contorno,
furos e netclasses, e escreve <trabalho>/altimetro.dsn para o Freerouting.
'finish' importa <trabalho>/altimetro.ses, cria os planos de GND, preenche,
ajusta a serigrafia e grava <trabalho>/altimetro.kicad_pcb.
"""
import sys, os, re, json, math, copy, subprocess, xml.etree.ElementTree as ET
import pcbnew

FPDIR = "/usr/share/kicad/footprints"

# ------------------------------------------------------------------ placa
W, H = 66.0, 26.0           # mm
OX, OY = 100.0, 100.0       # origem do contorno na folha
CORNER_R = 1.5

# netclasses: largura de trilha / folga (mm)
CLASSES = {
    "PIRO":  dict(track_width=0.8, clearance=0.3, patterns=["*VBAT", "*PYRO_A", "*PYRO_B"]),
    "POWER": dict(track_width=0.4, clearance=0.2, patterns=["+3V3", "*VSYS", "*VBUS", "GND"]),
}
DEFAULT_TRACK, DEFAULT_CLEAR = 0.25, 0.2

# posicoes fixas (mm relativos ao canto superior esquerdo da placa), rotacao em graus
TERM_Y = H - 4.85           # marcador de pino 1 do borne vai ate y=+4,49; 0,36 mm de folga da borda
FIXED = {
    "H1":  (3.6, H / 2, 0),
    "H2":  (W - 3.6, H / 2, 0),
    "J1":  (10.0, TERM_Y, 0),
    "J4":  (18.5, TERM_Y, 0),
    "J5":  (27.0, TERM_Y, 0),
    "LS1": (W - 13.0, H - 5.6, 0),
    "J3":  (10.5, 2.65, 180),      # micro-USB na borda superior (marca "PCB Edge" em y=+2.65)
    "C1":  (11.5, 11.0, 90),       # reservatorio do disparo, junto a J1 (acima da faixa do rotulo)
    "U1":  (19.5, 9.0, 0),
    "U2":  (34.0, 9.5, 0),
    "U4":  (49.5, 6.0, 0),
    "U3":  (W - 8.0, 5.0, 0),
    "J2":  (44.0, 12.2, 90),       # SWD ao lado de PA13/PA14
}

# ordem e ancoras do posicionamento guloso: ref -> (ref_ancora, pad_ancora)
GREEDY = [
    ("U5", ("J3", "3")),
    ("Q1", ("J4", "2")), ("Q2", ("J5", "2")), ("Q3", ("LS1", "2")),
    ("D1", ("U1", "2")), ("D2", ("U1", "2")), ("C2", ("U1", "2")),
    ("C3", ("U1", "3")), ("C4", ("U1", "3")),
    ("C6", ("U2", "1")), ("C9", ("U2", "5")), ("C7", ("U2", "17")),
    ("C8", ("U2", "1")), ("C10", ("U2", "5")), ("C11", ("U2", "4")),
    ("R3", ("U2", "31")), ("JP1", ("U2", "31")),
    ("C12", ("U3", "1")), ("C13", ("U4", "8")), ("R4", ("U4", "3")), ("R5", ("U4", "7")),
    ("C14", ("J3", "1")), ("C15", ("U5", "5")), ("R6", ("J3", "1")), ("R7", ("U2", "14")),
    ("R8", ("Q1", "1")), ("R9", ("Q1", "1")), ("R10", ("Q1", "3")), ("R11", ("U2", "6")),
    ("C16", ("U2", "6")),
    ("R12", ("Q2", "1")), ("R13", ("Q2", "1")), ("R14", ("Q2", "3")), ("R15", ("U2", "7")),
    ("C17", ("U2", "7")),
    ("R1", ("J1", "1")), ("R2", ("U2", "8")), ("C5", ("U2", "8")),
    ("R16", ("Q3", "1")), ("R17", ("Q3", "1")), ("D3", ("Q3", "3")),
    ("R18", ("U2", "25")), ("D4", ("U2", "25")),
]
MARGIN = 0.15               # folga extra entre courtyards (mm)
LABEL_BAND = 2.0            # faixa acima dos bornes: texto de 0,8 mm ocupa ~1,5 mm + folgas
EDGE = 0.4                  # courtyard ate a borda (mm), exceto pecas de borda


def mm(v):
    return pcbnew.FromMM(v)


def tomm(v):
    return pcbnew.ToMM(v)


# ------------------------------------------------------------------ netlist
def read_netlist(projdir, work):
    sch = os.path.join(projdir, "altimetro.kicad_sch")
    xmlp = os.path.join(work, "net.xml")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
                    "-o", xmlp, sch], check=True, capture_output=True)
    root = ET.parse(xmlp).getroot()
    comps = {}
    for c in root.find("components"):
        ts = c.find("tstamps")
        comps[c.get("ref")] = dict(value=c.findtext("value"), footprint=c.findtext("footprint"),
                                   uuid=(ts.text or "").split()[0])
    nets = {}
    for n in root.find("nets"):
        nets[n.get("name")] = [(x.get("ref"), x.get("pin")) for x in n.findall("node")]
    return comps, nets


# ------------------------------------------------------------------ geometria
def crt_box(fp):
    """Caixa do courtyard (F e B) em mm: (x0, y0, x1, y1)."""
    boxes = []
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        poly = fp.GetCourtyard(layer)
        if poly.OutlineCount():
            bb = poly.BBox()
            boxes.append((tomm(bb.GetLeft()), tomm(bb.GetTop()), tomm(bb.GetRight()), tomm(bb.GetBottom())))
    if not boxes:
        bb = fp.GetBoundingBox(False)
        boxes.append((tomm(bb.GetLeft()), tomm(bb.GetTop()), tomm(bb.GetRight()), tomm(bb.GetBottom())))
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def overlaps(a, b, m=0.0):
    return not (a[2] + m <= b[0] or b[2] + m <= a[0] or a[3] + m <= b[1] or b[3] + m <= a[1])


def set_pose(fp, x, y, rot):
    fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
    fp.SetOrientationDegrees(rot)


def pad_pos(fp, num):
    for p in fp.Pads():
        if p.GetNumber() == num:
            return tomm(p.GetPosition().x) - OX, tomm(p.GetPosition().y) - OY
    raise KeyError("%s pad %s" % (fp.GetReference(), num))


# ------------------------------------------------------------------ place
def place(projdir, work):
    comps, nets = read_netlist(projdir, work)
    pcb_path = os.path.join(work, "altimetro.kicad_pcb")
    for f in ("altimetro.kicad_pcb", "altimetro.kicad_pro", "altimetro.kicad_prl"):
        if os.path.exists(os.path.join(work, f)):
            os.remove(os.path.join(work, f))
    board = pcbnew.NewBoard(pcb_path)

    # nets
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pinnet = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pinnet[(ref, pin)] = name

    # footprints do esquematico
    fps = {}
    for ref, c in sorted(comps.items()):
        lib, name = c["footprint"].split(":", 1)
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
        if fp is None:
            raise SystemExit("footprint nao encontrado: " + c["footprint"])
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        fp.SetSheetname("/")
        fp.SetSheetfile("altimetro.kicad_sch")
        for p in fp.Pads():
            key = (ref, p.GetNumber())
            if key in pinnet:
                p.SetNet(netinfo[pinnet[key]])
        board.Add(fp)
        fps[ref] = fp

    # header SWD de passo 1,27 mm: nao cabem 2 raios termicos entre pads vizinhos;
    # o pad de GND e pequeno e solda bem com ligacao solida
    for p in fps["J2"].Pads():
        if p.GetNetname() == "GND":
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    # furos de fixacao (so placa)
    for ref in ("H1", "H2"):
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, "MountingHole.pretty"), "MountingHole_3.2mm_M3")
        fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_3.2mm_M3"))
        fp.SetReference(ref)
        fp.SetValue("M3")
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        board.Add(fp)
        fps[ref] = fp

    # contorno com cantos arredondados
    r = CORNER_R
    segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
    for (x0, y0), (x1, y1) in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(OX + x0), mm(OY + y0)))
        s.SetEnd(pcbnew.VECTOR2I(mm(OX + x1), mm(OY + y1)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
    for cx, cy, sx, sy in ((r, r, 0, r), (W - r, r, W - r, 0), (W - r, H - r, W, H - r), (r, H - r, r, H)):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(pcbnew.VECTOR2I(mm(OX + cx), mm(OY + cy)))
        a.SetStart(pcbnew.VECTOR2I(mm(OX + sx), mm(OY + sy)))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(mm(0.1))
        board.Add(a)

    # posicoes fixas
    occupied = []
    for ref, (x, y, rot) in FIXED.items():
        set_pose(fps[ref], x, y, rot)
        bx = crt_box(fps[ref])
        occupied.append((ref, (bx[0] - OX, bx[1] - OY, bx[2] - OX, bx[3] - OY)))

    # faixa reservada acima de cada borne para o rotulo de serigrafia (APO/PRI/+BAT-)
    # e uma area de regra sem vias, para o autorroteador nao furar o texto
    for ref in ("J1", "J4", "J5"):
        x0, y0, x1, _ = next(o for r_, o in occupied if r_ == ref)
        occupied.append(("rotulo-" + ref, (x0, y0 - LABEL_BAND, x1, y0)))
        ra = pcbnew.ZONE(board)
        ra.SetIsRuleArea(True)
        ra.SetDoNotAllowVias(True)
        ra.SetDoNotAllowTracks(False)
        ra.SetDoNotAllowPads(False)
        ra.SetDoNotAllowFootprints(False)
        ra.SetDoNotAllowZoneFills(False)
        ra.SetZoneName("rotulo " + ref)
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        ls.AddLayer(pcbnew.B_Cu)
        ra.SetLayerSet(ls)
        ol = ra.Outline()
        ol.NewOutline()
        for x, y in ((x0, y0 - LABEL_BAND), (x1, y0 - LABEL_BAND), (x1, y0), (x0, y0)):
            ol.Append(mm(OX + x), mm(OY + y))
        board.Add(ra)

    # posicionamento guloso
    report = []
    for ref, (aref, apad) in GREEDY:
        fp = fps[ref]
        ax, ay = pad_pos(fps[aref], apad)
        anet = pinnet.get((aref, apad))
        # caixas relativas por rotacao
        shapes = {}
        for rot in (0, 90, 180, 270):
            set_pose(fp, 0, 0, rot)
            bx = crt_box(fp)
            rel = (bx[0] - OX, bx[1] - OY, bx[2] - OX, bx[3] - OY)
            pads = [(p.GetNumber(), tomm(p.GetPosition().x) - OX, tomm(p.GetPosition().y) - OY,
                     p.GetNetname()) for p in fp.Pads()]
            shapes[rot] = (rel, pads)
        best = None
        cands = []
        step = 0.25
        n = int(16 / step)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                cands.append((i * i + j * j, ax + i * step, ay + j * step))
        cands.sort()
        found = 0
        for d2, cx, cy in cands:
            for rot, (rel, pads) in shapes.items():
                box = (rel[0] + cx, rel[1] + cy, rel[2] + cx, rel[3] + cy)
                if box[0] < EDGE or box[1] < EDGE or box[2] > W - EDGE or box[3] > H - EDGE:
                    continue
                if any(overlaps(box, o, MARGIN) for _, o in occupied):
                    continue
                # pontua pela distancia do pad que compartilha net com a ancora
                sc = None
                for num, px, py, net in pads:
                    if net == anet:
                        dd = math.hypot(px + cx - ax, py + cy - ay)
                        sc = dd if sc is None else min(sc, dd)
                if sc is None:
                    sc = math.sqrt(d2) * step
                if best is None or sc < best[0]:
                    best = (sc, cx, cy, rot, box)
                found += 1
            if found >= 60:
                break
        if best is None:
            raise SystemExit("sem lugar para " + ref)
        sc, cx, cy, rot, box = best
        set_pose(fp, round(cx, 3), round(cy, 3), rot)
        occupied.append((ref, box))
        report.append("%-4s perto de %s.%s  dist=%.2f mm  rot=%d" % (ref, aref, apad, sc, rot))

    # tudo posicionado?
    faltando = [r for r in fps if r not in FIXED and r not in dict(GREEDY)]
    if faltando:
        raise SystemExit("sem posicao definida: %s" % faltando)

    # serigrafia: referencia pequena, valor so na fab
    for fp in fps.values():
        t = fp.Reference()
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        t.SetTextThickness(mm(0.12))
        fp.Value().SetVisible(False)

    pcbnew.SaveBoard(pcb_path, board)
    write_project(work)
    # recarrega para aplicar regras do projeto
    board = pcbnew.LoadBoard(pcb_path)
    dsn = os.path.join(work, "altimetro.dsn")
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("falha exportando DSN")
    inject_classes(dsn, nets)
    with open(os.path.join(work, "place_report.txt"), "w") as f:
        f.write("\n".join(report) + "\n")
    print("place: %d footprints, placa %.1f x %.1f mm" % (len(fps), W, H))


def write_project(work):
    pro_path = os.path.join(work, "altimetro.kicad_pro")
    p = json.load(open(pro_path))
    ds = p["board"]["design_settings"]
    ds["rules"].update({
        "min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.5,
        "min_through_hole_diameter": 0.3, "min_via_annular_width": 0.1,
        "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
        "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.1,
    })
    ds["track_widths"] = [0.0, 0.25, 0.4, 0.8]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}]
    ns = p["net_settings"]
    base = ns["classes"][0]
    base.update(track_width=DEFAULT_TRACK, clearance=DEFAULT_CLEAR, via_diameter=0.6, via_drill=0.3)
    ns["classes"] = [base]
    pats = []
    for i, (name, c) in enumerate(CLASSES.items()):
        k = copy.deepcopy(base)
        k.update(name=name, track_width=c["track_width"], clearance=c["clearance"], priority=i)
        ns["classes"].append(k)
        pats += [{"netclass": name, "pattern": pt} for pt in c["patterns"]]
    ns["netclass_patterns"] = pats
    json.dump(p, open(pro_path, "w"), indent=2)


def class_of(net):
    import fnmatch
    for name, c in CLASSES.items():
        if any(fnmatch.fnmatchcase(net, pt) for pt in c["patterns"]):
            return name
    return None


def inject_classes(dsn, nets):
    """O exportador do pcbnew 10 nao resolve padroes de netclass; escrevemos as classes."""
    s = open(dsn).read()
    m = re.search(r'\(class kicad_default(.*?)\(circuit', s, re.S)
    if not m:
        raise SystemExit("classe kicad_default nao encontrada no DSN")
    toks = re.findall(r'"[^"]*"|[^\s()]+', m.group(1))
    names = [t.strip('"') for t in toks]
    keep, moved = [], {}
    for t, nme in zip(toks, names):
        k = class_of(nme)
        if k:
            moved.setdefault(k, []).append(t)
        else:
            keep.append(t)
    head = "(class kicad_default " + " ".join(keep) + "\n      (circuit"
    s = s[:m.start()] + head + s[m.end():]
    # largura/folga da classe default (o exportador ignora o .kicad_pro)
    i = s.index("(class kicad_default")
    j = s.index("(rule", i)
    k = s.index(")\n    )", j)
    s = s[:j] + "(rule\n        (width %d)\n        (clearance %d)\n      " % (
        round(DEFAULT_TRACK * 1000), round(DEFAULT_CLEAR * 1000)) + s[k:]
    blocks = []
    for k, lst in moved.items():
        c = CLASSES[k]
        blocks.append('    (class %s %s\n      (circuit\n        (use_via "Via[0-1]_600:300_um")\n'
                      '      )\n      (rule\n        (width %d)\n        (clearance %d)\n      )\n    )'
                      % (k, " ".join(lst), round(c["track_width"] * 1000), round(c["clearance"] * 1000)))
    i = s.index("(class kicad_default")
    s = s[:i] + "\n".join(blocks).lstrip() + "\n    " + s[i:]
    open(dsn, "w").write(s)


# ------------------------------------------------------------------ finish
def finish(projdir, work):
    pcb_path = os.path.join(work, "altimetro.kicad_pcb")
    board = pcbnew.LoadBoard(pcb_path)
    ses = os.path.join(work, "altimetro.ses")
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit("falha importando SES")

    gnd = board.FindNet("GND")
    for layer, prio in ((pcbnew.F_Cu, 0), (pcbnew.B_Cu, 1)):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.45))
        # SMD solido (refusao), alivio termico so nos passantes (bornes, header)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            ol.Append(mm(OX + x), mm(OY + y))
        board.Add(z)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    place_silk(board)
    n = stitch(board, gnd)
    filler.Fill(board.Zones())
    print("costura: %d vias de GND" % n)

    pcbnew.SaveBoard(pcb_path, board)
    print("finish: trilhas=%d vias=%d" % (
        sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"),
        sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")))


def stitch(board, gnd, pitch=2.54, via_d=0.6, drill=0.3, pad_gap=0.6):
    """Vias de GND ligando os planos de cima e de baixo onde ambos existem."""
    fills = [z.GetFilledPolysList(z.GetLayer()) for z in board.Zones() if not z.GetIsRuleArea()]
    proibidas = [z.Outline() for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    furos = [f for f in board.GetFootprints() if f.GetReference().startswith("H")]
    textos = [bbox_mm(d) for d in board.GetDrawings()
              if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
    textos += [bbox_mm(f.Reference()) for f in board.GetFootprints()
               if f.Reference().IsVisible() and f.Reference().GetLayer() == pcbnew.F_SilkS]
    r = via_d / 2 + 0.05
    n = 0
    y = pitch
    while y < H - pitch / 2:
        x = pitch
        while x < W - pitch / 2:
            px, py = OX + x, OY + y
            ok = True
            for k in range(13):
                if k == 12:
                    pt = pcbnew.VECTOR2I(mm(px), mm(py))
                else:
                    a = 2 * math.pi * k / 12
                    pt = pcbnew.VECTOR2I(mm(px + r * math.cos(a)), mm(py + r * math.sin(a)))
                if not all(f.Contains(pt) for f in fills) or any(o.Contains(pt) for o in proibidas):
                    ok = False
                    break
            if ok:
                c = pcbnew.VECTOR2I(mm(px), mm(py))
                for p in pads:
                    bb = p.GetBoundingBox()
                    bb.Inflate(mm(pad_gap + via_d / 2))
                    if bb.Contains(c):
                        ok = False
                        break
            if ok and any(t[0] - 0.5 < px < t[2] + 0.5 and t[1] - 0.5 < py < t[3] + 0.5 for t in textos):
                ok = False
            if ok:
                for f in furos:
                    if math.hypot(tomm(f.GetPosition().x) - px, tomm(f.GetPosition().y) - py) < 4.0:
                        ok = False
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(mm(px), mm(py)))
                v.SetWidth(mm(via_d))
                v.SetDrill(mm(drill))
                v.SetNet(gnd)
                board.Add(v)
                n += 1
            x += pitch
        y += pitch
    return n


def bbox_mm(item):
    bb = item.GetBoundingBox()
    return (tomm(bb.GetLeft()), tomm(bb.GetTop()), tomm(bb.GetRight()), tomm(bb.GetBottom()))


def place_silk(board):
    """Posiciona referencias e rotulos sem cobrir cobre exposto, outros textos ou o
    corpo de outra peca. O que nao couber fica oculto na serigrafia (continua no
    layer Fab, que vira o desenho de montagem)."""
    obst = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}      # (dono, caixa)
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for p in fp.Pads():
            for lay, cu in ((pcbnew.F_SilkS, pcbnew.F_Cu), (pcbnew.B_SilkS, pcbnew.B_Cu)):
                if p.IsOnLayer(cu):
                    obst[lay].append((None, bbox_mm(p)))
        for g in fp.GraphicalItems():
            if g.GetClass() == "PCB_SHAPE" and g.GetLayer() in obst:
                obst[g.GetLayer()].append((None, bbox_mm(g)))
        if not ref.startswith("H"):
            b = crt_box(fp)
            obst[pcbnew.F_SilkS].append((ref, b))
    # furo de via interrompe a serigrafia, mesmo com a via tampada
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            for lay in obst:
                obst[lay].append((None, bbox_mm(t)))
    x0, y0, x1, y1 = OX + 0.4, OY + 0.4, OX + W - 0.4, OY + H - 0.4

    def livre(box, lay, dono, m=0.12):
        if box[0] < x0 or box[1] < y0 or box[2] > x1 or box[3] > y1:
            return False
        return not any(overlaps(box, o, m) for d, o in obst[lay] if d is None or d != dono)

    def fixa(t, x, y, ang, dono):
        t.SetTextAngleDegrees(ang)
        t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        b = bbox_mm(t)
        if livre(b, t.GetLayer(), dono):
            obst[t.GetLayer()].append((None, b))
            return True
        return False

    def ao_redor(t, crt, dono, centro_ok):
        cx, cy = (crt[0] + crt[2]) / 2, (crt[1] + crt[3]) / 2
        if centro_ok and fixa(t, cx, cy, 0, dono):
            return True
        for ang in (0, 90):
            t.SetTextAngleDegrees(ang)
            t.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(cy)))
            b = bbox_mm(t)
            hw, hh = (b[2] - b[0]) / 2, (b[3] - b[1]) / 2
            # so posicoes ortogonais e coladas: em diagonal ou afastada a referencia
            # parece pertencer a peca vizinha
            g = 0.2
            for x, y in ((cx, crt[1] - hh - g), (cx, crt[3] + hh + g),
                         (crt[0] - hw - g, cy), (crt[2] + hw + g, cy)):
                if fixa(t, x, y, ang, dono):
                    return True
        return False

    def espiral(t, x, y):
        for r in range(0, 70):                      # ate 35 mm, passo 0,5 mm
            for k in range(max(1, 6 * r)):
                a = 2 * math.pi * k / max(1, 6 * r)
                if fixa(t, x + 0.5 * r * math.cos(a), y + 0.5 * r * math.sin(a), 0, None):
                    return True
        return False

    def novo_texto(txt, size, lay):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetLayer(lay)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(0.15))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        if lay == pcbnew.B_SilkS:
            t.SetMirrored(True)
        board.Add(t)
        return t

    ocultas = []
    # rotulos dos bornes: completos no verso (atras do borne) e, se couber, curtos no topo
    for ref, longo, curto in (("J1", "+BAT-", "+BAT-"), ("J4", "APOGEU", "APO"), ("J5", "PRINC", "PRI")):
        fp = board.FindFootprintByReference(ref)
        crt = crt_box(fp)
        t = novo_texto(curto, 0.8, pcbnew.F_SilkS)
        t.SetPosition(pcbnew.VECTOR2I(mm((crt[0] + crt[2]) / 2), mm(crt[1])))
        hh = (lambda b: (b[3] - b[1]) / 2)(bbox_mm(t))
        # so centralizado acima do proprio borne; em outro lugar o rotulo engana quem liga os fios
        if not fixa(t, (crt[0] + crt[2]) / 2, crt[1] - hh - 0.2, 0, ref):
            raise SystemExit("faixa do rotulo de %s ocupada" % ref)
        t = novo_texto(longo, 0.9, pcbnew.B_SilkS)
        if not espiral(t, (crt[0] + crt[2]) / 2, crt[1] + 1.0):
            raise SystemExit("sem lugar para o rotulo " + longo)

    grandes = {"U2", "U4", "LS1", "C1"}      # referencia dentro do corpo, sem cobre embaixo
    area = lambda f: (lambda b: (b[2] - b[0]) * (b[3] - b[1]))(crt_box(f))
    for fp in sorted(board.GetFootprints(), key=lambda f: -area(f)):
        ref = fp.GetReference()
        t = fp.Reference()
        if ref.startswith("H") or ref in ("J1", "J4", "J5"):    # bornes ja tem rotulo funcional
            t.SetVisible(False)
            continue
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        t.SetTextThickness(mm(0.15))
        t.SetVisible(True)
        if not ao_redor(t, crt_box(fp), ref, ref in grandes):
            t.SetVisible(False)
            ocultas.append(ref)

    for txt, size, (x, y) in (("ALTIMETRO 2 EVENTOS rev A", 1.0, (W / 2, 3.0)),
                              ("SWD 1:3V3 2:SWDIO 3:SWCLK 4:NRST 5:GND", 0.8, (W / 2, 8.0)),
                              ("BAT 4-16 V", 0.9, (10.0, 16.0))):
        t = novo_texto(txt, size, pcbnew.B_SilkS)
        if not espiral(t, OX + x, OY + y):
            raise SystemExit("sem lugar no verso para " + txt)
    print("serigrafia: %d referencias so no desenho de montagem: %s" % (len(ocultas), " ".join(ocultas)))


def add_text(board, txt, x, y, size, layer=pcbnew.F_SilkS, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(max(0.12, size * 0.15)))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


def merge_pro(projdir, work):
    """Leva regras/netclasses da placa para o .kicad_pro do projeto, preservando as folhas."""
    novo = json.load(open(os.path.join(work, "altimetro.kicad_pro")))
    velho_path = os.path.join(projdir, "altimetro.kicad_pro")
    velho = json.load(open(velho_path))
    novo["sheets"] = velho["sheets"]
    novo["meta"]["filename"] = "altimetro.kicad_pro"
    json.dump(novo, open(velho_path, "w"), indent=2)


if __name__ == "__main__":
    cmd, projdir, work = sys.argv[1], sys.argv[2], sys.argv[3]
    {"place": place, "finish": finish, "merge-pro": merge_pro}[cmd](projdir, work)
