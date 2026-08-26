# Case Domain Knowledge

## Form factor detection from names
- `(mATX)` / `Micro ATX` → supports mATX and smaller
- `(ATX)` explicit → supports ATX and smaller
- `(ITX)` → ITX only
- No marker → assume mATX-class (most common in Thai market listings)

## Cooling clearance note
- Air coolers > 155mm height and GPUs > 330mm length need mid/full towers;
  this data is rarely in listing names, so it is reported as UNKNOWN (skipped),
  never guessed.
