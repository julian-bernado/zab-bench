# zab
zab is an abstract construct. each time the llm plays the game, the zab is initialized with some number of qualities, at least a name.

## qualities
the zab has the following qualities.

### name
any non-empty string of characters.

### pim
a nonzero integer.

### bim
a color from this list:
- Pink
- Crimson
- Brown
- Maroon
- Red
- Salmon
- Coral
- Chocolate
- Orange
- Gold
- Ivory
- Yellow
- Olive
- Chartreuse
- Lime
- Green
- Aquamarine
- Turquoise
- Azure
- Cyan
- Teal
- Navy
- Blue
- Lavender
- Indigo
- Plum
- Violet
- Magenta
- Purple
- Tan
- Beige
- White
- Silver
- Gray
- Black


## functions
these are the functions the llm can call when playing the zab game.

### zab-independent functions

#### zab-independent functions only affecting one quality

##### zab-independent functions only affecting name
- fin
  - accepts: nothing
  - fin() reverses the name
- bin
  - accepts: nothing
  - bin() changes name to "bad name, please change me immediately!"
- stin
  - accepts: a noun
  - stin(noun) changes name to a spanish translation of noun
- hin
  - accepts: a positive integer n
  - hin(n) keeps the first n characters from the current name
- min
  - accepts: any non-empty string
  - min(string) changes name to string without its first character i.e. `string[1:]`

##### zab-independent functions only affecting pim
- tox
  - accepts: nothing
  - tox() doubles the pim
- plox
  - accepts: an integer from 1-10
  - plox(n) adds n to the current pim value
- rox
  - accepts: a named 2D shape
  - rox(shape) counts the number of sides that shape has then adds that to the current pim value

##### zab-independent functions only affecting bim
- sox
  - accepts: nothing
  - changes the pim to red
- vox
  - accepts: the name of an animal
  - vox(animal) identifies one color best associated with that animal then changed bim to that color
- lox
  - accepts: the name of a color
  - lox(color) changes the bim to some color in-between bim and color
- mox
  - accepts: an integer 1 - 7
  - mox(i) changes the color to the color represented by `"ROYGBIV"[i-1]`

#### zab-independent functions affecting several qualities
- hox
  - accepts: nothing
  - hox() changes the name to "Cama," the bim to 0, and the pim to "Red"
- box
  - accepts: the name of an animal
  - box(animal) changes the bim to the number of legs that animal has and the pim to the predominant color of the animal
- gox
  - 

### functions of one quality
- vin
  - accepts: nothing
  - depends on: some text-based quality
  - vin() changes name to the value of one of the other text-based qualities present in a given zab
  - on game initialization vin selects one of the other text-based qualities in a given zab and tethers to it
- cin
  - accepts: nothing
  - depends on: name
  - cin() changes name to the previous value
  - only loaded in for zabs given a different name-changing function
- 

### functions of several qualities