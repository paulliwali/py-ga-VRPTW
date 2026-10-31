# Drone Delivery (`py-ga-VRPMV`)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-0B0D0E?style=flat-square&logo=railway)](https://drone-delivery-production.up.railway.app)

A two-stage Genetic Algorithm (GA) solution for coordinated **Drone Delivery** and vehicle routing with movement synchronization (VRPMV / VRPMS). Heavy vehicles (trucks) team up with light aerial resources (drones) that launch from customer locations, deliver to interior customer clusters, and rendezvous with trucks downstream.

- **Interactive Web Visualizer**: Hosted live at [https://drone-delivery-production.up.railway.app](https://drone-delivery-production.up.railway.app)
- Implemented a fix to the Partially Matched Crossover (PMX) function for 1-indexed customer IDs
- Implemented an elitist selection process to improve GA convergence
- Enabled multi-processing with `DEAP` using Python's `multiprocessing` module
- Solved VRP with movement synchronization involving the coordinated teamwork of **heavy** (e.g., truck) and **light** (e.g., drone/courier) resources

## Reference to py-ga-VRPTW

- See iRB-Lab's [repository](https://github.com/iRB-Lab/py-ga-VRPTW)

## Contents for VRPMV

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Data Preparation](#data-preparation)
  - [Running the Solver](#running-the-solver)
- [Modifications to the GA Implementation for VRPTW](#modifications-to-the-ga-implementation-for-vrptw)
  - [Selection: Elite Selection](#selection-elite-selection)
  - [Partially Matched Crossover Method](#partially-matched-crossover-method)
  - [Multiprocessing](#multiprocessing)
- [GA Implementation of Movement Synchronization](#ga-implementation-of-movement-synchronization)
  - [Individual (Chromosomes)](#individual-chromosomes)
  - [Individual with Movement Synchronization (Chromosomes)](#individual-with-movement-synchronization-chromosomes)
    - [Decode Individual with Movement Synchronization](#decode-individual-with-movement-synchronization)
    - [Create Individuals with Movement Synchronization](#create-individuals-with-movement-synchronization)
  - [Evaluation of Individuals with Movement Synchronization](#evaluation-of-individuals-with-movement-synchronization)
  - [Crossover of Individuals with Movement Synchronization](#crossover-of-individuals-with-movement-synchronization)
- [File Structure](#file-structure)
- [Further Reading](#further-reading)
- [References](#references)

## Getting Started

### Prerequisites

This project is written in **Python 2.7**. Install the required packages via `pip`:

```bash
pip install -r requirements.txt
```

Required libraries:
- `deap>=1.0.2`
- `numpy>=1.13`
- `pandas>=0.20`
- `matplotlib>=2.0`

### Data Preparation

Convert raw Solomon/custom `.txt` benchmark files into `.json` format (which precomputes the Euclidean distance matrix):

```bash
# Convert standard Solomon benchmark instances (data/text/*.txt -> data/json/*.json)
python text2json.py

# Convert customized instances (data/text_customize/*.txt -> data/json_customize/*.json)
python text2json_customize.py
```

### Running the Solver

The VRPMV solver operates in **two stages** using scripts in `instance_run_scripts/`:

1. **Stage 1 — Solve VRPTW for Heavy Vehicle Sub-Routes**:
   ```bash
   python instance_run_scripts/sample_P-nX-X.py
   ```
   This evolves a permutation of all customers, splits it into feasible heavy-vehicle sub-routes (`ind2route`), prints the best route and cost, and optionally exports generation statistics to `results/`.

2. **Stage 2 — Optimize Movement Synchronization (Heavy + Light Resources)**:
   Copy the resulting sub-routes (`bestVRP`) from Stage 1 into `instance_run_scripts/sample_P-nX-X-VRPMS.py` and run:
   ```bash
   python instance_run_scripts/sample_P-nX-X-VRPMS.py
   ```
   For each sub-route, this clusters light-deliverable customers and evolves the departure and reunion (rendezvous) points between the light and heavy resources.

3. **Plot Fitness Curves**:
   ```bash
   python plotResults.py
   ```
   Generates `.png` fitness progression plots in `results/` for all exported `.csv` files.

## Modifications to the GA Implementation for VRPTW

Several modifications are made to improve the performance of iRB-Lab's GA implementation.

### Selection: Elite Selection

Instead of solely relying on the roulette selection process to pick the individuals for crossover and mutation, select one elite `individual` to keep untouched past the crossover and mutation step, select the top 10% of the current generation, and roulette-select the remaining 90%. The selection methods use built-in `deap` tools:

```python
elite = deap.tools.selBest(individuals, 1)
offspring = deap.tools.selBest(individuals, int(numpy.ceil(len(individuals) * 0.1)))
offspringRoulette = deap.tools.selRoulette(individuals, int(numpy.floor(len(individuals) * 0.9)) - 1)
```

### Partially Matched Crossover Method

The partially matched crossover (PMX) method originally coded is based on a paper by Goldberg [(1985)][goldberg-1985]. The original implementation was not working as intended, so it was replaced with the built-in version from `deap` with an index offset modification (`-1`) to account for 1-indexed customer IDs (since `0` is reserved for the depot).

PMX is suited for problems where the optimal values and locations of the chromosomes matter. PMX works by randomly selecting a range of customers to swap between the routes. As each customer is swapped between the two routes, the duplicates are also swapped. For example, if there are two `individuals`:

```python
A = [9, 8, 4, 5, 6, 7, 1, 3, 2, 10]
B = [8, 7, 1, 2, 3, 10, 9, 5, 4, 6]
```

PMX first randomly chooses a range called the "mapping section":

```python
A = [9, 8, 4, 5, 6, 7, 1, 3, 2, 10]
             ^        ^
B = [8, 7, 1, 2, 3, 10, 9, 5, 4, 6]
             ^         ^
```

Then the first pair (`5` - `2`) is swapped, followed by a check to see where the duplicated customers are and swapping them accordingly:

```python
A_swapped = [9, 8, 4, 2, 6, 7, 1, 3, 5, 10]
                     ^        ^
B_swapped = [8, 7, 1, 5, 3, 10, 9, 2, 4, 6]
                     ^         ^
```

Then it moves to the next pair (`6` - `3`) until all the pairs are exhausted in the mapping section:

```python
A_swapped = [9, 8, 4, 2, 3, 10, 1, 6, 5, 7]
                     ^         ^
B_swapped = [8, 10, 1, 5, 6, 7, 9, 2, 4, 3]
                      ^        ^
```

### Multiprocessing

Python is by default locked from using multiple processors on a given machine due to the Global Interpreter Lock (GIL). In order to circumvent this, the [`multiprocessing` module][multiprocessing] is used. However, to take advantage of this with `DEAP`, the `creator` classes and `toolbox` population initializers must be exposed in the module's global scope.

There are ongoing discussions and work done on this issue. For more information, see [DEAP PR #76](https://github.com/DEAP/deap/pull/76).

## GA Implementation of Movement Synchronization

### Individual (Chromosomes)

Recall the `individual` used in the GA process from the `py-ga-VRPTW` stage is coded in the following manner. If the sub-routes of the individual are the following:

```python
Sub-route 1: 0 - 5 - 3 - 2 - 0
Sub-route 2: 0 - 7 - 1 - 6 - 9 - 0
Sub-route 3: 0 - 8 - 4 - 0
```

then the `individual` is coded as a flat permutation list of customer IDs:

```python
individual = [5, 3, 2, 7, 1, 6, 9, 8, 4]
```

The process (`ind2route`) that decodes the `individual` into the sub-route representation uses a split procedure based on the capacity constraint of the vehicle and the depot due time. Each sub-route is split at the point where the addition of another customer would violate either constraint.

### Individual with Movement Synchronization (Chromosomes)

For the purpose of representing both light and heavy resource sub-routes, a new representation is created based on the best individual from the `py-ga-VRPTW` stage. Using the same example as above, suppose this individual is decoded into two sub-routes served by heavy resources:

```python
bestIndividual = [5, 3, 2, 7, 1, 6, 9, 8, 4]
```

which is decoded into two sub-routes served by heavy resources:

```python
heavy-sub-route 1: 0 - 5 - 3 - 2 - 7 - 1 - 6 - 9 - 0
heavy-sub-route 2: 0 - 8 - 4 - 0
```

#### Decode Individual with Movement Synchronization

```python
splitLightCustomers(instance, individual, lightRange=100, lightCapacity=50)
```

This method (`gatspmv/mvCore.py`) selects interior customers in a `heavy-sub-route` based on their inter-customer distances and demands, greedily clustering them into customer groups that the light resource can serve.

##### Parameters

- `instance` – A problem instance dict object loaded from a JSON file.
- `individual` – A heavy-resource sub-route (list of customer IDs) from Stage 1.
- `lightRange` – Maximum distance the light resource is able to travel in a single sortie (including departure and reunion legs).
- `lightCapacity` – Maximum total demand the light resource is able to carry per sortie.

##### Returns

- A binary list indicating which customers in the sub-route the light resource will deliver to:

```python
light-list-sub-route-1 = [0, 0, 1, 1, 0, 0]
light-list-sub-route-2 = [0, 0]
```

This example indicates that the light resource is assigned to deliver to customers `7` and `1` in sub-route 1 and makes no deliveries in sub-route 2.

#### Create Individuals with Movement Synchronization

Since the `individual` created for the `py-ga-VRPTW` stage is a flat list of customer IDs, its initialization uses the standard `creator()` and `initIterate` tools from `deap`.

The initialization for `individual-mv` (with movement synchronization) uses a custom function in `gatspmv/mvCore.py`:

```python
initMVIndividuals(icls, lightList, individual)
```

This method creates a custom `individual` structured as `[[L_1], [L_2], ..., [H]]`, where:
- Each `[L_k] = [depart_customer, light_customer_1, ..., rejoin_customer]` represents a light resource sub-route (starting at a randomly chosen heavy-route customer before the cluster and rejoining at a randomly chosen heavy-route customer after the cluster).
- `[H]` (always the last element `individual[-1]`) is the list of remaining customers served directly by the heavy resource.

##### Parameters

- `icls` – The DEAP class representing the `individual`.
- `lightList` – The binary list from `splitLightCustomers` indicating which customers are light-deliverable in the sub-route.
- `individual` – A sub-route from the best individual of the `py-ga-VRPTW` stage.

##### Returns

- A properly classed `individual` (`[[L_1], ..., [H]]`) ready to be used with `deap` operators and algorithms.

### Evaluation of Individuals with Movement Synchronization

```python
evalTSPMS(MVindividual, instance, unitCost=1.0, waitCost=0, delayCost=0, speed=1,
          lightUnitCost=1.0, lightWaitCost=0, lightDelayCost=0, lightSpeed=1)
```

Takes in the customized `MVindividual` and the associated cost/speed variables as parameters and calculates the total cost of the synchronized route. It incorporates synchronization waiting costs at rendezvous nodes accordingly: if the light resource arrives at the rendezvous customer before the heavy resource, a wait cost is incurred for the time the light resource spends waiting (`lightWaitCost`), and vice versa (`waitCost`).

#### Parameters

- `MVindividual` – A customized `individual` (`[[L_1], ..., [H]]`) representing a sub-route served by both light and heavy resources.
- `instance` – A problem instance dict object loaded from a JSON file.
- `unitCost` – Cost per unit distance for the heavy resource.
- `waitCost` – Cost per unit time when the heavy resource has to wait (either for a customer's `ready_time` window or for the light resource to rejoin).
- `delayCost` – Cost per unit time when the heavy resource arrives after a customer's `due_time`.
- `speed` – Travel time multiplier per unit distance for the heavy resource.
- `lightUnitCost` – Cost per unit distance for the light resource.
- `lightWaitCost` – Cost per unit time when the light resource has to wait (either for a customer's `ready_time` window or for the heavy resource to arrive at the rendezvous point).
- `lightDelayCost` – Cost per unit time when the light resource arrives after a customer's `due_time`.
- `lightSpeed` – Travel time multiplier per unit distance for the light resource.

#### Returns

- A 1-tuple `(fitness,)` containing the inverse total cost `1 / totalCost` of the `MVindividual`.

### Crossover of Individuals with Movement Synchronization

```python
cxSinglePointSwap(ind1, ind2)
```

Executes a single-point crossover between the rendezvous customers of paired light sub-routes of two `MVindividual` chromosomes. For each light sub-route, it swaps either the departure customer (`subRoute[0]`) or the reunion customer (`subRoute[-1]`) with 50% probability.

#### Parameters

- `ind1`, `ind2` – Two customized `MVindividual` chromosomes representing routes with both light and heavy resources.

#### Returns

- A tuple `(ind1, ind2)` of two individuals with swapped rendezvous points for their light resource sub-routes.

## File Structure

```text
├── data/
│   ├── json/
│   │   └── <Solomon instance>.json
│   ├── json_customize/
│   │   └── <Customized instance>.json
│   ├── plot/
│   │   └── <Route plot>.png
│   ├── text/
│   │   └── <Solomon instance>.txt
│   └── text_customize/
│       └── <Customized instance>.txt
├── results/
│   └── <Exported CSVs & fitness plots>
├── gatspmv/
│   ├── __init__.py
│   └── mvCore.py
├── gavrptw/
│   ├── __init__.py
│   ├── core.py
│   └── utils.py
├── instance_run_scripts/
│   ├── __init__.py
│   ├── sample_A-n32-k5.py
│   ├── sample_A-n32-k5-VRPMV.py
│   ├── sample_P-n10-k2.py
│   ├── sample_P-n10-k2-VRPMV.py
│   ├── sample_P-nX-X.py
│   └── sample_P-nX-X-VRPMS.py
├── text2json.py
├── text2json_customize.py
├── plotResults.py
├── ind2route.py
├── ga-spec.txt
├── requirements.txt
├── AGENT.md
├── README.md
├── LICENSE
└── .gitignore
```

## Further Reading

**Distributed Evolutionary Algorithms in Python (DEAP)**

- [Docs][deap-docs]
- [GitHub][deap-github]
- [PyPI][deap-pypi]

## References

1. [Solomon's VRPTW Benchmark Problems][solomon]
2. [100 Customers Instance Definitions][100-customers]
3. [Distributed Evolutionary Algorithms in Python (DEAP)][deap-pypi]

## License

[MIT License][license]

[repository]: https://github.com/paulliwali/py-ga-VRPTW "paulliwali/py-ga-VRPTW"
[license]: https://github.com/paulliwali/py-ga-VRPTW/blob/master/LICENSE "License"

[multiprocessing]: https://docs.python.org/2/library/multiprocessing.html "multiprocessing"

[solomon]: http://web.cba.neu.edu/~msolomon/problems.htm "Solomon's VRPTW Benchmark Problems"
[100-customers]: http://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/100-customers/ "100 Customers Instance Definitions"
[100-customers-zip]: http://www.sintef.no/globalassets/project/top/vrptw/solomon/solomon-100.zip "100 Customers Instance Definitions (Zip)"

[deap-docs]: http://deap.readthedocs.org/ "Distributed Evolutionary Algorithms in Python (DEAP) Docs"
[deap-github]: https://github.com/deap/deap/ "Distributed Evolutionary Algorithms in Python (DEAP) GitHub"
[deap-pypi]: https://pypi.python.org/pypi/deap/ "Distributed Evolutionary Algorithms in Python (DEAP) PyPI"

[goldberg-1985]: https://books.google.ca/books?hl=en&lr=&id=lI17AgAAQBAJ&oi=fnd&pg=PA154&dq=Alleles,+loci,+and+the+traveling+salesman+problem&ots=0LkXa9L20z&sig=Q7f4TPgLODK_h9uSF0dLUvkgn5M#v=onepage&q=Alleles%2C%20loci%2C%20and%20the%20traveling%20salesman%20problem&f=false "Alleles Loci and the Traveling Salesman Problem"