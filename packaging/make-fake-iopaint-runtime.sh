#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUNTIME_DIR="${1:-fake-iopaint-runtime}"
rm -rf "$RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"

cat > "$RUNTIME_DIR/iopaint" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

has_run=0
image_dir=""
output_dir=""
for arg in "$@"; do
  if [[ "$arg" == "run" ]]; then
    has_run=1
  elif [[ "$arg" == --image=* ]]; then
    image_dir="${arg#--image=}"
  elif [[ "$arg" == --output=* ]]; then
    output_dir="${arg#--output=}"
  fi
done

if [[ "$has_run" != "1" ]]; then
  exit 3
fi
if [[ -z "$image_dir" || -z "$output_dir" ]]; then
  exit 4
fi

mkdir -p "$output_dir"
find "$image_dir" -maxdepth 1 -type f -exec cp {} "$output_dir/" \;
EOF

chmod +x "$RUNTIME_DIR/iopaint"
echo "Fake IOPaint runtime prepared: $PROJECT_ROOT/$RUNTIME_DIR"
