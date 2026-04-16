#!/usr/bin/env bash
# =============================================================================
# generate_protos.sh — gRPC Python-Stubs aus Proto-Definitionen generieren
# =============================================================================
# Aufruf:
#   bash scripts/generate_protos.sh
#   make proto
#
# Voraussetzungen:
#   pip install grpcio-tools protobuf
#
# Output:
#   packages/shared/generated/python/*.py  (pb2.py + pb2_grpc.py fuer jedes Proto)
#   packages/shared/generated/python/*.pyi (Type-Stubs fuer Mypy/IDE)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PROTO_DIR="$PROJECT_ROOT/proto"
OUT_DIR="$PROJECT_ROOT/packages/shared/generated/python"

echo "=== TI-Radar v2 — gRPC Python Stub-Generierung ==="
echo "Proto-Verzeichnis:  $PROTO_DIR"
echo "Output-Verzeichnis: $OUT_DIR"
echo ""

# Pruefen ob grpcio-tools installiert ist
if ! python -m grpc_tools.protoc --version &>/dev/null 2>&1; then
    echo "FEHLER: grpcio-tools nicht gefunden."
    echo "Installation: pip install grpcio-tools>=1.60 protobuf>=4.25"
    exit 1
fi

# Pruefen ob Proto-Dateien vorhanden sind
PROTO_FILES=("$PROTO_DIR"/*.proto)
if [ ${#PROTO_FILES[@]} -eq 0 ]; then
    echo "FEHLER: Keine .proto-Dateien in $PROTO_DIR gefunden."
    exit 1
fi

echo "Gefunden: ${#PROTO_FILES[@]} Proto-Dateien"

# Output-Verzeichnis vorbereiten (alte Stubs entfernen)
mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*_pb2.py "$OUT_DIR"/*_pb2_grpc.py "$OUT_DIR"/*_pb2.pyi "$OUT_DIR"/*_pb2_grpc.pyi

# Alle .proto-Dateien kompilieren
echo "Kompiliere Proto-Dateien..."
python -m grpc_tools.protoc \
    --proto_path="$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    --pyi_out="$OUT_DIR" \
    "${PROTO_FILES[@]}"

echo "Protobuf-Kompilierung erfolgreich."
echo ""

# Import-Pfade fixen: protoc generiert absolute Imports (import common_pb2),
# aber innerhalb eines Python-Packages brauchen wir relative Imports
# (from . import common_pb2) damit das Package korrekt importierbar ist.
echo "Fixe Import-Pfade (-> relative Imports)..."

fix_count=0
for f in "$OUT_DIR"/*_pb2.py "$OUT_DIR"/*_pb2_grpc.py "$OUT_DIR"/*.pyi; do
    [ -f "$f" ] || continue
    # Ersetze "import xxx_pb2" mit "from . import xxx_pb2"
    # Matcht nur Zeilen die mit "import" beginnen und auf "_pb2" enden
    # Ignoriert "from google.protobuf import ..." etc.
    if grep -q '^import [a-z0-9_]*_pb2' "$f" 2>/dev/null; then
        sed -i 's/^import \([a-z0-9_]*_pb2[a-z0-9_]*\)/from . import \1/g' "$f"
        fix_count=$((fix_count + 1))
    fi
done

echo "  $fix_count Dateien gepatcht."
echo ""

# __init__.py fuer das generated-Package und das python-Subpackage
echo "Aktualisiere __init__.py Dateien..."

touch "$PROJECT_ROOT/packages/shared/generated/__init__.py"

cat > "$OUT_DIR/__init__.py" << 'PYEOF'
"""Auto-generated gRPC Python stubs.

Generiert aus proto/ via scripts/generate_protos.sh.
Nicht manuell editieren!

Usage:
    from packages.shared.generated.python import common_pb2
    from packages.shared.generated.python import uc1_landscape_pb2
    from packages.shared.generated.python import uc1_landscape_pb2_grpc
"""
PYEOF

# Zusammenfassung
echo ""
echo "=== Generierung abgeschlossen ==="
PB2_COUNT=$(find "$OUT_DIR" -name "*_pb2.py" -not -name "*_grpc*" | wc -l)
GRPC_COUNT=$(find "$OUT_DIR" -name "*_pb2_grpc.py" | wc -l)
PYI_COUNT=$(find "$OUT_DIR" -name "*.pyi" | wc -l)
echo "  Protobuf-Module:  $PB2_COUNT"
echo "  gRPC-Service-Stubs: $GRPC_COUNT"
echo "  Type-Stubs (.pyi):  $PYI_COUNT"
echo ""

# Generierte Dateien auflisten
echo "Generierte Dateien:"
for f in "$OUT_DIR"/*_pb2.py; do
    [ -f "$f" ] && echo "  $(basename "$f")"
done
echo ""
echo "Import-Beispiel:"
echo "  from packages.shared.generated.python import common_pb2"
echo "  from packages.shared.generated.python import uc1_landscape_pb2_grpc"
