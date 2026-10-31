# AGENT.md — Project Context & Developer Guide

## 1. Project Overview

**`py-ga-VRPTW` / `py-ga-VRPMV`** is a Python 3.12+ Genetic Algorithm (GA) framework built on [DEAP](https://github.com/DEAP/deap) for solving:
1. **VRPTW** (Vehicle Routing Problem with Time Windows) — forked from [`iRB-Lab/py-ga-VRPTW`](https://github.com/iRB-Lab/py-ga-VRPTW) with fixes to Partially Matched Crossover (PMX), elitist selection, 2-opt local search, and `multiprocessing` support.
2. **VRPMV / VRPMS** (Vehicle Routing Problem with Movement Synchronization) — an extension where a **heavy resource** (e.g., truck) teams up with a **light resource** (e.g., drone or courier). The light resource departs from the heavy vehicle at a customer node, serves a cluster of customers within its range and capacity limits, and rejoins (rendezvous with) the heavy vehicle at a downstream customer node.
3. **Interactive Web Visualizer (`web/`)** — A static web application designed for [pauldeng.me](https://pauldeng.me) featuring map rendering, Gantt synchronization timelines, vehicle playback animation, and an in-browser live GA engine.

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
  - **Memetic Refinement (`gavrptw.core.two_opt`)**: 2-opt local search operator that eliminates crossing route edges and refines sub-route distance.
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

1. **Python 3.12+ Modern Stack**:
   - Modernized from legacy Python 2.7. All `print` calls use `print(...)`, `xrange` replaced with `range`, and packaging is managed via `pyproject.toml` and `uv`.
   - Run tests anytime with `pytest -v`.

2. **Module Filenames & Compatibility**:
   - `gatspmv/mvcore.py` is lowercase, and `gatspmv/__init__.py` aliases `mvCore = mvcore` for complete backwards compatibility across macOS, Linux, and Windows.

3. **`"deport"` Spelling in JSON & Code**:
   - The depot key is spelled `"deport"` across `gavrptw/utils.py`, `gavrptw/core.py`, and all generated `.json` files. Do **not** change `"deport"` to `"depot"` in code without updating `utils.py` and regenerating all JSON files.

4. **Dedicated Stage 2 Mutation (`mutMVRendezvous`)**:
   - Resolved the previous limitation where `mutPb = 0` was required. The new `mutMVRendezvous` operator mutates departure and reunion rendezvous points without perturbing the compound chromosome structure `[[L_1], ..., [H]]`.

5. **Memetic 2-Opt Refinement**:
   - `gavrptw.core.two_opt_subroute` and `two_opt` are available for untangling sub-route edges.

6. **Web Visualizer (`web/`)**:
   - A static web app located in `web/` (`index.html`, `style.css`, `app.js`, `data/instances.js`) with canvas rendering, Gantt timeline, vehicle playback animation, and in-browser GA solver. Ready to host directly on `pauldeng.me`.

---

## 6. Common Workflows

Run all commands from the repository root (`/Users/pauldeng/Documents/code/py-ga-VRPTW`):

```bash
# 1. Run automated test suite
pytest -v

# 2. Convert text benchmark instances to JSON
python text2json.py            # data/text/*.txt -> data/json/*.json
python text2json_customize.py  # data/text_customize/*.txt -> data/json_customize/*.json

# 3. Run Stage 1: Heavy-vehicle VRPTW GA (outputs sub-routes and CSV stats to results/)
python instance_run_scripts/sample_P-nX-X.py

# 4. Run Stage 2: Movement Synchronization GA on Stage 1 sub-routes
# (Paste the bestVRP sub-routes from Stage 1 into bestVRP in sample_P-nX-X-VRPMS.py)
python instance_run_scripts/sample_P-nX-X-VRPMS.py

# 5. Launch interactive web visualizer locally
python server.py
# Open http://localhost:8080 (or /health for health check)

# 6. Production Railway Deployment
# Railway project: drone-delivery
# Live URL: https://drone-delivery-production.up.railway.app
# Deployment managed via Dockerfile, railway.toml, Procfile, and Railway CLI:
railway up --detach
```

