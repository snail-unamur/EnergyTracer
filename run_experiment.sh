#!/usr/bin/env sh

# Configuration

BAR_WIDTH=30

WARMUP_RUNS=10          # Number of warm-up iterations
WARMUP_N=500            # Code iterations per warm-up run

MEASURE_RUNS=30         # Number of measurement iterations
MEASURE_N=1000          # Code iterations per measurement run
COOLDOWN=60             # Sleep duration (seconds) between measurements

OUTPUT_DIR="output"

# Helpers

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

# Start
section "Energy Measurement"
echo "⚠️  Do not interrupt — results may be incomplete."

# 1. Warm-up phase
step "Phase 1: Warm-up ($WARMUP_RUNS iterations x 2 profilers)"

WARMUP_TOTAL=$(( WARMUP_RUNS * 2))
for i in $(seq 1 $WARMUP_RUNS); do
    uv run ET -p carbon -n $WARMUP_N -o warmup-$i --shuffle
    progress_bar $((i * 2 - 1)) "$WARMUP_TOTAL" "Warm-up"

    uv run ET -p mac-silicon -n $WARMUP_N -o warmup-$i --shuffle
    progress_bar $((i * 2)) "$WARMUP_TOTAL" "Warm-up"

done
printf "\r  Warm-up %*s\n" $((BAR_WIDTH + 20)) ""
echo "  ✅ Warm-up complete."

if [ -d "$OUTPUT_DIR/" ]; then
    rm -rf "$OUTPUT_DIR/"
fi

# 2. Measurement phase
step "Phase 2: Measurement ($MEASURE_RUNS iterations x 2 profilers - with cooldown periods of $((COOLDOWN / 60)) min)"

MEASURE_TOTAL=$(( MEASURE_RUNS * 2 ))
for i in $(seq 1 $MEASURE_RUNS); do

    # Sleep between each measurement to allow the system to cool down and stabilize.
    sleep $COOLDOWN

    uv run ET -p carbon -n $MEASURE_N -o measure-$i --shuffle
    progress_bar $((i * 2 - 1)) "$MEASURE_TOTAL" "Measurement"

    sleep $COOLDOWN

    uv run ET -p mac-silicon -n $MEASURE_N -o measure-$i --shuffle
    progress_bar $((i * 2)) "$MEASURE_TOTAL" "Measurement"
done
printf "\r  Measurement %*s\n" $((BAR_WIDTH + 20)) ""
echo "  ✅ Measurement complete."

# 3. End
step "All done! Results are in the '$OUTPUT_DIR/' directory."