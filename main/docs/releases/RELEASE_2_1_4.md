# v2.1.4

## Changed

* **The browser Back button now navigates within the tool** rather than leaving
  the page, as do the mouse back button and Alt+Left. At Home with nothing open,
  Back still leaves the page.
* **The four numbers in "City and castle, side by side" are editable on both
  sides**, with **Copy city to castle** under each half to apply all four at
  once.
* **Unit cards on disk / Info cards on disk** show each image at the size the
  slot above displays it, and that slot no longer duplicates one of them.
* **The 3D viewer opens closer.** A unit's height now fills the frame instead of
  the framing being determined by a horizontal weapon.
* **Preview is renamed Probe** throughout the interface.

## Fixed

* A `battle_models.modeldb` that fails to parse on a valid line now reports the
  character that caused it. An attachment's sprite slot accepts only a bare `0`;
  a digit left attached to it by a manual edit caused the reader to consume the
  next field and fail two lines later on valid input. Reported against Tsardoms
  MP.
