#!/usr/bin/env bash
# Download the public datasets used by v2 into data/external and verify their checksums.
#   SNDlib (Orlowski et al., 2010): Abilene/GEANT topologies, Abilene 5-min traffic matrices (Zhang)
#   KDN training datasets (Mestres et al., 2017): VNF CPU consumption vs traffic features
set -euo pipefail
cd "$(dirname "$0")/.."
D=data/external
mkdir -p "$D/sndlib" "$D/kdn_vnf"
S=https://sndlib.put.poznan.pl/download
K=https://knowledgedefinednetworking.org/data
get() { [ -s "$D/$2" ] || curl -fsSL -m 600 -o "$D/$2" "$1"; }
get "$S/sndlib-networks-native/abilene.txt" sndlib/abilene.txt
get "$S/sndlib-networks-native/geant.txt" sndlib/geant.txt
get "$S/directed-abilene-zhang-5min-over-6months-ALL-native.tgz" sndlib/abilene_tm.tgz
for f in snort firewall ovs; do get "$K/$f.zip" "kdn_vnf/$f.zip"; done
(cd "$D" && sha256sum -c ../../experiments/external_data.sha256)
# extract (archives contain only data files; nothing from them is executed)
[ -d "$D/sndlib/abilene_tm" ] || { mkdir -p "$D/sndlib/abilene_tm"; tar xzf "$D/sndlib/abilene_tm.tgz" -C "$D/sndlib/abilene_tm" --strip-components=1; }
for f in snort firewall ovs; do [ -d "$D/kdn_vnf/$f" ] || unzip -q "$D/kdn_vnf/$f.zip" -d "$D/kdn_vnf/$f"; done
echo "external data ready in $D"
