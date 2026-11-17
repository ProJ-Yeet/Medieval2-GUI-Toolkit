-- A report of one trait: its levels, what each level does, and which
-- triggers give it points. Reads only.
--
--   python lua_cli.py run lua/examples/trait_report.lua --mod <mod> --set trait=GoodCommander
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.

local name = assert(args.trait, "give trait=<trait name> as an argument")
local trait = toolkit.trait(name)
if not trait then error("no trait called " .. name) end

print(("Trait %s, for %s%s"):format(trait.name, table.concat(trait.characters, ", "),
  trait.hidden and " (hidden)" or ""))
for i, level in ipairs(trait.levels) do
  local effects = {}
  for _, e in ipairs(level.effects) do
    effects[#effects + 1] = e.attribute .. " " .. e.amount
  end
  print(("  %d. %s at %s points: %s"):format(i, level.name, level.threshold,
    #effects > 0 and table.concat(effects, ", ") or "no effects"))
end

-- a trigger gives points with an effect line `Affects <trait> <points> Chance <n>`
print("Triggers that give it points:")
for _, t in ipairs(toolkit.triggers("traits")) do
  for _, e in ipairs(t.effects) do
    if e.keyword == "Affects" and e.args[1] == name then
      print(("  %s (%s): %s"):format(t.name, t.when_to_test, table.concat(e.args, " ")))
    end
  end
end
