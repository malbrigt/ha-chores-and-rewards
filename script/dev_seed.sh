#!/usr/bin/env bash
# Seed the local Docker HA with 3 kids and some chores (after script/dev_onboard.py).
set -euo pipefail
cd "$(dirname "$0")/.."
T='"token":"$token"'
C='"type":"chores_and_rewards/admin/chore/save"'
.venv/bin/python script/dev_ws.py \
  '{"type":"chores_and_rewards/pin/unlock","pin":"1234"}' \
  '{"type":"chores_and_rewards/admin/currency/save",'"$T"',"currency_id":1,"name":"Skjermtid","unit":"min","icon":"mdi:tablet","payout_weekday":4,"can_be_lost":true,"cap_mode":"fixed","default_max":120}' \
  '{"type":"chores_and_rewards/admin/kid/save",'"$T"',"name":"Ada"}' \
  '{"type":"chores_and_rewards/admin/kid/save",'"$T"',"name":"Bo"}' \
  '{"type":"chores_and_rewards/admin/kid/save",'"$T"',"name":"Cato"}' \
  '{'"$C"','"$T"',"name":"Re opp sengen","chore_type":"expected","slot":"morning","weekdays":[0,1,2,3,4],"kid_ids":[1,2,3],"values":{"1":10,"2":5}}' \
  '{'"$C"','"$T"',"name":"Dekke bordet","chore_type":"expected","slot":"afternoon","weekdays":[],"kid_ids":[1,2],"values":{"1":20,"2":10}}' \
  '{'"$C"','"$T"',"name":"Tømme søppel","chore_type":"expected","slot":"afternoon","weekdays":[1,4],"kid_ids":[1],"values":{"1":15,"2":10}}' \
  '{'"$C"','"$T"',"name":"Mate katten","chore_type":"expected","slot":"anytime","weekdays":[],"kid_ids":[3],"values":{"1":10}}' \
  '{'"$C"','"$T"',"name":"Vaske vinduer","chore_type":"bonus","slot":"anytime","weekdays":[5,6],"kid_ids":[1,2,3],"values":{"2":50}}' \
  '{'"$C"','"$T"',"name":"Rydde garasjen","chore_type":"bonus","slot":"anytime","weekdays":[],"kid_ids":[2,3],"values":{"2":40}}' \
  | cut -c1-120
