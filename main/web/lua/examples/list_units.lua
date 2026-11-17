-- List one faction's units: a first script that only reads.
--
--   python lua_cli.py run lua/examples/list_units.lua --mod <mod> --set faction=england
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.
--
-- Leave out --set faction to list every unit. Nothing is ever written by a
-- script that only calls the read functions.

local faction = args.faction   -- nil when not given

-- true when the unit's ownership line names the faction
local function owned_by(unit, name)
  for _, owner in ipairs(unit.ownership) do
    if owner == name then return true end
  end
  return false
end

local shown = 0
for _, u in ipairs(toolkit.units()) do
  if faction == nil or owned_by(u, faction) then
    -- u.name is the shown name (from export_units.txt), u.type the EDU's own
    print(("%-40s %-10s %-8s %s"):format(u.type, u.category, u.class, u.name))
    shown = shown + 1
  end
end
print(("%d unit(s)"):format(shown))
