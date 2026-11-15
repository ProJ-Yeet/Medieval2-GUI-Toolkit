-- Copy a battle-model entry under a new name, optionally with a new texture.
--
--   python lua_cli.py run docs/lua_examples/clone_entry.lua --mod <mod> --set from=<entry> --set name=<new entry>
--   ... --set texture=unit_models/_units/my_unit/textures/my_unit.texture

local from = assert(args.from, "give --set from=<entry>")
local name = assert(args.name, "give --set name=<new entry>")

if toolkit.model(name) then
  error(("an entry called %s is already in the modeldb"):format(name))
end
toolkit.clone_model(from, name)
if args.texture then
  toolkit.edit_model(name, { texture = args.texture })
end

local m = toolkit.model(name)
print(("%s: %d LOD(s), %d faction texture(s), first texture %s"):format(
  m.name, #m.lods, #m.textures, m.textures[1] and m.textures[1].texture or "none"))
