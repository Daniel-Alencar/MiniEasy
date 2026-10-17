#!/bin/sh
# Gera o esquematico a partir das bibliotecas do KiCad instalado e roda todas as
# verificacoes. Uso: gerador/verificar.sh [dir-dos-simbolos]   (padrao: /usr/share/kicad/symbols)
set -e
G=$(cd "$(dirname "$0")" && pwd)
P=$(dirname "$G")
LIBS=${1:-/usr/share/kicad/symbols}
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

python3 -I "$G/gen_sch.py" "$LIBS" "$T/altimetro.kicad_sch"
python3 -I "$G/check_sch.py" "$T/altimetro.kicad_sch"
python3 -I "$G/check_layout.py" "$T/altimetro.kicad_sch"
cp "$P/altimetro.kicad_pro" "$T/"
kicad-cli sch upgrade "$T/altimetro.kicad_sch" >/dev/null
kicad-cli sch erc --severity-all --exit-code-violations -o "$T/erc.rpt" "$T/altimetro.kicad_sch" \
    || { cat "$T/erc.rpt"; exit 1; }
echo "ERC: 0 violacoes"
kicad-cli sch export netlist --format kicadxml -o "$T/net.xml" "$T/altimetro.kicad_sch" >/dev/null
python3 -I "$G/netcheck.py" "$T/net.xml"

cp "$T/altimetro.kicad_sch" "$P/altimetro.kicad_sch"
kicad-cli sch export pdf -o "$P/altimetro.pdf" "$P/altimetro.kicad_sch" >/dev/null
kicad-cli sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' \
    --labels 'Referencias,Valor,Footprint,Qtd' --group-by 'Value,Footprint' \
    --ref-range-delimiter '' -o "$P/bom.csv" "$P/altimetro.kicad_sch" >/dev/null
echo "gravado: altimetro.kicad_sch, altimetro.pdf, bom.csv"
