-- Replace a word in every entry of one text archive (a .strings.bin).
--
--   python lua_cli.py run lua/examples/replace_text.lua --mod <mod> --set file=event_titles --set from=Merchant --set to=Trader
--   In the app's Lua tab: pick it under Examples and give the same values in the
--   Arguments box, one key=value a line. Guide: lua/guide.html.
--
-- `file` is the archive in data/text without its ending: event_titles means
-- data/text/event_titles.txt.strings.bin. The match is plain text, not a
-- pattern, and it is case sensitive.

local file = assert(args.file, "give file=<archive> as an argument")
local from = assert(args.from, "give from=<text> as an argument")
local to = args.to or ""

-- Lua's gsub reads patterns; escape every magic character so `from` is plain
local plain = from:gsub("[%^%$%(%)%%%.%[%]%*%+%-%?]", "%%%0")
local safe_to = to:gsub("%%", "%%%%")

local changes, n = {}, 0
for i, entry in ipairs(toolkit.strings(file)) do
  local new, hits = entry.value:gsub(plain, safe_to)
  if hits > 0 then
    -- a tagged archive is keyed by tag, one with no tags by place from 1
    changes[entry.tag ~= "" and entry.tag or i] = new
    n = n + 1
  end
end

if n > 0 then
  toolkit.edit_strings(file, changes)   -- one call, every change at once
end
print(("%d entr%s changed in %s"):format(n, n == 1 and "y" or "ies", file))
