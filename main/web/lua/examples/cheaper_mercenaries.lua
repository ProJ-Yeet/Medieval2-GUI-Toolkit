-- Make every mercenary in a campaign cheaper (or dearer).
--
--   python lua_cli.py run lua/examples/cheaper_mercenaries.lua --mod <mod> --set factor=0.8
--   ... --set campaign=imperial_campaign   (the default)
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.
--
-- factor 0.8 is 20% cheaper; 1.5 is half as dear again. Costs are rounded to
-- whole florins and never go below 1.

local factor = tonumber(args.factor or "0.8")
local campaign = args.campaign          -- nil means imperial_campaign

local changed = 0
for _, pool in ipairs(toolkit.mercenaries(campaign)) do
  for _, unit in ipairs(pool.units) do
    if unit.cost then
      local cost = math.max(1, math.floor(unit.cost * factor + 0.5))
      if cost ~= unit.cost then
        -- a line of a pool is named by its place in the pool, from 1
        toolkit.edit_merc_unit(pool.name, unit.place, { cost = cost }, campaign)
        changed = changed + 1
      end
    end
  end
end
print(("%d mercenary line(s) repriced by x%s"):format(changed, factor))
