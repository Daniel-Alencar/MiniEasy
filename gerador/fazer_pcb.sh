#!/bin/sh
# Gera a PCB a partir do esquematico: posiciona, autorroteia (Freerouting), cria
# planos de GND e serigrafia, roda DRC com paridade e so entao grava no projeto.
#
# Requer: KiCad 10 (pcbnew Python + kicad-cli), Java 25+ e Freerouting 2.4.1.
# Uso: FREEROUTING=/caminho/freerouting-2.4.1.jar JAVA=/caminho/java gerador/fazer_pcb.sh [dir-trabalho]
set -e
G=$(cd "$(dirname "$0")" && pwd)
P=$(dirname "$G")
JAVA=${JAVA:-java}
FR=${FREEROUTING:?defina FREEROUTING=/caminho/freerouting.jar}
T=${1:-$(mktemp -d)}
mkdir -p "$T"
q() { grep -v -E 'property.h|Debug: Adding'; }

python3 "$G/build_pcb.py" place "$P" "$T" 2>&1 | q
cp "$P/altimetro.kicad_dru" "$P/altimetro.kicad_sch" "$T/"
rm -f "$T/altimetro.ses"
(cd "$T" && "$JAVA" -Djava.awt.headless=true -jar "$FR" --gui.enabled=false \
    -de altimetro.dsn -do altimetro.ses -mp 60 > fr.log 2>&1)
grep -o 'final score: [^,]*, *([^)]*)' "$T/fr.log" | tail -1 | sed 's/^/freerouting: /'
python3 "$G/build_pcb.py" finish "$P" "$T" 2>&1 | q
kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations \
    -o "$T/drc.rpt" "$T/altimetro.kicad_pcb" >/dev/null || {
    grep -E '^\[' "$T/drc.rpt" | sed 's/:.*//' | sort | uniq -c
    echo "DRC falhou; relatorio em $T/drc.rpt"; exit 1; }
echo "DRC: 0 violacoes, 0 pads desconectados, paridade com o esquematico ok"

python3 "$G/build_pcb.py" merge-pro "$P" "$T"
cp "$T/altimetro.kicad_pcb" "$P/"

# saidas de fabricacao
F="$P/fabricacao"
rm -rf "$F"; mkdir -p "$F/gerber"
B="$P/altimetro.kicad_pcb"
kicad-cli pcb export gerbers -o "$F/gerber" --subtract-soldermask \
    -l "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" "$B" >/dev/null
kicad-cli pcb export drill -o "$F/gerber/" --format excellon --excellon-separate-th \
    --generate-map --map-format pdf "$B" >/dev/null
(cd "$F/gerber" && zip -q -r ../altimetro-gerber.zip .)
kicad-cli pcb export pos -o "$F/altimetro-pos.csv" --side front --format csv --units mm \
    --exclude-dnp "$B" >/dev/null
kicad-cli pcb export pdf -o "$F/altimetro-montagem.pdf" --mode-single --scale 0 \
    --layers "F.Fab,F.Courtyard,Edge.Cuts" "$B" >/dev/null
kicad-cli pcb render --side top --width 1600 --height 900 --quality high \
    -o "$F/altimetro-topo.png" "$B" >/dev/null
kicad-cli pcb render --side bottom --width 1600 --height 900 --quality high \
    -o "$F/altimetro-verso.png" "$B" >/dev/null
cp "$P/bom.csv" "$F/altimetro-bom.csv"
echo "gravado: altimetro.kicad_pcb, altimetro.kicad_pro, fabricacao/ (trabalho em $T)"
