# -*- coding: utf-8 -*-
"""Tests for Movement Synchronization (VRPMV / VRPMS) core algorithms."""

import json
import os
import pytest
from gatspmv.mvcore import (
    splitLightCustomers,
    initMVIndividuals,
    evalTSPMS,
    cxSinglePointSwap,
)
from gavrptw.utils import visualizeRoutes
from gavrptw import BASE_DIR


@pytest.fixture
def instance_a_n32_k5():
    json_path = os.path.join(BASE_DIR, 'data', 'json_customize', 'A-n32-k5.json')
    with open(json_path, 'r') as f:
        return json.load(f)


def test_split_light_customers(instance_a_n32_k5):
    route_1 = [8, 11, 4, 22, 29, 23, 30, 14]
    mask_1 = splitLightCustomers(instance_a_n32_k5, route_1, lightRange=100, lightCapacity=50)
    # Customers 4 and 22 should be flagged for light delivery
    assert mask_1 == [0, 0, 1, 1, 0, 0, 0, 0]

    route_4 = [19, 17, 31, 21, 13, 28, 18]
    mask_4 = splitLightCustomers(instance_a_n32_k5, route_4, lightRange=100, lightCapacity=50)
    # Customers 31, 21, 13 should be flagged for light delivery
    assert mask_4 == [0, 0, 1, 1, 1, 0, 0]


def test_init_mv_individuals(instance_a_n32_k5):
    route_1 = [8, 11, 4, 22, 29, 23, 30, 14]
    mask_1 = splitLightCustomers(instance_a_n32_k5, route_1, lightRange=100, lightCapacity=50)

    class DummyInd(list):
        pass

    mv_ind = initMVIndividuals(DummyInd, mask_1, route_1)
    # Chromosome must have [[L1], [H]]
    assert len(mv_ind) == 2
    light_sub = mv_ind[0]
    heavy_sub = mv_ind[1]

    # Light sub-route has departure, 4, 22, reunion
    assert light_sub[1:-1] == [4, 22]
    assert light_sub[0] in [8, 11]  # from preceding heavy segment
    assert light_sub[-1] in [29, 23, 30, 14]  # from succeeding heavy segment
    assert heavy_sub == [8, 11, 29, 23, 30, 14]


def test_eval_tspms_total_cost(instance_a_n32_k5):
    # Validated mixed route from sample_A-n32-k5-VRPMV.py:
    # route 1: [[11, 4, 22, 29], [8, 11, 29, 23, 30, 14]]
    # route 2: [[12, 16, 5, 25, 10, 20]]
    # route 3: [[15, 9, 6, 3, 1, 27, 26]]
    # route 4: [[19, 31, 21, 13, 28], [19, 17, 28, 18]]
    # route 5: [[24, 2, 7]]
    all_subroutes = [
        [[11, 4, 22, 29], [8, 11, 29, 23, 30, 14]],
        [[12, 16, 5, 25, 10, 20]],
        [[15, 9, 6, 3, 1, 27, 26]],
        [[19, 31, 21, 13, 28], [19, 17, 28, 18]],
        [[24, 2, 7]],
    ]

    total_cost = 0.0
    for sub in all_subroutes:
        fit, = evalTSPMS(sub, instance_a_n32_k5, unitCost=1.0, waitCost=0.0, delayCost=0.0, speed=1.0,
                         lightUnitCost=1.0, lightWaitCost=0.0, lightDelayCost=0.0, lightSpeed=1.0)
        total_cost += (1.0 / fit)

    assert pytest.approx(total_cost, rel=1e-3) == 1498.00


def test_cx_single_point_swap():
    ind1 = [[11, 4, 22, 29], [8, 11, 29, 23, 30, 14]]
    ind2 = [[8, 4, 22, 23], [8, 11, 29, 23, 30, 14]]

    c1 = [sub[:] for sub in ind1]
    c2 = [sub[:] for sub in ind2]

    cxSinglePointSwap(c1, c2)
    # The light route customers [4, 22] remain unchanged; only rendezvous nodes [0] or [-1] may swap
    assert c1[0][1:-1] == [4, 22]
    assert c2[0][1:-1] == [4, 22]


def test_mut_mv_rendezvous():
    from gatspmv.mvcore import mutMVRendezvous
    subRoute = [8, 11, 4, 22, 29, 23, 30, 14]
    lightList = [0, 0, 1, 1, 0, 0, 0, 0]
    ind = [[11, 4, 22, 29], [8, 11, 29, 23, 30, 14]]

    mutated, = mutMVRendezvous([sub[:] for sub in ind], lightList, subRoute, indpb=1.0)
    # Interior light customers [4, 22] must never change
    assert mutated[0][1:-1] == [4, 22]
    # Departure node must be in preceding heavy segment
    assert mutated[0][0] in [8, 11]
    # Reunion node must be in succeeding heavy segment
    assert mutated[0][-1] in [29, 23, 30, 14]
    # Heavy route must remain intact
    assert mutated[1] == [8, 11, 29, 23, 30, 14]



def test_visualize_routes(instance_a_n32_k5, tmp_path):
    subroutes = [
        [[11, 4, 22, 29], [8, 11, 29, 23, 30, 14]],
        [[12, 16, 5, 25, 10, 20]],
    ]
    # Test visualization for mixed light/heavy resources
    visualizeRoutes("test_vrpmv_plot", instance_a_n32_k5, subroutes, containsLightResource=True)
    plot_file = os.path.join(BASE_DIR, 'data', 'plot', 'test_vrpmv_plot.png')
    assert os.path.exists(plot_file)
    if os.path.exists(plot_file):
        os.remove(plot_file)
