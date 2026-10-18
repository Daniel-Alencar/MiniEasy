#!/usr/bin/env python3
"""Gera o esquematico KiCad do altimetro (clone funcional do EasyMini).

Uso: python3 -I gen_sch.py <dir-dos-simbolos-do-kicad> <saida.kicad_sch>

Simbolos sao achatados e embutidos em (lib_symbols), de modo que o arquivo abre
sem precisar das bibliotecas instaladas. Conexoes sao feitas por rotulos (labels)
em stubs de 2.54 mm: a netlist gerada e exatamente a tabela NETS abaixo.
"""
import sys, os, uuid, hashlib, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import load, find_symbol, unq

NS = uuid.UUID("6f1a9c2e-5b3d-4c1a-9e7f-2d8b4a6c0e11")


def uid(key):
    return str(uuid.uuid5(NS, key))


# ---------------------------------------------------------------- componentes
# (ref, lib, simbolo, valor, footprint, x, y, rot)
CW, CH = 30.48, 30.48


def cell(ox, oy, c, r, cw=CW, ch=CH):
    return (ox + c * cw, oy + r * ch)


COMPS = []


def add(ref, lib, sym, val, fp, pos, rot=0, desc=None):
    COMPS.append(dict(ref=ref, lib=lib, sym=sym, val=val, fp=fp,
                      x=round(pos[0], 2), y=round(pos[1], 2), rot=rot, desc=desc))


R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOD123 = "Diode_SMD:D_SOD-123"
TBLOCK = "TerminalBlock_MetzConnect:TerminalBlock_MetzConnect_Type059_RT06302HBWC_1x02_P3.50mm_Horizontal"

# ---- B1: alimentacao e protecao -------------------------------------------
B1 = (40.64, 45.72)
add("J1", "Connector", "Screw_Terminal_01x02", "BAT 4-16 V", TBLOCK, cell(*B1, 0, 0))
add("D1", "Device", "D_Schottky", "B5819W", SOD123, cell(*B1, 1, 0))
add("D2", "Device", "D_Schottky", "B5819W", SOD123, cell(*B1, 2, 0))
add("U1", "Regulator_Linear", "MCP1703Ax-330xxMB", "MCP1703A-3302E/MB",
    "Package_TO_SOT_SMD:SOT-89-3", cell(*B1, 3, 0))
add("C1", "Device", "C_Polarized", "100u/25V", "Capacitor_SMD:CP_Elec_6.3x7.7", cell(*B1, 0, 1))
add("C2", "Device", "C", "10u/25V", C0805, cell(*B1, 1, 1))
add("C3", "Device", "C", "10u", C0805, cell(*B1, 2, 1))
add("C4", "Device", "C", "100n", C0603, cell(*B1, 3, 1))
add("C5", "Device", "C", "100n", C0603, cell(*B1, 4, 1))
add("R1", "Device", "R", "100k", R0603, cell(*B1, 0, 2))
add("R2", "Device", "R", "10k", R0603, cell(*B1, 1, 2))
add("#FLG1", "power", "PWR_FLAG", "PWR_FLAG", "", cell(*B1, 2, 2))
add("#FLG2", "power", "PWR_FLAG", "PWR_FLAG", "", cell(*B1, 3, 2))

# ---- B2: MCU ---------------------------------------------------------------
B2 = (200.66, 45.72)
add("C6", "Device", "C", "100n", C0603, cell(*B2, 0, 0))
add("C7", "Device", "C", "100n", C0603, cell(*B2, 1, 0))
add("C8", "Device", "C", "1u", C0603, cell(*B2, 0, 1))
add("C9", "Device", "C", "100n", C0603, cell(*B2, 1, 1))
add("C10", "Device", "C", "1u", C0603, cell(*B2, 0, 2))
add("C11", "Device", "C", "100n", C0603, cell(*B2, 1, 2))
add("R3", "Device", "R", "10k", R0603, cell(*B2, 0, 3))
add("JP1", "Jumper", "SolderJumper_2_Open", "BOOT0",
    "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", cell(*B2, 1, 3))
add("J2", "Connector_Generic", "Conn_01x05", "SWD",
    "Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical", (200.66, 167.64))
add("U2", "MCU_ST_STM32F0", "STM32F042K6Tx", "STM32F042K6T6",
    "Package_QFP:LQFP-32_7x7mm_P0.8mm", (276.86, 95.25))

# ---- B3: barometro + flash -------------------------------------------------
add("U3", "Sensor_Pressure", "MS5607-02BA", "MS5607-02BA03",
    "Package_LGA:LGA-8_3x5mm_P1.25mm", (400.05, 48.26))
add("C12", "Device", "C", "100n", C0603, (438.15, 48.26))
add("U4", "Memory_Flash", "W25Q16JVSS", "W25Q16JVSSIQ",
    "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", (480.06, 48.26))
add("R4", "Device", "R", "10k", R0603, (520.7, 48.26))
add("R5", "Device", "R", "10k", R0603, (551.18, 48.26))
add("C13", "Device", "C", "100n", C0603, (480.06, 110.49))

# ---- B4: USB ---------------------------------------------------------------
add("J3", "Connector", "USB_B_Micro", "USB micro-B",
    "Connector_USB:USB_Micro-B_Molex_47346-0001", (400.05, 190.5))
add("U5", "Power_Protection", "USBLC6-2SC6", "USBLC6-2SC6",
    "Package_TO_SOT_SMD:SOT-23-6", (459.74, 190.5))
add("C14", "Device", "C", "1u", C0603, (505.46, 190.5))
add("C15", "Device", "C", "100n", C0603, (530.86, 190.5))
add("R6", "Device", "R", "100k", R0603, (505.46, 240.03))
add("R7", "Device", "R", "100k", R0603, (530.86, 240.03))

# ---- B5/B6: canais pirotecnicos --------------------------------------------
for idx, (B, j, q, rs, cs) in enumerate([
        ((40.64, 167.64), "J4", "Q1", ("R8", "R9", "R10", "R11"), "C16"),
        ((40.64, 256.54), "J5", "Q2", ("R12", "R13", "R14", "R15"), "C17")]):
    nome = "APOGEU" if idx == 0 else "PRINCIPAL"
    add(j, "Connector", "Screw_Terminal_01x02", "PIRO %s" % nome, TBLOCK, cell(*B, 0, 0))
    add(q, "Transistor_FET", "AO3400A", "AO3400A", SOT23, cell(*B, 1, 0))
    add(rs[0], "Device", "R", "100R", R0603, cell(*B, 2, 0))
    add(rs[1], "Device", "R", "100k", R0603, cell(*B, 3, 0))
    add(cs, "Device", "C", "10n", C0603, cell(*B, 4, 0))
    add(rs[2], "Device", "R", "100k", R0603, cell(*B, 2, 1))
    add(rs[3], "Device", "R", "10k", R0603, cell(*B, 3, 1))

# ---- B7: aviso sonoro + LED ------------------------------------------------
B7 = (40.64, 345.44)
add("LS1", "Device", "Buzzer", "CMT-8504-100-SMT",
    "Buzzer_Beeper:MagneticBuzzer_CUI_CMT-8504-100-SMT", cell(*B7, 0, 0))
add("Q3", "Transistor_FET", "BSS138", "BSS138", SOT23, cell(*B7, 1, 0))
add("R16", "Device", "R", "100R", R0603, cell(*B7, 2, 0))
add("R17", "Device", "R", "100k", R0603, cell(*B7, 3, 0))
add("D3", "Device", "D_Schottky", "B5819W", SOD123, cell(*B7, 4, 0))
add("R18", "Device", "R", "1k", R0603, cell(*B7, 5, 0))
add("D4", "Device", "LED", "LED verde", "LED_SMD:LED_0603_1608Metric", cell(*B7, 6, 0))

# ---------------------------------------------------------------------- nets
NETS = {
    "GND": [("J1", "2"), ("C1", "2"), ("C2", "2"), ("U1", "1"), ("C3", "2"), ("C4", "2"),
            ("C5", "2"), ("R2", "2"), ("U2", "16"), ("U2", "32"), ("C6", "2"), ("C7", "2"),
            ("C8", "2"), ("C9", "2"), ("C10", "2"), ("C11", "2"), ("R3", "2"), ("J2", "5"),
            ("U3", "2"), ("U3", "3"), ("C12", "2"), ("U4", "4"), ("C13", "2"),
            ("J3", "5"), ("J3", "SH"), ("U5", "2"), ("C14", "2"), ("C15", "2"), ("R7", "2"),
            ("Q1", "2"), ("R9", "2"), ("R11", "2"), ("C16", "2"),
            ("Q2", "2"), ("R13", "2"), ("R15", "2"), ("C17", "2"),
            ("Q3", "2"), ("R17", "2")],
    "+3V3": [("U1", "3"), ("C3", "1"), ("C4", "1"), ("U2", "1"), ("U2", "5"), ("U2", "17"),
             ("C6", "1"), ("C7", "1"), ("C8", "1"), ("C9", "1"), ("C10", "1"), ("J2", "1"),
             ("JP1", "1"), ("U3", "1"), ("C12", "1"), ("U4", "8"), ("C13", "1"),
             ("R4", "1"), ("R5", "1"), ("LS1", "1"), ("D3", "1"), ("R18", "1")],
    "VBAT": [("J1", "1"), ("D1", "2"), ("C1", "1"), ("R1", "1"), ("J4", "1"), ("J5", "1"),
             ("#FLG1", "1")],
    "VSYS": [("D1", "1"), ("D2", "1"), ("C2", "1"), ("U1", "2"), ("#FLG2", "1")],
    "VBUS": [("J3", "1"), ("D2", "2"), ("U5", "5"), ("C14", "1"), ("C15", "1"), ("R6", "1")],
    "VB_SNS": [("R1", "2"), ("R2", "1"), ("C5", "1"), ("U2", "8")],
    "NRST": [("U2", "4"), ("C11", "1"), ("J2", "4")],
    "BOOT0": [("U2", "31"), ("R3", "1"), ("JP1", "2")],
    "SWDIO": [("U2", "23"), ("J2", "2")],
    "SWCLK": [("U2", "24"), ("J2", "3")],
    "SCK": [("U2", "11"), ("U3", "8"), ("U4", "6")],
    "MISO": [("U2", "12"), ("U3", "6"), ("U4", "2")],
    "MOSI": [("U2", "13"), ("U3", "7"), ("U4", "5")],
    "CS_BARO": [("U2", "10"), ("U3", "4")],
    "CS_FLSH": [("U2", "9"), ("U4", "1")],
    "WPn": [("U4", "3"), ("R4", "2")],
    "HOLDn": [("U4", "7"), ("R5", "2")],
    "USB_DM": [("U2", "21"), ("U5", "4")],
    "USB_DP": [("U2", "22"), ("U5", "6")],
    "DM_CON": [("J3", "2"), ("U5", "3")],
    "DP_CON": [("J3", "3"), ("U5", "1")],
    "VU_SNS": [("R6", "2"), ("R7", "1"), ("U2", "14")],
    "FIRE_A": [("U2", "18"), ("R8", "1")],
    "GATE_A": [("R8", "2"), ("R9", "1"), ("Q1", "1")],
    "PYRO_A": [("J4", "2"), ("Q1", "3"), ("R10", "1")],
    "SNS_A": [("R10", "2"), ("R11", "1"), ("C16", "1"), ("U2", "6")],
    "FIRE_B": [("U2", "19"), ("R12", "1")],
    "GATE_B": [("R12", "2"), ("R13", "1"), ("Q2", "1")],
    "PYRO_B": [("J5", "2"), ("Q2", "3"), ("R14", "1")],
    "SNS_B": [("R14", "2"), ("R15", "1"), ("C17", "1"), ("U2", "7")],
    "BEEP": [("U2", "15"), ("R16", "1")],
    "GATE_BZ": [("R16", "2"), ("R17", "1"), ("Q3", "1")],
    "BUZZ": [("LS1", "2"), ("Q3", "3"), ("D3", "2")],
    "LED_A": [("R18", "2"), ("D4", "2")],
    "STAT": [("U2", "25"), ("D4", "1")],
}

NC = [("U2", "2"), ("U2", "3"), ("U2", "20"), ("U2", "26"), ("U2", "27"),
      ("U2", "28"), ("U2", "29"), ("U2", "30"), ("J3", "4")]

POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3"}

CAPTIONS = [
    (40.0, 30.0, "1. ALIMENTACAO E PROTECAO"),
    (200.0, 30.0, "2. MICROCONTROLADOR"),
    (380.0, 30.0, "3. BAROMETRO E MEMORIA DE VOO"),
    (380.0, 165.0, "4. USB (DOWNLOAD / DFU)"),
    (40.0, 152.0, "5. CANAL PIROTECNICO A - APOGEU"),
    (40.0, 241.0, "6. CANAL PIROTECNICO B - PRINCIPAL"),
    (40.0, 330.0, "7. AVISO SONORO E LED DE ESTADO"),
]

NOTES = [
    (380.0, 300.0, 1.5,
     "NOTAS DE PROJETO"),
    (380.0, 306.0, 1.27,
     "1. Q1/Q2 ficam desligados sem firmware: R9/R13 (100k) mantem o gate em GND."),
    (380.0, 311.0, 1.27,
     "2. Continuidade: R10/R11 e R14/R15 formam divisor 100k/10k no dreno. Com igniter"),
    (380.0, 316.0, 1.27,
     "   intacto a corrente de teste e VBAT/110k (<0,15 mA em 16 V), muito abaixo do no-fire."),
    (380.0, 321.0, 1.27,
     "3. Corrente de disparo vem de VBAT direto (J4/J5 pino 1); C1 (100u) sustenta a tensao."),
    (380.0, 326.0, 1.27,
     "4. D1/D2 fazem OR de fontes: bateria OU USB alimentam o 3V3. Com USB sozinho os"),
    (380.0, 331.0, 1.27,
     "   canais pirotecnicos ficam sem energia - bancada segura."),
    (380.0, 336.0, 1.27,
     "5. USB sem cristal: HSI48 + CRS sincronizado ao SOF. PF0/PF1 nao sao usados."),
    (380.0, 341.0, 1.27,
     "6. JP1 fechado = BOOT0 em 3V3 = bootloader DFU por USB (regravacao sem SWD)."),
    (380.0, 346.0, 1.27,
     "7. SPI1 compartilhado: U3 (MS5607, modo SPI com PS em GND) e U4 (flash 16 Mbit)."),
    (380.0, 351.0, 1.27,
     "8. LDO em SOT-89: com VBAT=16 V e 25 mA dissipa 0,32 W (SOT-23 esquentaria demais)."),
]


# ------------------------------------------------------------ libs/simbolos
def collect_symbol(libdir, lib, name):
    """Retorna (props_do_simbolo, attrs_da_base, subsimbolos_da_base)."""
    path = os.path.join(libdir, lib + ".kicad_sym")
    doc = load(path)
    sym = find_symbol(doc, name)
    if sym is None:
        raise SystemExit("simbolo nao encontrado: %s:%s" % (lib, name))
    base = sym
    seen = set()
    while True:
        ext = None
        for q in base:
            if isinstance(q, list) and q[0] == "extends":
                ext = unq(q[1])
        if ext is None or ext in seen:
            break
        seen.add(ext)
        base = find_symbol(doc, ext)
    return sym, base


def pins_of(base):
    out = []
    for sub in base:
        if isinstance(sub, list) and sub[0] == "symbol":
            for p in sub:
                if isinstance(p, list) and p[0] == "pin":
                    hidden = "hide" in p or any(isinstance(q, list) and q[:2] == ["hide", "yes"]
                                                for q in p)
                    num = nm = None
                    at = None
                    for q in p:
                        if isinstance(q, list):
                            if q[0] == "number":
                                num = unq(q[1])
                            elif q[0] == "name":
                                nm = unq(q[1])
                            elif q[0] == "at":
                                at = (float(q[1]), float(q[2]), float(q[3]) if len(q) > 3 else 0.0)
                    out.append(dict(num=num, name=nm, at=at, hide=hidden))
    return out


def dump(node, indent):
    sp = "\t" * indent
    if isinstance(node, str):
        return sp + node
    head = node[0] if node and isinstance(node[0], str) else ""
    if all(isinstance(x, str) for x in node):
        return sp + "(" + " ".join(node) + ")"
    lines = [sp + "(" + head]
    for x in node[1:]:
        if isinstance(x, str):
            lines[-1] += " " + x
        else:
            lines.append(dump(x, indent + 1))
    lines.append(sp + ")")
    return "\n".join(lines)


def rename_sub(node, old, new):
    if isinstance(node, list) and node and node[0] == "symbol" and len(node) > 1 \
            and isinstance(node[1], str) and node[1].startswith('"'):
        inner = unq(node[1])
        if inner.startswith(old + "_"):
            node = [node[0], '"' + new + inner[len(old):] + '"'] + node[2:]
    return node


def build_lib_symbol(libdir, lib, name, indent=2):
    sym, base = collect_symbol(libdir, lib, name)
    out = ['\t' * indent + '(symbol "%s:%s"' % (lib, name)]
    # atributos vindos da base (geometria/flags)
    for q in base:
        if isinstance(q, str) and q in ("power",):
            out.append('\t' * (indent + 1) + "(power)")
        elif isinstance(q, list) and q[0] in ("pin_numbers", "pin_names", "exclude_from_sim",
                                              "in_bom", "on_board"):
            out.append(dump(q, indent + 1))
        elif isinstance(q, list) and q[0] == "power":
            out.append(dump(q, indent + 1))
    # propriedades vindas do simbolo concreto
    for q in sym:
        if isinstance(q, list) and q[0] == "property":
            out.append(dump(q, indent + 1))
    # graficos/pinos vindos da base
    for q in base:
        if isinstance(q, list) and q[0] == "symbol":
            out.append(dump(rename_sub(q, unq(base[1]), name), indent + 1))
    out.append('\t' * indent + ")")
    return "\n".join(out)


# -------------------------------------------------------------- geometria
def rot_offset(dx, dy, rot):
    """Rotaciona um offset em coordenadas de folha (y para baixo), CCW na tela."""
    r = int(rot) % 360
    if r == 0:
        return dx, dy
    if r == 90:
        return dy, -dx
    if r == 180:
        return -dx, -dy
    if r == 270:
        return -dy, dx
    raise SystemExit("rotacao nao suportada: %s" % rot)


def pin_geom(comp, pin):
    """Posicao na folha do ponto de conexao e direcao do stub (para fora do corpo)."""
    px, py, pa = pin["at"]
    ox, oy = rot_offset(px, -py, comp["rot"])
    x, y = comp["x"] + ox, comp["y"] + oy
    # direcao "para o corpo" em coords de folha, antes da rotacao
    import math
    bx = math.cos(math.radians(pa))
    by = -math.sin(math.radians(pa))
    bx, by = rot_offset(bx, by, comp["rot"])
    sx, sy = -bx, -by          # stub aponta para fora
    return round(x, 2), round(y, 2), round(sx, 4), round(sy, 4)


def label_angle(sx, sy):
    if abs(sx) > 0.5:
        return (0, "left") if sx > 0 else (180, "right")
    return (90, "left") if sy < 0 else (270, "right")


# ------------------------------------------------------------------ escrita
def main():
    libdir, outpath = sys.argv[1], sys.argv[2]

    by_ref = {c["ref"]: c for c in COMPS}
    if len(by_ref) != len(COMPS):
        raise SystemExit("referencia duplicada")

    # geometria de cada simbolo usado
    geom = {}
    keys = [(c["lib"], c["sym"]) for c in COMPS]
    keys += [tuple(pw.split(":")) for pw in POWER_NETS.values()]
    for key in keys:
        if key not in geom:
            sym, base = collect_symbol(libdir, key[0], key[1])
            geom[key] = pins_of(base)
            LIBPROPS[key] = lib_props(sym)
            IN_BOM[key] = not any(isinstance(q, list) and q[:2] == ["in_bom", "no"]
                                  for q in list(sym) + list(base))

    # mapa pino -> net; valida cobertura total
    pinnet = {}
    for net, conns in NETS.items():
        for ref, num in conns:
            if ref not in by_ref:
                raise SystemExit("net %s cita ref inexistente %s" % (net, ref))
            if (ref, num) in pinnet:
                raise SystemExit("pino %s.%s em duas nets: %s e %s"
                                 % (ref, num, pinnet[(ref, num)], net))
            pinnet[(ref, num)] = net
    for ref, num in NC:
        if (ref, num) in pinnet:
            raise SystemExit("pino %s.%s marcado NC mas esta na net %s" % (ref, num, pinnet[(ref, num)]))
        pinnet[(ref, num)] = None

    faltando = []
    for c in COMPS:
        for p in geom[(c["lib"], c["sym"])]:
            if p["hide"]:
                continue
            if (c["ref"], p["num"]) not in pinnet:
                faltando.append("%s.%s (%s)" % (c["ref"], p["num"], p["name"]))
    if faltando:
        raise SystemExit("pinos sem net nem NC:\n  " + "\n  ".join(faltando))

    sobrando = [k for k in pinnet
                if not any(p["num"] == k[1] for p in geom[(by_ref[k[0]]["lib"], by_ref[k[0]]["sym"])])]
    if sobrando:
        raise SystemExit("nets citam pinos inexistentes: %s" % sobrando)

    body = []
    E = body.append

    # lib_symbols
    used = []
    for c in COMPS:
        k = (c["lib"], c["sym"])
        if k not in used:
            used.append(k)
    for net, pw in POWER_NETS.items():
        k = tuple(pw.split(":"))
        if k not in used:
            used.append(k)
    E("\t(lib_symbols")
    for lib, name in used:
        E(build_lib_symbol(libdir, lib, name))
    E("\t)")

    # texto de bloco
    for x, y, t in CAPTIONS:
        E('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n'
          '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 2.5 2.5)\n\t\t\t\t(bold yes)\n\t\t\t)\n'
          '\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)'
          % (t, x, y, uid("cap" + t)))
    for x, y, sz, t in NOTES:
        E('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n'
          '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %s %s)\n\t\t\t)\n'
          '\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)'
          % (t, x, y, sz, sz, uid("note" + t)))

    # fios, rotulos, simbolos de alimentacao, no-connects
    npower = 0
    pwr_list = []
    seg_owner = {}
    pwr_pts = {}
    for c in COMPS:
        for p in geom[(c["lib"], c["sym"])]:
            if p["hide"]:
                continue
            net = pinnet[(c["ref"], p["num"])]
            x, y, sx, sy = pin_geom(c, p)
            tag = "%s.%s" % (c["ref"], p["num"])
            if net is None:
                E('\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)' % (x, y, uid("nc" + tag)))
                continue
            pts = [(x, y), (round(x + sx * 2.54, 2), round(y + sy * 2.54, 2))]
            if net in POWER_NETS:
                lib, name = POWER_NETS[net].split(":")
                pp = geom[(lib, name)][0]
                import math
                pa = pp["at"][2]
                if abs(pa % 180.0 - 90.0) > 1e-6:
                    raise SystemExit("simbolo %s tem pino em angulo inesperado: %s" % (name, pa))
                # direcao em que o corpo do simbolo cresce (rot 0)
                bdy = round(-math.sin(math.radians(pa)), 4)
                px1, py1 = pts[-1]
                if abs(sx) < 0.5 and abs(sy - bdy) < 1e-6:
                    pass                       # stub ja aponta na direcao certa
                elif abs(sx) > 0.5:
                    # avanca na horizontal para alem dos rotulos vizinhos antes de virar,
                    # senao o simbolo de GND/3V3 cai sobre o texto do pino de baixo
                    pts.append((round(px1 + sx * 10.16, 2), round(py1, 2)))
                    pts.append((round(px1 + sx * 10.16, 2), round(py1 + bdy * 2.54, 2)))
                else:                          # stub aponta ao contrario: desvia 2.54 para a direita
                    pts.append((round(px1 + 2.54, 2), round(py1, 2)))
                    pts.append((round(px1 + 2.54, 2), round(py1 + bdy * 5.08, 2)))
                pf = pts[-1]
                if pf in pwr_pts:
                    raise SystemExit("dois simbolos de alimentacao no mesmo ponto: %s e %s"
                                     % (pwr_pts[pf], tag))
                pwr_pts[pf] = tag
                ox, oy = pp["at"][0], -pp["at"][1]
                npower += 1
                pwr_list.append((dict(ref="#PWR%02d" % npower, lib=lib, sym=name, val=net,
                                      fp="", x=round(pf[0] - ox, 2), y=round(pf[1] - oy, 2),
                                      rot=0, desc=None), uid("pw" + tag)))
            else:
                ang, just = label_angle(sx, sy)
                ex, ey = pts[-1]
                E('\t(label "%s"\n\t\t(at %s %s %s)\n\t\t(fields_autoplaced yes)\n'
                  '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
                  '\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)'
                  % (net, ex, ey, ang, just, uid("lb" + tag)))
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                key = tuple(sorted([a, b]))
                if key in seg_owner:
                    raise SystemExit("segmento duplicado %s: %s e %s" % (key, seg_owner[key], tag))
                seg_owner[key] = tag
                E('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n'
                  '\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
                  '\t\t(uuid "%s")\n\t)'
                  % (a[0], a[1], b[0], b[1], uid("w%s_%d" % (tag, i))))

    # valor visivel so no primeiro de cada grupo de simbolos iguais vizinhos
    # (ex.: VDD/VDDA/VDDIO2 do U2 a 2,54 mm um do outro)
    visiveis = []
    for c, u in sorted(pwr_list, key=lambda t: (t[0]["y"], t[0]["x"])):
        perto = any(v["val"] == c["val"] and abs(v["x"] - c["x"]) < 7.7 and abs(v["y"] - c["y"]) < 5.1
                    for v in visiveis)
        if not perto:
            visiveis.append(c)
        E(sym_instance(c, u, hide_ref=True, hide_value=perto))

    # simbolos
    for c in COMPS:
        E(sym_instance(c, uid("sym" + c["ref"]), hide_ref=c["ref"].startswith("#")))

    hdr = ['(kicad_sch',
           '\t(version 20231120)',
           '\t(generator "manual")',
           '\t(generator_version "8.0")',
           '\t(uuid "%s")' % uid("sheet"),
           '\t(paper "A2")',
           '\t(title_block',
           '\t\t(title "Altimetro de dois eventos - classe EasyMini")',
           '\t\t(date "%s")' % datetime.date.today().isoformat(),
           '\t\t(rev "A")',
           '\t\t(comment 1 "STM32F042K6 + MS5607 + flash 16 Mbit + 2 canais pirotecnicos")',
           '\t\t(comment 2 "Conexoes por rotulo: cada pino tem um stub com o nome da net")',
           '\t)']
    ftr = ['\t(sheet_instances',
           '\t\t(path "/"',
           '\t\t\t(page "1")',
           '\t\t)',
           '\t)',
           ')']
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("\n".join(hdr + body + ftr) + "\n")

    print("ok: %d componentes, %d nets, %d pinos NC, %d simbolos de alimentacao"
          % (len(COMPS), len(NETS), len(NC), npower))
    return 0


LIBPROPS = {}   # (lib, simbolo) -> {campo: (x, y, angulo, effects)}
IN_BOM = {}     # (lib, simbolo) -> False quando a biblioteca marca (in_bom no), ex. jumper de solda


def lib_props(sym):
    out = {}
    for q in sym:
        if isinstance(q, list) and q[0] == "property":
            at = eff = None
            for r in q:
                if isinstance(r, list) and r[0] == "at":
                    at = (float(r[1]), float(r[2]), r[3] if len(r) > 3 else "0")
                elif isinstance(r, list) and r[0] == "effects":
                    eff = r
            out[unq(q[1])] = (at, eff)
    return out


def effects_with(eff, hide):
    """Copia (effects ...) da biblioteca trocando apenas o estado de visibilidade."""
    if eff is None:
        eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
    body = [x for x in eff[1:] if x != "hide" and not (isinstance(x, list) and x[0] == "hide")]
    if hide:
        body.append(["hide", "yes"])
    return dump(["effects"] + body, 3)


def sym_instance(c, u, hide_ref=False, hide_value=False):
    lp = LIBPROPS[(c["lib"], c["sym"])]
    props = [
        ("Reference", c["ref"], hide_ref),
        ("Value", c["val"], hide_value),
        ("Footprint", c["fp"], True),
        ("Datasheet", "~", True),
        ("Description", c["desc"] or "", True),
    ]
    out = ['\t(symbol',
           '\t\t(lib_id "%s:%s")' % (c["lib"], c["sym"]),
           '\t\t(at %s %s %s)' % (c["x"], c["y"], c["rot"]),
           '\t\t(unit 1)',
           '\t\t(exclude_from_sim no)',
           '\t\t(in_bom %s)' % ("no" if c["ref"].startswith("#")
                                  or not IN_BOM.get((c["lib"], c["sym"]), True) else "yes"),
           '\t\t(on_board %s)' % ("no" if c["ref"].startswith("#") else "yes"),
           '\t\t(dnp no)',
           '\t\t(uuid "%s")' % u]
    for nm, val, hide in props:
        at, eff = lp.get(nm, ((0.0, 0.0, "0"), None))
        if c["rot"] != 0:
            raise SystemExit("campos so sao posicionados para rotacao 0")
        x, y = round(c["x"] + at[0], 2), round(c["y"] - at[1], 2)
        out.append('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %s)\n%s\n\t\t)'
                   % (nm, val, x, y, at[2], effects_with(eff, hide)))
    out.append('\t\t(instances\n\t\t\t(project "altimetro"\n\t\t\t\t(path "/%s"\n'
               '\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)'
               % (uid("sheet"), c["ref"]))
    out.append('\t)')
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
