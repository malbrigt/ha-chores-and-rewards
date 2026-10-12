#!/usr/bin/env bash
# Seed the local Docker HA (after script/dev_onboard.py): English UI, 3 kids, a school-week
# routine. Ada and Bo are at school; Cato is in kindergarten (no homework).
set -euo pipefail
cd "$(dirname "$0")/.."
T='"token":"$token"'
C='"type":"chores_and_rewards/admin/chore/save"'
# Daily chores pay screen time and a little allowance (≈7 € a good week). An extra pays
# allowance, or wins back lost screen time (the kid picks, D49). A once-a-day extra goes to
# the first kid who does it (D51); the trash is open to all. Homework can be ticked ahead (D52).
# Weekdays: 0 = Monday … 6 = Sunday; [] = every day. Currency 1 = screen time (min);
# 3 = allowance in € with cents (amounts in cents, D50), replacing the whole-kroner default 2.
SCHOOL='[0,1,2,3,4]'
"${PYTHON:-.venv/bin/python}" script/dev_ws.py \
  '{"type":"config/core/update","language":"en"}' \
  '{"type":"frontend/set_user_data","key":"language","value":{"language":"en","number_format":"language","time_format":"language","date_format":"language","time_zone":"local","first_weekday":"language"}}' \
  '{"type":"chores_and_rewards/pin/unlock","pin":"1234"}' \
  '{"type":"chores_and_rewards/admin/currency/save",'"$T"',"currency_id":1,"name":"Screen time","unit":"min","icon":"mdi:tablet","payout_weekday":4,"can_be_lost":true,"cap_mode":"fixed","default_max":120}' \
  '{"type":"chores_and_rewards/admin/currency/delete",'"$T"',"currency_id":2}' \
  '{"type":"chores_and_rewards/admin/currency/save",'"$T"',"name":"Allowance","unit":"€","icon":"mdi:cash","payout_weekday":5,"can_be_lost":false,"cap_mode":"pot","decimals":2}' \
  '{"type":"chores_and_rewards/admin/kid/save",'"$T"',"name":"Ada"}' \
  '{"type":"chores_and_rewards/admin/kid/save",'"$T"',"name":"Bo"}' \
  '{"type":"chores_and_rewards/admin/kid/save",'"$T"',"name":"Cato"}' \
  '{'"$C"','"$T"',"name":"Make your bed","icon":"mdi:bed","chore_type":"expected","slot":"morning","weekdays":[],"kid_ids":[1,2,3],"values":{"1":10,"3":20},"sort":10}' \
  '{'"$C"','"$T"',"name":"Tidy the mudroom","icon":"mdi:shoe-sneaker","description":"Shoes and clothes in place. Lunchbox out of the bag and into the dishwasher.","chore_type":"expected","slot":"afternoon","weekdays":'"$SCHOOL"',"kid_ids":[1,2,3],"values":{"1":10,"3":20},"sort":20}' \
  '{'"$C"','"$T"',"name":"Homework","icon":"mdi:book-open-variant","chore_type":"expected","slot":"afternoon","weekdays":'"$SCHOOL"',"kid_ids":[1,2],"values":{"1":20,"3":30},"can_tick_ahead":true,"sort":30}' \
  '{'"$C"','"$T"',"name":"Tidy your room","icon":"mdi:broom","chore_type":"expected","slot":"afternoon","weekdays":[4],"kid_ids":[1,2,3],"values":{"1":15,"3":100},"sort":40}' \
  '{'"$C"','"$T"',"name":"Take out the trash","icon":"mdi:trash-can","chore_type":"bonus","slot":"anytime","weekdays":[],"kid_ids":[1,2,3],"values":{"1":10,"3":30},"sort":50}' \
  '{'"$C"','"$T"',"name":"Clean the shower","icon":"mdi:shower","chore_type":"bonus","slot":"anytime","weekdays":[3,4],"kid_ids":[1],"values":{"1":20,"3":75},"sort":60}' \
  '{'"$C"','"$T"',"name":"Vacuum the mudroom","icon":"mdi:vacuum","chore_type":"bonus","slot":"anytime","weekdays":[2,4],"kid_ids":[1,2,3],"values":{"1":15,"3":75},"once_a_day":true,"sort":70}' \
  '{'"$C"','"$T"',"name":"Set the table","icon":"mdi:silverware-fork-knife","chore_type":"bonus","slot":"anytime","weekdays":[],"kid_ids":[1,2,3],"values":{"1":10,"3":30},"once_a_day":true,"sort":80}' \
  | cut -c1-120
