#!/usr/bin/env bash

# ========= 默认参数 =========
OUT_DIR="."
FILE_NAME=""
INTERVAL=1

# ========= 参数解析 =========
usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  -o <dir>     output directory (default: current directory)
  -f <file>    log file name (default: stats_YYYY-MM-DD_HHMMSS.log)
  -i <sec>     sampling interval in seconds (default: 1)
  -h           show this help message

Examples:
  $0
  $0 -o /var/log/sys -f load.log
  $0 -i 2
  $0 -o /tmp -i 5
EOF
}

while getopts ":o:f:i:h" opt; do
  case $opt in
    o) OUT_DIR="$OPTARG" ;;
    f) FILE_NAME="$OPTARG" ;;
    i) INTERVAL="$OPTARG" ;;
    h) usage; exit 0 ;;
    \?) echo "Invalid option: -$OPTARG"; usage; exit 1 ;;
  esac
done

# ========= 参数校验 =========
[[ "$INTERVAL" =~ ^[0-9]+$ ]] || {
  echo "ERROR: interval must be a number"
  exit 1
}

mkdir -p "$OUT_DIR" || {
  echo "ERROR: cannot create directory $OUT_DIR"
  exit 1
}

if [[ -z "$FILE_NAME" ]]; then
  FILE_NAME="stats_$(date +%F_%H%M%S).log"
fi

LOG="${OUT_DIR%/}/$FILE_NAME"

# ========= 运行时字段说明 =========
{
  echo "===== RUNTIME STATS BEGIN ====="

  echo
  echo "[vmstat fields]"
  vmstat | head -2

  echo
  echo "[mpstat fields]"
  echo "%usr=user %nice=nice %sys=kernel %iowait=io_wait"
  echo "%irq=hw_irq %soft=softirq %steal=vm_steal %idle=idle"

  echo
  echo "[iostat -x fields]"
  echo "r/s,w/s=IOPS | rkB/s,wkB/s=throughput"
  echo "await=avg_latency(ms) | %util=device_busy"

  echo
} >> "$LOG"

# ========= 主循环 =========
while true; do
  {
    echo "----- TS: $(date +%F_%T) -----"

    echo
    echo "[CPU - top]"
    top -b -n1 | head -5

    echo
    echo "[CPU/IO - vmstat]"
    vmstat "$INTERVAL" 2 | tail -1

    echo
    echo "[CPU - mpstat]"
    mpstat "$INTERVAL" 1 | tail -n +4

    echo
    echo "[IO - iostat -x]"
    iostat -x "$INTERVAL" 1 2>/dev/null | tail -n +4

    echo
    echo "[MEM - free -m]"
    free -m

    echo
    echo "[GPU - nvidia-smi]"
    nvidia-smi \
      --query-gpu=timestamp,name,utilization.gpu,utilization.memory,memory.total,memory.used \
      --format=csv,noheader 2>/dev/null \
      || echo "nvidia-smi not found"

    echo
  } >> "$LOG"

  sleep "$INTERVAL"
done
