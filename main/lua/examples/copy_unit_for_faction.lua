-- Copy a unit for one faction: a new unit with its own name, owned only by
-- that faction, and stronger by a point of attack.
--
--   python lua_cli.py run lua/examples/copy_unit_for_faction.lua --mod <mod> --set from="Peasants" --set type="Royal Peasants" --set faction=england
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.
--
-- Shows edits that build on each other: the second edit changes the unit the
-- first one made, and a read after an edit sees it.

local from = assert(args.from, 'give from=<unit type> as an argument')
local new = assert(args.type, 'give type=<new unit type> as an argument')
local faction = assert(args.faction, "give faction=<name> as an argument")

toolkit.clone_unit(from, new, { name = args.name or new })

-- stat_pri is "attack, charge, missile type, ...": raise the first number
local unit = toolkit.unit(new)
local pri = {}
for i, v in ipairs(unit.stat_pri) do pri[i] = v end
pri[1] = tostring(tonumber(pri[1]) + 1)

local changes = {
  ownership = { faction },          -- a list is written as "england"
  stat_pri = pri,
}
-- era lines are not in every mod: set only the ones the unit has
for _, era in ipairs({ "era 0", "era 1", "era 2" }) do
  if unit.fields[era] then
    changes[era] = { faction }      -- a field name with a space is a quoted key
  end
end
toolkit.edit_unit(new, changes)
print(("%s copied as %s for %s, attack %s"):format(from, new, faction, pri[1]))
