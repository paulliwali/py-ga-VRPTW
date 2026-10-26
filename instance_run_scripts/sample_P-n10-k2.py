# -*- coding: utf-8 -*-
# sample_P-n10-k2.py
# Used to test the GA setup against the MIP solution

import os
import sys
import random
import numpy
from json import load
from csv import DictWriter
from deap import base, creator, tools
from timeit import default_timer as timer
import multiprocessing

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gavrptw import core, utils

# Create Fitness and Individual Classes
creator.create('FitnessMax', base.Fitness, weights=(1.0,))
creator.create('Individual', list, fitness=creator.FitnessMax)
toolbox = base.Toolbox()

IND_SIZE = 10
toolbox.register('indexes', random.sample, range(1, IND_SIZE + 1), IND_SIZE)
toolbox.register('individual', tools.initIterate, creator.Individual, toolbox.indexes)
toolbox.register('population', tools.initRepeat, list, toolbox.individual)


def gaVRPTW(pop, instName, unitCost, waitCost, delayCost, indSize, popSize, cxPb, mutPb, NGen, exportCSV=False, customizeData=False, speed=1.0):
    if customizeData:
        jsonDataDir = os.path.join('data', 'json_customize')
    else:
        jsonDataDir = os.path.join('data', 'json')
    jsonFile = os.path.join(jsonDataDir, '%s.json' % instName)
    with open(jsonFile) as f:
        instance = load(f)

    toolbox.register('evaluate', core.evalVRPTW, instance=instance, unitCost=unitCost, waitCost=waitCost, delayCost=delayCost, speed=speed)
    toolbox.register('select', tools.selRoulette)
    toolbox.register('mate', core.cxPartialyMatched)
    toolbox.register('mutate', core.mutInverseIndexes)

    csvData = []
    print('Start of evolution')
    fitnesses = list(toolbox.map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    for g in range(NGen):
        print('-- Generation %d --' % g)
        elite = tools.selBest(pop, 1)
        offspring = tools.selBest(pop, int(numpy.ceil(len(pop) * 0.1)))
        offspringRoulette = toolbox.select(pop, int(numpy.floor(len(pop) * 0.9)) - 1)
        offspring.extend(offspringRoulette)
        offspring = list(toolbox.map(toolbox.clone, offspring))

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < cxPb:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
        for mutant in offspring:
            if random.random() < mutPb:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        invalidInd = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = list(toolbox.map(toolbox.evaluate, invalidInd))
        for ind, fit in zip(invalidInd, fitnesses):
            ind.fitness.values = fit

        offspring.extend(elite)
        pop[:] = offspring

        fits = [ind.fitness.values[0] for ind in pop]
        length = len(pop)
        mean = sum(fits) / length
        sum2 = sum(x * x for x in fits)
        std = abs(sum2 / length - mean ** 2) ** 0.5

        if exportCSV:
            csvRow = {
                'generation': g,
                'evaluated_individuals': len(invalidInd),
                'min_fitness': min(fits),
                'max_fitness': max(fits),
                'avg_fitness': mean,
                'std_fitness': std,
                'avg_cost': 1 / mean,
            }
            csvData.append(csvRow)

    print('-- End of (successful) evolution --')
    bestInd = tools.selBest(pop, 1)[0]
    print('Best individual: %s' % bestInd)
    print('Fitness: %s' % bestInd.fitness.values[0])
    core.printRoute(core.ind2route(bestInd, instance, speed=speed))
    print('Total cost: %s' % (1 / bestInd.fitness.values[0]))

    if exportCSV:
        csvFilename = '%s_uC%s_wC%s_dC%s_iS%s_pS%s_cP%s_mP%s_nG%s.csv' % (instName, unitCost, waitCost, delayCost, indSize, popSize, cxPb, mutPb, NGen)
        csvPathname = os.path.join('results', csvFilename)
        print('Write to file: %s' % csvPathname)
        utils.makeDirsForFile(pathname=csvPathname)
        if not utils.exist(pathname=csvPathname, overwrite=True):
            with open(csvPathname, 'w', newline='') as f:
                fieldnames = ['generation', 'evaluated_individuals', 'min_fitness', 'max_fitness', 'avg_fitness', 'std_fitness', 'avg_cost']
                writer = DictWriter(f, fieldnames=fieldnames, dialect='excel')
                writer.writeheader()
                for csvRow in csvData:
                    writer.writerow(csvRow)
    return core.ind2route(bestInd, instance, speed=speed)


def main():
    random.seed(64)
    instName = 'P-n10-k2'
    unitCost = 10.0
    waitCost = 0.0
    delayCost = 0.0
    speed = 1.0

    indSize = 10
    popSize = 200
    cxPb = 0.9
    mutPb = 0.05
    NGen = 50

    exportCSV = True
    customizeData = True

    pop = toolbox.population(n=popSize)

    gaVRPTW(
        pop=pop,
        instName=instName,
        unitCost=unitCost,
        waitCost=waitCost,
        delayCost=delayCost,
        speed=speed,
        indSize=indSize,
        popSize=popSize,
        cxPb=cxPb,
        mutPb=mutPb,
        NGen=NGen,
        exportCSV=exportCSV,
        customizeData=customizeData
    )


if __name__ == '__main__':
    pool = multiprocessing.Pool()
    toolbox.register('map', pool.map)
    tic = timer()
    main()
    print('Computing Time: %s' % (timer() - tic))
    pool.close()