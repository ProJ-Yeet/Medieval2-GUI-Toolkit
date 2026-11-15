-- Raise the morale of one faction's infantry.
--
--   python lua_cli.py run docs/lua_examples/raise_morale.lua --mod <mod> --set faction=england --set by=2
--
-- Add --apply to write it. stat_mental is "morale, discipline, training".

local faction = assert(args.faction, "give --set faction=<name>")
local by = tonumber(args.by or "1")

local function owns(u, f)
  for _, o in ipairs(u.ownership) do
    if o == f then return true end
  end
  return false
end

local count = 0
for _, u in ipairs(toolkit.units()) do
  local mental = u.fields.stat_mental
  if u.category == "infantry" and owns(u, faction) and mental then
    local morale, rest = mental:match("^%s*(%d+)%s*,(.*)$")
    if morale then
      toolkit.edit_unit(u.type, { stat_mental = (tonumber(morale) + by) .. "," .. rest })
      count = count + 1
    end
  end
end
print(("%d %s infantry unit(s) get +%d morale"):format(count, faction, by))
