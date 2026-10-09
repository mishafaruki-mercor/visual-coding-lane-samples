# Making your own Reconstruction sample

A sample is a furnished room. You provide a `.blend` and a short `scene.json`. The tool builds the hidden
answer key, takes the 3 pictures the agent will see, and creates a Harbor task you can run.

## What you need
- **Blender 4.2 or newer** installed locally. The tool finds it on `PATH` or at the default macOS location;
  otherwise set `BLENDER=/path/to/blender`.
- **Python 3.10+** with `pip install -r requirements.txt`.
- **Harbor + Docker**, to validate and run the task.

## 1. Pick a room
Any `.blend` of a furnished room works. Good samples have:
- **5–12 main furniture items**, such as bed, sofa, desk, chair, wardrobe, shelf, table or lamp;
- **real-world size**, or a known unit you can convert (e.g. a room built in feet);
- **items that aren't completely hidden** behind others from every side.

The room doesn't need textures or a clean scene. Walls, floors, lights and decor are simply left out.

## 2. See what's in the file
```bash
mkdir -p samples/my-room && cp ~/Downloads/my_room.blend samples/my-room/
python tooling/make_sample.py --list samples/my-room/my_room.blend
```
This prints every object with its centre and size:
```
collection       object                       type   centre (x, y, z)           size (x, y, z)
Scene Collection Bed_Frame                    MESH   (  11.00,  -2.80,  0.15)    (2.10, 1.60, 0.30)
Scene Collection Bed_Mattress                 MESH   (  11.00,  -2.80,  0.42)    (2.00, 1.50, 0.25)
Scene Collection Pillow.001                   MESH   (  10.25,  -3.20,  0.60)    (0.35, 0.60, 0.12)
Scene Collection Wardrobe_Body                MESH   (  13.80,  -2.40,  1.00)    (0.60, 1.20, 2.00)
Scene Collection Floor                        MESH   (  12.00,  -4.00, -0.01)    (5.00, 4.50, 0.02)
...
```
Use the names, positions and sizes to work out which pieces belong to which piece of furniture. Opening the
file in Blender helps.

## 3. Write `samples/my-room/scene.json`
```json
{
  "name": "my-room",
  "title": "My room",
  "source": "my_room.blend",
  "units_to_metres": 1.0,
  "items": {
    "Bed":        ["Bed_*", "Pillow*"],
    "Nightstand": ["NS_*"],
    "Desk":       ["Desk_*"],
    "Chair":      ["Chair_*"],
    "Wardrobe":   ["Wardrobe_*"],
    "Lamp":       ["Lamp_*"]
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Short id. The task becomes `tasks/recon-<name>` |
| `title` | no | Human-readable name, used in the task description |
| `source` | yes | The `.blend` file, relative to the folder `scene.json` is in |
| `units_to_metres` | no (1.0) | Multiply source units by this to get metres. Use `0.3048` for feet, `0.01` for centimetres |
| `items` | yes | Each furniture item → a list of object-name patterns. All matching objects are joined into that one item |
| `exclude` | no | Patterns to leave out even if an item pattern matches them |
| `colors` | no | `{"Bed": [r, g, b]}` from 0 to 1. Default: the item's own material colour |
| `origin` | no | `"auto"` (default): centre of the furniture, floor at 0. Or `[x, y, z]` in source units |
| `cameras` | no | Default: 3 automatic corner views. Or a list of `{"position": [...], "target": [...]}` in metres |
| `camera_directions` | no | Change the automatic view directions, e.g. `[[-0.55, -0.75, 0.28], ...]` |
| `golden_file` | no | File name of the answer key (default `<name>_full.glb`) |
| `notes` | no | Free text: where the file came from, what you left out |

**Patterns** use `*` (anything), `?` (one character) and `[1-4]` (a range). For example `Chair_*` matches
`Chair_Seat`, `Chair_Back` and `Chair_Leg.000`. An exact name like `Piano` matches only that object.
Anything not matched by an item is left out: walls, floor, rug, books, lights.

**Item names** can be anything ("Bed", "Fridge", "Wardrobe_2"); every item is scored.

Both shipped samples are worked examples: `samples/living-room/scene.json`, with Indonesian object names,
and `samples/gaming-room/scene.json`, built in feet with fixed cameras.

## 4. Build it
```bash
python tooling/make_sample.py samples/my-room/scene.json
```
What it does:
1. **Golden solution.** Joins each item's objects into one mesh, converts to metres, puts the floor at 0,
   and saves `samples/my-room/build/golden.glb`. This is the hidden answer key.
2. **Cameras.** Places 3 cameras around the room and moves them back until every item is in the picture.
3. **Pictures.** Renders the 3 views the agent will get (furniture only, plain background, official
   SceneActBench settings: 768 px, 39.6° field of view).
4. **Harbor task.** Writes `tasks/recon-my-room/` with the official prompt, the camera positions, the
   environment, the hidden answer key and the oracle.
5. **Golden check.** Scores the answer key against itself; it must reach at least 0.95.

If something is wrong it stops and tells you, for example:
```
[my-room] FAILED - fix scene.json and run again:
  - item "Wardrobe": pattern "Wardrobe_Dor*" matched no objects (run make_sample.py --list to see object names)
```
```
[my-room] FAILED - fix scene.json and run again:
  - furniture spans 42 m. Wrong units_to_metres, or a stray object far from the room? Furthest items: Lamp, Wardrobe, Desk
```
Other checks: an object claimed by two items, an item with no surface, an item cut off by the picture edge
in every view, and an item hidden behind other furniture in every view. Warnings (such as an item cut off
in *some* views, or mostly hidden) don't stop the build.

When it succeeds it prints each item's size and how visible it is per view:
```
  6 items, room span [4.2, 4.1, 2.0] m
    Bed                5 objects  size [2.15, 1.6, 1.0] m  visible per view [0.9, 0.93, 1.0]
    ...
  golden check: 1.000 (needs >= 0.95)
[my-room] OK -> tasks/recon-my-room
```

## 5. Look at the pictures
Open `samples/my-room/build/preview.png`, which shows the 3 views side by side. Check that:
- every item you listed is there and recognisable;
- the sizes look right (a bed is about 2 m, a chair about 0.9 m tall);
- nothing you left out (walls, decor) appears.

If a view is poor, set `camera_directions` or `cameras` and rebuild.

## 6. Validate in Harbor
```bash
harbor run -p tasks/recon-my-room -a oracle   # must be ~1.0: the answer key placed in Blender
harbor run -p tasks/recon-my-room -a nop      # must be 0.0: an empty scene
```
The first run builds the Docker image, which takes a few minutes.

## 7. Run a model
```bash
export VERCEL_AI_GATEWAY_API_KEY=...
PYTHONPATH=agents harbor run -p tasks/recon-my-room \
    -a sceneactbench_agent.harbor_agent:SceneActBenchAgent -m <model>
python tooling/report.py jobs/<job>/<trial> --task tasks/recon-my-room --out results/<model>/recon-my-room
```
`report.py` writes the before/after picture, a top-down overlay and a per-item score table (`RESULTS.md`).

## Checklist before sharing a sample
- [ ] `make_sample.py` finished with `OK` and a golden check ≥ 0.95
- [ ] `preview.png` looks right: all items visible, sensible sizes, no walls or decor
- [ ] `harbor run -a oracle` ≈ 1.0 and `harbor run -a nop` = 0.0
- [ ] `scene.json` has `notes` saying where the `.blend` came from and what was left out
- [ ] You're allowed to share the `.blend`. If not, ship only `scene.json` and say where to download it
- [ ] Commit `samples/<name>/scene.json`, the `.blend`, and the generated `tasks/recon-<name>/`
      (`samples/<name>/build/` is regenerated and ignored by git)
