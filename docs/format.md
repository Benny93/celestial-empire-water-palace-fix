# Observed save format and repair boundaries

This describes the supplied samples, not a specification for every game version.

Each chunk has a 49-byte little-endian header (`<QQBQQQQ`): magic
`0x222222229E2A83C1`, maximum raw block size 131072, method marker 3,
compressed size, raw size, repeated compressed size, repeated raw size.
A complete zlib stream follows. Zlib checks its embedded Adler-32 checksum;
no additional checksum field was found in this observed outer framing.
The tool checks all sizes, EOF and trailing compressed data and limits decoded
input to 512 MiB. It does not require identical compressed output across zlib versions.

The raw payload starts with an int32 length (total minus four) and an int32 actor
count. Actor records have encoded class/name strings, 80 opaque transform bytes,
one flag byte, a length-prefixed property blob, and a component count. Components
have a name, 80 transform bytes, and a property blob. Non-NUL actor/name bytes
decode by adding one. Property names and resource keys use plain length-prefixed
strings. Transform and trailing level-data semantics are not edited.

Target blobs have a leading zero byte, tagged properties, a None terminator and
eight trailing zero bytes. Tags have a name, recursive type-name tree, int32 size,
and flags. The limited reader supports the target flags 0/16. Other flags and
general nested data are not comprehensively supported. Unrelated blobs remain opaque.

The two target maps store a zero removed-key count, an entry count, then string keys
with byte booleans or float32 values. The repair adds 18 bytes to GatheringResource
and 21 to OwnedResources, updates the map counts and parent lengths, and recompresses.
All bytes outside those edits and length updates must remain unchanged.

The Water Palace is identified by `Building.Monument.WaterPalace`, not a raw string
hit in an improvement or quest. `AddresOfConstructedMonument` must match the first
palace `OccupiedCellsID`. The linked altar owns the construction state and inventory.

The initial samples' offering On/Off comparison changed exactly four boolean values
in GatheringResource (Scroll, Baijiu, ClothesLinen, Duck). That comparison alone did
not prove the map's construction role. The later successful singular-key patch
provided in-game evidence that the added entry restored delivery in this case.

Required quantities are not decoded from a requirement table. The repair does not
assume quantities, modify existing values, or force construction stages. The initial
city's legacy class name contained `deprected`; this is evidence of a legacy class
name, not proof of the precise update/migration failure.
