# -*- coding: utf-8 -*-
# ind2route.py
# Test code to run the ind2route function from core
# Also used to test the crossover function PMX

import os
import random
from json import load
from gavrptw.core import ind2routeMS, printRoute, evalVRPMS
from deap import base, creator, tools

instName = 'P-n10-0'

random.seed(64)


def cxPartialyMatched(ind1, ind2):
    size = min(len(ind1), len(ind2))
    p1, p2 = [0] * size, [0] * size

    for i in range(size):
        p1[ind1[i] - 1] = i
        p2[ind2[i] - 1] = i

    cxpoint1 = 7
    cxpoint2 = 9
    if cxpoint2 >= cxpoint1:
        cxpoint2 += 1
    else:
        cxpoint1, cxpoint2 = cxpoint2, cxpoint1

    for i in range(cxpoint1, cxpoint2):
        temp1 = ind1[i]
        temp2 = ind2[i]
        ind1[i], ind1[p1[temp2 - 1]] = temp2, temp1
        ind2[i], ind2[p2[temp1 - 1]] = temp1, temp2
        p1[temp1 - 1], p1[temp2 - 1] = p1[temp2 - 1], p1[temp1 - 1]
        p2[temp1 - 1], p2[temp2 - 1] = p2[temp2 - 1], p2[temp1 - 1]

    return ind1, ind2


jsonDataDir = os.path.join('data', 'json_customize')
jsonFile = os.path.join(jsonDataDir, '%s.json' % instName)
with open(jsonFile) as f:
    instance = load(f)

creator.create('FitnessMax', base.Fitness, weights=(1.0,))
creator.create('Individual', list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()
IND_SIZE = 10

toolbox.register('indexes', random.sample, range(1, IND_SIZE + 1), IND_SIZE)
toolbox.register('individual', tools.initIterate, creator.Individual, toolbox.indexes)
toolbox.register('population', tools.initRepeat, list, toolbox.individual)
toolbox.register('mate', cxPartialyMatched)
toolbox.register('select', tools.selRoulette)
toolbox.register('evaluate', evalVRPMS, instance=instance, unitCost=1.0, lightUnitCost=1.0)

pop = toolbox.population(n=2)
print(pop)

fitnesses = list(map(toolbox.evaluate, pop))
for ind, fit in zip(pop, fitnesses):
    ind.fitness.values = fit
print('  Evaluated %d individuals' % len(pop))

offspring = pop
for child1, child2 in zip(offspring[::2], offspring[1::2]):
    toolbox.mate(child1, child2)

print(offspring)
