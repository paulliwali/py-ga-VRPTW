# AGENT.md — Project Context & Developer Guide

## 1. Project Overview

**`py-ga-VRPTW` / `py-ga-VRPMV`** is a Python 2.7 Genetic Algorithm (GA) framework built on [DEAP](https://github.com/DEAP/deap) for solving:
1. **VRPTW** (Vehicle Routing Problem with Time Windows) — forked from [`iRB-Lab/py-ga-VRPTW`](https://github.com/iRB-Lab/py-ga-VRPTW) with fixes to Partially Matched Crossover (PMX), elitist selection, and `multiprocessing` support.
2. **VRPMV / VRPMS** (Vehicle Routing Problem with Movement Synchronization) — an extension where a **heavy resource** (e.g., truck) teams up with a **light resource** (e.g., drone or courier). The light resource departs from the heavy vehicle at a customer node, serves a cluster of customers within its range and capacity limits, and rejoins (rendezvous with) the heavy vehicle at a downstream customer node.

---

## 2. Two-Stage Solution Architecture

The active solver workflow (`instance_run_scripts/`) decouples the problem into two sequential GA stages:

### Stage 1: Heavy-Vehicle VRPTW (`gavrptw`)
- **Chromosome Representation**: A 1-indexed permutation list of all customer IDs `[1, 2, ..., N]` (depot `0` is implicit).
- **Decoding (`gavrptw.core.ind2route`)**: Splits the permutation greedily into feasible heavy-vehicle sub-routes whenever adding the next customer would exceed `instance['vehicle_capacity']` or return to the depot after `instance['deport']['due_time']` (accounting for travel distance $\times$ `speed` and `service_time`).
- **Evaluation (`gavrptw.core.evalVRPTW`)**: Computes travel cost (`unitCost * distance * speed`) plus time-window penalties (`waitCost` for arriving before `ready_time`, `delayCost` for arriving after `due_time`). Returns `(1.0 / totalCost,)`.
- **Genetic Operators**:
  - **Selection**: Keeps `1` elite individual untouched past crossover/mutation; forms the mating pool from the top `10%` (`tools.selBest`) + `90% - 1` (`tools.selRoulette`).
  - **Crossover (`gavrptw.core.cxPartialyMatched`)**: DEAP's PMX adapted for 1-indexed customer IDs (offsets positions by `-1` so customer `1..N` maps to index `0..N-1`).
  - **Mutation (`gavrptw.core.mutInverseIndexes`)**: Reverses a randomly sampled contiguous slice of the chromosome.
- **Parallelism**: Uses `multiprocessing.Pool().map` registered to `toolbox.map`.

### Stage 2: Movement Synchronization per Sub-Route (`gatspmv`)
Takes each heavy sub-route (TSP tour) produced by Stage 1 and optimizes coordinated heavy + light resource routing:
1. **Light Customer Clustering (`gatspmv.mvCore.splitLightCustomers`)**:
   - Evaluates inter-customer distances along the sub-route and greedily grows clusters of interior customers (excluding the first and last customer of the sub-route) that satisfy `lightRange` (cumulative distance including departure and reunion legs) and `lightCapacity` (cumulative customer demand, excluding rendezvous nodes).
   - Returns a binary mask of length `len(tsp)`, e.g. `[0, 0, 1, 1, 0, 0]`, where `1` marks customers assigned to the light resource.
2. **MV Individual Initialization (`gatspmv.mvCore.initMVIndividuals`)**:
   - Splits the TSP sub-route wherever the binary mask transitions between `0` and `1`.
   - Even segments (`splitList[0::2]`) are concatenated to form the **heavy vehicle genome** (`heavyGenome`).
   - Odd segments (`splitList[1::2]`) form **light vehicle sub-routes**, each bookended by a randomly sampled departure node from the preceding heavy segment (`splitList[i-2]`) and a randomly sampled reunion node from the succeeding heavy segment (`splitList[i]`).
   - **Resulting Chromosome Format**: `[[L_1], [L_2], ..., [H]]`
     - Each `[L_k] = [depart_customer, light_customer_1, ..., rejoin_customer]`
     - `[H] = [heavy_customer_1, heavy_customer_2, ...]` (always at index `-1`).
3. **Synchronized Evaluation (`gatspmv.mvCore.evalTSPMS`)**:
   - Simulates the heavy route `route[-1]` first, recording `heavyArrivalTime` and `heavyDepartureTime` at each heavy customer (note: `heavyServiceTime` is multiplied by `2` in `evalTSPMS`), along with heavy travel and time-window costs.
   - Simulates each light sub-route `subLightRoute` in `route[:-1]`, starting at `heavyArrivalTime[depart_customer]`, accumulating light travel and time-window costs (`lightSpeed`, `lightUnitCost`, `lightWaitCost`, `lightDelayCost`), and computing `lightFinishTime` at `rejoin_customer`.
   - Computes synchronization delay `resourceDelayTime[rejoin_customer]`:
     - Negative value $\rightarrow$ light resource arrived early and waits for heavy resource (`lightWaitCost * abs(delay)`).
     - Positive value $\rightarrow$ heavy resource waited for light resource (`waitCost * delay`).
   - Returns `(1 / totalCost,)`.
4. **MV Crossover (`gatspmv.mvCore.cxSinglePointSwap`)**:
   - Iterates over paired light sub-routes `(subRoute1, subRoute2)` in `zip(ind1[:-1], ind2[:-1])`.
   - With 50% probability swaps the departure rendezvous customer (`subRoute[0]`), otherwise swaps the reunion rendezvous customer (`subRoute[-1]`).

> **Note on Legacy Single-Stage VRPMS in `gavrptw/core.py`**:
> `gavrptw/core.py` also contains `ind2routeMS`, `evalVRPMS`, and `gaVRPMS`. That was an earlier single-stage formulation that greedily grouped consecutive customers into `[[heavy], [light], [heavy]]` triplets during route decoding. The two-stage `gavrptw` + `gatspmv` workflow in `instance_run_scripts/` superseded it.

---

## 3. Repository Layout

```text
├── gavrptw/
│   ├── __init__.py          # Defines BASE_DIR (repo root)
│   ├── core.py              # VRPTW decoding (ind2route), evaluation (evalVRPTW), PMX crossover, mutation, printRoute, plus legacy VRPMS functions
│   └── utils.py             # text2json converter, CSV fitness plotting (plotResults), route plotting (visualizeRoutes), file helpers
├── gatspmv/
│   ├── __init__.py          # Defines BASE_DIR (repo root)
│   └── mvCore.py            # Stage 2 movement synchronization: splitLightCustomers, initMVIndividuals, evalTSPMS, cxSinglePointSwap
├── instance_run_scripts/
│   ├── sample_P-nX-X.py         # Latest Stage 1 runner (supports speed parameter, multiprocessing, elite selection)
│   ├── sample_P-nX-X-VRPMS.py   # Latest Stage 2 runner (pairs with sample_P-nX-X.py, runs gaTSPMV on sub-routes)
│   ├── sample_A-n32-k5.py       # Stage 1 runner for Augerat A-n32-k5 instance
│   ├── sample_A-n32-k5-VRPMV.py # Stage 2 runner for Augerat A-n32-k5 instance
│   ├── sample_P-n10-k2.py       # Stage 1 runner for 10-customer MIP comparison instance
│   └── sample_P-n10-k2-VRPMV.py # Stage 2 runner for 10-customer MIP comparison instance
├── data/
│   ├── text/                # Standard 100-customer Solomon VRPTW benchmark instances (.txt)
│   ├── json/                # Compiled JSON Solomon instances (generated by text2json.py)
│   ├── text_customize/      # Custom instances: A-n32-k5, P-n5-k1, P-n10-*, P-n15-*, P-n20-*, P-n50-0, P-n100-0
│   ├── json_customize/      # Compiled JSON custom instances (generated by text2json_customize.py)
│   └── plot/                # Saved route visualization PNGs
├── text2json.py             # CLI script to convert data/text/*.txt -> data/json/*.json
├── text2json_customize.py   # CLI script to convert data/text_customize/*.txt -> data/json_customize/*.json
├── plotResults.py           # CLI script to plot generation fitness curves from results/*.csv -> results/*.png
├── ind2route.py             # Scratch/test script for PMX and ind2routeMS
├── ga-spec.txt              # Benchmark log of GA hyperparameter sweeps (nGen, popSize, runTime, bestCost) on A-n32-k5 & F-n135-k7
└── requirements.txt         # deap>=1.0.2, numpy>=1.13, pandas>=0.20, matplotlib>=2.0
```

---

## 4. Data Formats

### Raw Text Format (`data/text/` and `data/text_customize/`)
Strict line-number-based format parsed by `gavrptw.utils.text2json()`:
- **Line 1**: Instance name (must match filename stem, e.g., `P-n10-0`).
- **Lines 2–4**: Header text (ignored).
- **Line 5**: `<max_vehicle_number> <vehicle_capacity>` (optionally followed by `<max_light_vehicle_number> <light_vehicle_capacity> <light_vehicle_range>`).
- **Lines 6–9**: Customer table headers (ignored).
- **Line 10**: Depot (`0`) row: `0 <x> <y> <demand> <ready_time> <due_time> <service_time>`.
- **Lines 11+**: Customer (`1..N`) rows: `<id> <x> <y> <demand> <ready_time> <due_time> <service_time>`.

### Compiled JSON Format (`data/json/` and `data/json_customize/`)
- `"instance_name"`: string
- `"max_vehicle_number"`: int, `"vehicle_capacity"`: float
- `"deport"`: dict with `"coordinates": {"x", "y"}`, `"demand"`, `"ready_time"`, `"due_time"`, `"service_time"` *(Note the spelling `"deport"`!)*
- `"customer_1"` ... `"customer_N"`: dicts with the same structure as `"deport"`
- `"distance_matrix"`: $(N+1) \times (N+1)$ 2D list of Euclidean distances where index `0` is `"deport"` and index `i` is `"customer_i"`.

---

## 5. Known Quirks, Gotchas & Technical Debt

Read this section carefully before modifying or running code:

1. **Python 2.7 Codebase**:
   - Uses Python 2 `print` statements, `xrange()` (in `gavrptw/core.py:cxPartialyMatched`), and `df.append()` (in `gavrptw/utils.py`).
   - Run scripts with a Python 2.7 interpreter, or port `print` / `xrange` / relative imports if migrating to Python 3.

2. **Module Filename Casing (`gatspmv/mvCore.py` vs `mvcore`)**:
   - The file on disk is `gatspmv/mvCore.py` (capital `C`), but scripts import `from gatspmv import mvcore` (lowercase `c`).
   - On case-sensitive filesystems (Linux) or strict module loaders, `from gatspmv import mvcore` will raise `ImportError`. Even on macOS/Windows, Python's import machinery can be case-sensitive for module names. If importing fails, either import `mvCore as mvcore` or rename `mvCore.py` to `mvcore.py`.

3. **`"deport"` Spelling in JSON & Code**:
   - The depot key is spelled `"deport"` across `gavrptw/utils.py`, `gavrptw/core.py`, and all generated `.json` files. Do **not** change `"deport"` to `"depot"` in code without updating `utils.py` and regenerating all JSON files.

4. **Function Signature Drift Across Sample Scripts**:
   - Commit `8b290f5` updated `gavrptw.core.evalVRPTW` and `gatspmv.mvCore.evalTSPMS` to accept `speed` (and `lightSpeed`) and **removed** `initCost` (and `lightInitCost`).
   - `instance_run_scripts/sample_P-nX-X.py` and `instance_run_scripts/sample_P-nX-X-VRPMS.py` match the current signatures in `core.py` and `mvCore.py`.
   - Older scripts (`sample_A-n32-k5.py`, `sample_A-n32-k5-VRPMV.py`, `sample_P-n10-k2.py`, `sample_P-n10-k2-VRPMV.py`, and `ind2route.py`) still pass `initCost=initCost` / `lightInitCost=lightInitCost` to `evalVRPTW` / `evalTSPMS` and will raise `TypeError: evalVRPTW() got an unexpected keyword argument 'initCost'` unless `initCost` is removed from their `toolbox.register('evaluate', ...)` calls.

5. **Commented-Out Imports in `gavrptw/core.py`**:
   - Lines 9–10 of `gavrptw/core.py` (`#from . import BASE_DIR` and `#from .utils import makeDirsForFile, exist`) were commented out during multiprocessing refactoring.
   - As a result, `core.gaVRPTW()` and `core.gaVRPMS()` inside `gavrptw/core.py` cannot be called directly without uncommenting those imports; the active `gaVRPTW` and `gaTSPMV` drivers live in `instance_run_scripts/`.

6. **Trailing Blank Lines in `.txt` Instance Files**:
   - `gavrptw.utils.text2json()` computes `numOfCustomers = size - 9` where `size` is the total line count of the `.txt` file.
   - A trailing blank line at the end of a `.txt` file (like line 42 in `data/text_customize/A-n32-k5.txt` if empty) increments `size` and causes `KeyError` unless there is no trailing newline or empty lines are stripped.

7. **Mutation in Stage 2 (`gaTSPMV`)**:
   - `gaTSPMV` registers `core.mutInverseIndexes` as `toolbox.mutate`, which reverses a slice of the top-level individual list `[[L_1], ..., [H]]`.
   - Because `evalTSPMS` assumes `route[-1]` is the heavy route `[H]` and `route[:-1]` are light routes, running `mutInverseIndexes` on an MV individual can move `[H]` out of index `-1` and break evaluation. Keep `mutPb = 0` in Stage 2 unless a custom MV mutation operator is implemented.

8. **Route Visualization (`gavrptw.utils.visualizeRoutes`)**:
   - Works for standard VRPTW routes (`containsLightResource=False`), saving plots to `data/plot/<instanceName>.png`.
   - The `else:` block for `containsLightResource=True` is accidentally indented under the `for subRoutes in route:` loop (making it a `for..else` block) and is marked `# TODO`.

---

## 6. Common Workflows

Run all commands from the repository root (`/Users/pauldeng/Documents/code/py-ga-VRPTW`):

```bash
# 1. Convert text benchmark instances to JSON
python text2json.py            # data/text/*.txt -> data/json/*.json
python text2json_customize.py  # data/text_customize/*.txt -> data/json_customize/*.json

# 2. Run Stage 1: Heavy-vehicle VRPTW GA (outputs sub-routes and CSV stats to results/)
python instance_run_scripts/sample_P-nX-X.py

# 3. Run Stage 2: Movement Synchronization GA on Stage 1 sub-routes
# (Paste the bestVRP sub-routes from Stage 1 into bestVRP in sample_P-nX-X-VRPMS.py)
python instance_run_scripts/sample_P-nX-X-VRPMS.py

# 4. Plot fitness evolution curves from results/*.csv -> results/*.png
python plotResults.py
```
