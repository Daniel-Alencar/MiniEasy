#!/usr/bin/env python3
"""Reextrai a netlist da GEOMETRIA do .kicad_sch gerado e compara com a tabela NETS.

Uso: python3 -I check_sch.py <arquivo.kicad_sch>
"""
import sys, os, math, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import load, unq
import gen_sch


def prop(node, name):
    for q in node:
        if isinstance(q, list) and q[0] == "property" and unq(q[1]) == name:
            return unq(q[2])
    return None


def main():
    doc = load(sys.argv[1])

    libpins = {}
    symbols = []
    wires = []
    labels = []
    ncs = []

    for n in doc:
        if not isinstance(n, list):
            continue
        if n[0] == "lib_symbols":
            for s in n[1:]:
                name = unq(s[1])
                pins = []
                for sub in s:
                    if isinstance(sub, list) and sub[0] == "symbol":
                        for p in sub:
                            if isinstance(p, list) and p[0] == "pin":
                                num = at = None
                                hide = "hide" in p
                                for q in p:
                                    if isinstance(q, list) and q[0] == "number":
                                        num = unq(q[1])
                                    elif isinstance(q, list) and q[0] == "at":
                                        at = (float(q[1]), float(q[2]), float(q[3]))
                                pins.append((num, at, hide))
                libpins[name] = pins
        elif n[0] == "symbol":
            libid = None
            at = None
            for q in n:
                if isinstance(q, list) and q[0] == "lib_id":
                    libid = unq(q[1])
                elif isinstance(q, list) and q[0] == "at":
                    at = (float(q[1]), float(q[2]), float(q[3]))
            symbols.append(dict(libid=libid, at=at, ref=prop(n, "Reference"),
                                val=prop(n, "Value")))
        elif n[0] == "wire":
            for q in n:
                if isinstance(q, list) and q[0] == "pts":
                    pts = [(float(x[1]), float(x[2])) for x in q[1:]]
                    wires.append((rnd(pts[0]), rnd(pts[1])))
        elif n[0] == "label":
            for q in n:
                if isinstance(q, list) and q[0] == "at":
                    labels.append((unq(n[1]), rnd((float(q[1]), float(q[2])))))
        elif n[0] == "no_connect":
            for q in n:
                if isinstance(q, list) and q[0] == "at":
                    ncs.append(rnd((float(q[1]), float(q[2]))))

    # ---- union-find sobre pontos
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in wires:
        union(a, b)

    # ---- pinos de cada instancia
    pinpos = {}        # (ref, num) -> ponto
    pwr_at = []        # (nome_da_net, ponto)
    for s in symbols:
        if s["libid"] not in libpins:
            sys.exit("lib_id ausente em lib_symbols: %s" % s["libid"])
        if s["at"][2] != 0:
            sys.exit("instancia %s nao esta em rotacao 0" % s["ref"])
        for num, at, hide in libpins[s["libid"]]:
            if hide:
                continue
            pt = rnd((s["at"][0] + at[0], s["at"][1] - at[1]))
            find(pt)
            if s["libid"] in ("power:GND", "power:+3V3"):
                pwr_at.append((s["val"], pt))
            else:
                if (s["ref"], num) in pinpos:
                    sys.exit("pino duplicado %s.%s" % (s["ref"], num))
                pinpos[(s["ref"], num)] = pt

    # ---- endpoint de fio no meio de outro fio (ligacao involuntaria)
    def on_segment(p, a, b):
        if p == a or p == b:
            return False
        cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if abs(cross) > 1e-6:
            return False
        dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
        return 0 < dot < (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2

    tees = []
    allpts = set(itertools.chain.from_iterable(wires)) | set(pinpos.values())
    for a, b in wires:
        for p in allpts:
            if on_segment(p, a, b):
                tees.append((p, a, b))
    if tees:
        print("AVISO: %d ponto(s) tocando o meio de um fio:" % len(tees))
        for t in tees[:10]:
            print("   ", t)

    # ---- nomes de net por ponto
    netof = {}
    for name, pt in labels + pwr_at:
        r = find(pt)
        if r in netof and netof[r] != name:
            sys.exit("conflito de nets no mesmo no: %s vs %s em %s" % (netof[r], name, pt))
        netof[r] = name

    # ---- netlist derivada
    derived = {}
    orfaos = []
    for (ref, num), pt in sorted(pinpos.items()):
        r = find(pt)
        if r not in netof:
            orfaos.append((ref, num, pt))
            continue
        derived.setdefault(netof[r], set()).add((ref, num))

    esperado = {k: set(v) for k, v in gen_sch.NETS.items()}
    ncset = set(gen_sch.NC)

    orf = [o for o in orfaos if (o[0], o[1]) not in ncset]
    erros = []
    if orf:
        erros.append("pinos sem net: %s" % orf)
    for p in ncset:
        if p in [(o[0], o[1]) for o in orfaos]:
            continue
        erros.append("pino NC %s.%s acabou conectado" % p)
    for nome in sorted(set(esperado) | set(derived)):
        e, d = esperado.get(nome, set()), derived.get(nome, set())
        if e != d:
            erros.append("net %s difere: sobrando %s, faltando %s"
                         % (nome, sorted(d - e), sorted(e - d)))

    if erros:
        print("FALHOU:")
        for x in erros:
            print("  -", x)
        return 1
    print("netlist geometrica identica a tabela NETS: %d nets, %d pinos conectados, "
          "%d pinos NC" % (len(derived), len(pinpos) - len(orfaos), len(ncset)))
    return 0


def rnd(p):
    return (round(p[0], 2), round(p[1], 2))


if __name__ == "__main__":
    sys.exit(main())
