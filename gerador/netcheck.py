#!/usr/bin/env python3
"""Compara a netlist exportada pelo KiCad (kicadxml) com a tabela NETS do gerador
e confere cada footprint contra os filtros de footprint do simbolo.

Uso: python3 -I netcheck.py <net.xml>
"""
import sys, os, fnmatch, xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sch

root = ET.parse(sys.argv[1]).getroot()
kic = {}
for n in root.find("nets"):
    kic[n.get("name").lstrip("/")] = {(x.get("ref"), x.get("pin")) for x in n.findall("node")}

esperado = {k: {p for p in v if not p[0].startswith("#")} for k, v in gen_sch.NETS.items()}
esperado["CS_BARO"].add(("U3", "5"))   # pino 5 do MS5607: oculto, empilhado com o 4
real = {k: v for k, v in kic.items() if not k.startswith("unconnected-")}
soltos = {p for k, v in kic.items() if k.startswith("unconnected-") for p in v}

erros = []
for k in sorted(set(esperado) | set(real)):
    e, r = esperado.get(k, set()), real.get(k, set())
    if e != r:
        erros.append("net %s: faltando %s, sobrando %s" % (k, sorted(e - r), sorted(r - e)))
if soltos != set(gen_sch.NC):
    erros.append("pinos sem conexao diferem do esperado: %s" % sorted(soltos ^ set(gen_sch.NC)))

filtros = {(lp.get("lib"), lp.get("part")): [f.text for f in lp.findall("footprints/fp")]
           for lp in root.find("libparts")}
for c in root.find("components"):
    fp = c.findtext("footprint") or ""
    src = c.find("libsource")
    fl = filtros.get((src.get("lib"), src.get("part")), [])
    if not fp:
        erros.append("%s sem footprint" % c.get("ref"))
    elif fl and not any(fnmatch.fnmatch(fp.split(":")[-1], f) or fnmatch.fnmatch(fp, f) for f in fl):
        erros.append("%s: footprint %s fora do filtro %s" % (c.get("ref"), fp, fl))

if erros:
    print("FALHOU:")
    for e in erros:
        print("  -", e)
    sys.exit(1)
print("netlist do KiCad identica a tabela NETS (%d nets, %d pinos sem conexao); "
      "%d footprints dentro dos filtros" % (len(real), len(soltos), len(root.find("components"))))
