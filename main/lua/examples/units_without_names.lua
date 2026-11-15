-- List the units that have no shown name in export_units.txt. Reads only.
--
--   python lua_cli.py run lua/examples/units_without_names.lua --mod <mod>
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.

local missing = {}
for _, u in ipairs(toolkit.units()) do
  if u.name == "" then
    missing[#missing + 1] = ("%s (dictionary %s, %s)"):format(u.type, u.dictionary, u.file)
  end
end
table.sort(missing)
for _, line in ipairs(missing) do print(line) end
print(("%d of %d units have no shown name"):format(#missing, #toolkit.units()))
