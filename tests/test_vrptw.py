# -*- coding: utf-8 -*-
"""Tests for VRPTW core algorithms and genetic operators."""

import json
import os
import pytest
from gavrptw.core import ind2route, evalVRPTW, cxPartialyMatched, mutInverseIndexes
from gavrptw import BASE_DIR


@pytest.fixture
def instance_a_n32_k5():
    json_path = os.path.join(BASE_DIR, 'data', 'json_customize', 'A-n32-k5.json')
    with open(json_path, 'r') as f:
        return json.load(f)


def test_ind2route_capacity_and_split(instance_a_n32_k5):
    # Chromosome from ga-spec.txt line 78
    individual = [5, 10, 15, 22, 9, 11, 28, 18, 6, 3, 2, 17, 19, 31, 21, 13, 23, 4, 8, 29, 27, 14, 24, 30, 16, 12, 1, 7, 26, 25, 20]
    routes = ind2route(individual, instance_a_n32_k5, speed=1.0)

    # Must produce exactly 5 sub-routes
    assert len(routes) == 5

    # Every customer from 1 to 31 must be visited exactly once
    flattened = [cust for sub in routes for cust in sub]
    assert sorted(flattened) == list(range(1, 32))

    # Vehicle capacity constraint must not be violated
    max_cap = instance_a_n32_k5['vehicle_capacity']
    for sub in routes:
        load = sum(instance_a_n32_k5[f'customer_{c}']['demand'] for c in sub)
        assert load <= max_cap


def test_evalVRPTW_benchmark_match(instance_a_n32_k5):
    # Validated benchmark output from ga-spec.txt
    individual = [5, 10, 15, 22, 9, 11, 28, 18, 6, 3, 2, 17, 19, 31, 21, 13, 23, 4, 8, 29, 27, 14, 24, 30, 16, 12, 1, 7, 26, 25, 20]
    fitness, = evalVRPTW(individual, instance_a_n32_k5, unitCost=1.0, waitCost=0.0, delayCost=0.0, speed=1.0)
    cost = 1.0 / fitness

    # Matches ga-spec.txt line 78 (bestCost: 995.5, meanFitness: ~0.00100454)
    assert pytest.approx(cost, rel=1e-3) == 995.48
    assert pytest.approx(fitness, rel=1e-3) == 0.00100454


def test_pmx_crossover_permutation_integrity():
    ind1 = list(range(1, 21))
    ind2 = list(reversed(range(1, 21)))

    for _ in range(50):
        c1 = ind1[:]
        c2 = ind2[:]
        cxPartialyMatched(c1, c2)
        assert sorted(c1) == list(range(1, 21)), "c1 is no longer a valid permutation!"
        assert sorted(c2) == list(range(1, 21)), "c2 is no longer a valid permutation!"


def test_mut_inverse_indexes():
    ind = list(range(1, 21))
    mutant, = mutInverseIndexes(ind[:])
    assert sorted(mutant) == list(range(1, 21))
    assert len(mutant) == 20


def test_two_opt(instance_a_n32_k5):
    from gavrptw.core import two_opt
    individual = [5, 10, 15, 22, 9, 11, 28, 18, 6, 3, 2, 17, 19, 31, 21, 13, 23, 4, 8, 29, 27, 14, 24, 30, 16, 12, 1, 7, 26, 25, 20]
    fit_before, = evalVRPTW(individual, instance_a_n32_k5)
    opt_individual = two_opt(individual, instance_a_n32_k5)
    fit_after, = evalVRPTW(opt_individual, instance_a_n32_k5)

    # 2-opt must preserve all customer IDs
    assert sorted(opt_individual) == list(range(1, 32))
    # 2-opt cost must be equal or lower than unoptimized
    assert (1.0 / fit_after) <= (1.0 / fit_before) + 1e-6

