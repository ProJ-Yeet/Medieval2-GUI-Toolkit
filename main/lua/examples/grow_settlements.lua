-- Grow the population of every settlement a faction starts with.
--
--   python lua_cli.py run lua/examples/grow_settlements.lua --mod <mod> --set faction=england --set percent=25
--   ... --set campaign=imperial_campaign   (the default)
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.
--
-- The settlement panel's own checks still apply: a population too big for a
-- settlement's level is reported as a warning in the run's report.

local faction = assert(args.faction, "give faction=<name> as an argument")
local percent = tonumber(args.percent or "10")
local campaign = args.campaign

local grown = 0
for _, s in ipairs(toolkit.settlements(campaign)) do
  if s.faction == faction and s.population then
    local population = math.floor(s.population * (1 + percent / 100) + 0.5)
    toolkit.edit_settlement(s.region, { population = population }, campaign)
    print(("%-30s %6d -> %6d"):format(s.region, s.population, population))
    grown = grown + 1
  end
end
print(("%d settlement(s) of %s grown by %d%%"):format(grown, faction, percent))
