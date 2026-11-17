-- Let more of a unit be recruited: raise the pool maximum of every
-- recruit_pool line that names it (the recruitment sheet's Maximum column).
--
--   python lua_cli.py run lua/examples/bigger_recruit_pools.lua --mod <mod> --set unit="Peasants" --set by=1
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.
--
-- `unit` is the name the EDB's recruit_pool lines use (the unit's `type`).

local unit = assert(args.unit, 'give unit=<unit type> as an argument')
local by = tonumber(args.by or "1")

local n = 0
for _, row in ipairs(toolkit.recruits()) do
  if row.unit == unit then
    -- row.line names the line in export_descr_buildings.txt
    toolkit.edit_recruit(row.line, { maximum = row.maximum + by })
    print(("%s/%s: maximum %s -> %s"):format(row.building, row.level, row.maximum, row.maximum + by))
    n = n + 1
  end
end
print(("%d recruit_pool line(s) for %s"):format(n, unit))
