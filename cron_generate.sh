#!/bin/bash
# Posts are triggered by separate cron slots — this script checks if it should fire for slot $1
# Slot numbers: 1=8am, 2=12pm, 3=4pm, 4=8pm, 5=11pm (all UTC)
SLOT=$1

START=$(cat /opt/handholding-engine/cron_start_date.txt)
DAYS=$(( ($(date -d "$(date +%Y-%m-%d)" +%s) - $(date -d "$START" +%s)) / 86400 ))

if   [ $DAYS -lt 30  ]; then COUNT=1
elif [ $DAYS -lt 60  ]; then COUNT=2
elif [ $DAYS -lt 90  ]; then COUNT=3
elif [ $DAYS -lt 120 ]; then COUNT=4
else                          COUNT=5
fi

# Only fire if this slot is within today's count
if [ "$SLOT" -gt "$COUNT" ]; then
  exit 0
fi

echo "[$(date -u)] slot=$SLOT day=$DAYS count=$COUNT — triggering" >> /var/log/handholding-cron.log

curl -s -X POST http://localhost:5000/demo/full-automation/start \
  -H 'Content-Type: application/json' \
  -d '{}' >> /var/log/handholding-cron.log 2>&1

echo " done" >> /var/log/handholding-cron.log
