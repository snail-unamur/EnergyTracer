#!/usr/bin/env sh

# ── Helpers ──────────────────────────────────────────────────
BAR_WIDTH=30

# Displays a progress bar in the terminal.
# Author : Claude Opus 4.6
progress_bar() {
    # Usage: progress_bar <current> <total> <label>
    current=$1; total=$2; label=$3
    filled=$((current * BAR_WIDTH / total))
    empty=$((BAR_WIDTH - filled))
    bar=$(printf '%0.s█' $(seq 1 $filled 2>/dev/null))
    bar="$bar$(printf '%0.s░' $(seq 1 $empty 2>/dev/null))"
    pct=$((current * 100 / total))
    printf "\r  %s [%s] %3d%% (%d/%d)" "$label" "$bar" "$pct" "$current" "$total"
}

# Displays a section header in the terminal.
# Author : Claude Opus 4.6
section() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    printf "║  %-42s  ║\n" "$1"
    echo "╚══════════════════════════════════════════════╝"
}

# Displays a step header in the terminal.
# Author : Claude Opus 4.6
step() {
    echo ""
    echo "── $1 ──"
    echo ""
}

# ── Start ────────────────────────────────────────────────────
section "Energy Measurement"
echo "⚠️  Do not interrupt — results may be incomplete."

# 1. Warm-up phase
step "Phase 1: Warm-up (10 iterations x 2 profilers)"

WARMUP_TOTAL=$((10 * 2))
for i in $(seq 1 10); do
    uv run src/main.py -p carbon -n 1 -o warmup-$i --shuffle
    progress_bar $((i * 2 - 1)) "$WARMUP_TOTAL" "Warm-up"

    uv run src/main.py -p mac-silicon -n 1 -o warmup-$i --shuffle
    progress_bar $((i * 2)) "$WARMUP_TOTAL" "Warm-up"

done
printf "\r  Warm-up %*s\n" $((BAR_WIDTH + 20)) ""
echo "  ✅ Warm-up complete."

if [ -d "output/" ]; then
    rm -rf output/
fi

# 2. Measurement phase
step "Phase 2: Measurement (30 iterations x 2 profilers - with cooldown periods of 1 min)"

MEASURE_TOTAL=$((2 * 30))
for i in $(seq 1 30); do

    # Sleep a minute between each measurement to allow the system to cool down and stabilize.
    sleep 60

    uv run src/main.py -p carbon -n 100 -o measure-$i --shuffle
    progress_bar $((i * 2 - 1)) "$MEASURE_TOTAL" "Measurement"

    sleep 60

    uv run src/main.py -p mac-silicon -n 100 -o measure-$i --shuffle
    progress_bar $((i * 2)) "$MEASURE_TOTAL" "Measurement"
done
printf "\r  Measurement %*s\n" $((BAR_WIDTH + 20)) ""
echo "  ✅ Measurement complete."

# 3. End
step "All done! Results are in the 'output/' directory."

EOF