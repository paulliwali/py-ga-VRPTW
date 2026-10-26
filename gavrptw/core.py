# -*- coding: utf-8 -*-

import os
import random
import numpy
from json import load
from csv import DictWriter
from deap import base, creator, tools
from . import BASE_DIR
from .utils import makeDirsForFile, exist


def printRoute(route, merge=False, twoResources=False):
    routeStr = '0'
    subRouteCount = 0
    for subRoute in route:
        subRouteCount += 1
        subSubRouteCount = 0
        subRouteStr = '0'
        heavyRouteStr = '0'
        lightRouteStr = ''
        if twoResources:
            for subSubRoute in subRoute:
                subSubRouteCount += 1
                for customerID in subSubRoute:
                    # A lightSubRoute
                    if subSubRouteCount % 3 == 2:
                        lightRouteStr = lightRouteStr + ' - ' + str(customerID)
                        subRouteStr = subRouteStr + ' - ' + str(customerID)
                        routeStr = routeStr + ' - ' + str(customerID)
                    # A heavySubRoute
                    elif subSubRouteCount % 3 == 1 or subSubRouteCount % 3 == 0:
                        heavyRouteStr = heavyRouteStr + ' - ' + str(customerID)
                        subRouteStr = subRouteStr + ' - ' + str(customerID)
                        routeStr = routeStr + ' - ' + str(customerID)
                # Replace the lightSubRoute as a 'L' in heavySubRoute
                if subSubRouteCount % 3 == 2:
                    heavyRouteStr = heavyRouteStr + ' - L'
                # Replace the heavySubRoute as a 'H' in heavySubRoute
                elif subSubRouteCount % 3 == 1 or subSubRouteCount % 3 == 0:
                    lightRouteStr = lightRouteStr + ' - H'

            heavyRouteStr = heavyRouteStr + ' - 0'
            subRouteStr = subRouteStr + ' - 0'

            if not merge:
                print('  Vehicle %d\'s route: %s ' % (subRouteCount, subRouteStr))
                print('  Vehicle %d\'s heavy resource route %s ' % (subRouteCount, heavyRouteStr))
                print('  Vehicle %d\'s light resource route %s ' % (subRouteCount, lightRouteStr))

        else:
            for customerID in subRoute:
                subRouteStr = subRouteStr + ' - ' + str(customerID)
                routeStr = routeStr + ' - ' + str(customerID)
            subRouteStr = subRouteStr + ' - 0'
            if not merge:
                print('  Vehicle %d\'s route: %s' % (subRouteCount, subRouteStr))
                routeStr = routeStr + ' - 0'
        if merge:
            print(routeStr)

    return


def ind2route(individual, instance, speed=1.0):
    route = []
    vehicleCapacity = instance['vehicle_capacity']
    deportDueTime = instance['deport']['due_time']
    # Initialize a sub-route
    subRoute = []
    vehicleLoad = 0
    elapsedTime = 0
    lastCustomerID = 0
    for customerID in individual:
        # Update vehicle load
        demand = instance['customer_%d' % customerID]['demand']
        updatedVehicleLoad = vehicleLoad + demand
        # Update elapsed time
        serviceTime = instance['customer_%d' % customerID]['service_time']
        returnTime = instance['distance_matrix'][customerID][0] * speed
        updatedElapsedTime = elapsedTime + (instance['distance_matrix'][lastCustomerID][customerID] * speed) + serviceTime + returnTime
        # Validate vehicle load and elapsed time
        if (updatedVehicleLoad <= vehicleCapacity) and (updatedElapsedTime <= deportDueTime):
            # Add to current sub-route
            subRoute.append(customerID)
            vehicleLoad = updatedVehicleLoad
            elapsedTime = updatedElapsedTime - returnTime
        else:
            # Save current sub-route
            route.append(subRoute)
            # Initialize a new sub-route and add to it
            subRoute = [customerID]
            vehicleLoad = demand
            elapsedTime = (instance['distance_matrix'][0][customerID] * speed) + serviceTime
        # Update last customer ID
        lastCustomerID = customerID
    if subRoute != []:
        # Save current sub-route before return if not empty
        route.append(subRoute)
    return route


def ind2routeMS(individual, instance):
    route = []
    routeWithTwoResources = []
    vehicleCapacity = instance['vehicle_capacity']
    deportDueTime = instance['deport']['due_time']
    lightVehicleCapcity = instance.get('light_vehicle_capacity', 10)
    lightVehicleRange = instance.get('light_vehicle_range', 50)
    # Initialize a sub-route
    subRoute = []
    vehicleLoad = 0
    elapsedTime = 0
    lastCustomerID = 0
    for customerID in individual:
        demand = instance['customer_%d' % customerID]['demand']
        updatedVehicleLoad = vehicleLoad + demand
        serviceTime = instance['customer_%d' % customerID]['service_time']
        returnTime = instance['distance_matrix'][customerID][0]
        updatedElapsedTime = elapsedTime + instance['distance_matrix'][lastCustomerID][customerID] + serviceTime + returnTime
        if (updatedVehicleLoad <= vehicleCapacity) and (updatedElapsedTime <= deportDueTime):
            subRoute.append(customerID)
            vehicleLoad = updatedVehicleLoad
            elapsedTime = updatedElapsedTime - returnTime
        else:
            route.append(subRoute)
            subRoute = [customerID]
            vehicleLoad = demand
            elapsedTime = instance['distance_matrix'][0][customerID] + serviceTime
        lastCustomerID = customerID
    if subRoute != []:
        route.append(subRoute)

    for subroutes in route:
        lightSubRoute = []
        heavySubRoute = []
        subRoute = []
        lightVehicleLoad = 0
        lightTravelRange = 0
        lastCustomerID = 0
        for customerID in subroutes:
            demand = instance['customer_%d' % customerID]['demand']
            updatedLightVehicleLoad = lightVehicleLoad + demand
            travelTime = instance['distance_matrix'][lastCustomerID][customerID]
            updatedLightTravelRange = lightTravelRange + travelTime

            if heavySubRoute == []:
                heavySubRoute.append(customerID)
            elif (updatedLightVehicleLoad <= lightVehicleCapcity) and (updatedLightTravelRange <= lightVehicleRange):
                lightSubRoute.append(customerID)
                lightVehicleLoad = updatedLightVehicleLoad
                lightTravelRange = updatedLightTravelRange
            else:
                if lightSubRoute == []:
                    heavySubRoute.append(customerID)
                else:
                    subRoute.append(heavySubRoute)
                    subRoute.append(lightSubRoute)
                    subRoute.append([customerID])
                    lightSubRoute = []
                    heavySubRoute = []
                    lightTravelRange = 0
                    lightVehicleLoad = 0
            lastCustomerID = customerID

        if lightSubRoute != [] and heavySubRoute != []:
            if subRoute == []:
                subRoute.append(heavySubRoute)
            else:
                subRoute[-1].extend(heavySubRoute)
            subRoute[-1].extend(lightSubRoute)
        elif lightSubRoute == [] and heavySubRoute != []:
            subRoute.append(heavySubRoute)

        routeWithTwoResources.append(subRoute)

    return routeWithTwoResources


def evalVRPTW(individual, instance, unitCost=1.0, waitCost=0, delayCost=0, speed=1):
    route = ind2route(individual, instance, speed)
    totalCost = 0
    for subRoute in route:
        subRouteTimeCost = 0
        subRouteDistance = 0
        elapsedTime = 0
        lastCustomerID = 0
        for customerID in subRoute:
            distance = instance['distance_matrix'][lastCustomerID][customerID] * speed
            subRouteDistance = subRouteDistance + distance
            arrivalTime = elapsedTime + distance
            timeCost = waitCost * max(instance['customer_%d' % customerID]['ready_time'] - arrivalTime, 0) + delayCost * max(arrivalTime - instance['customer_%d' % customerID]['due_time'], 0)
            subRouteTimeCost = subRouteTimeCost + timeCost
            elapsedTime = arrivalTime + instance['customer_%d' % customerID]['service_time']
            lastCustomerID = customerID
        subRouteDistance = subRouteDistance + (instance['distance_matrix'][lastCustomerID][0] * speed)
        subRouteTranCost = unitCost * subRouteDistance
        subRouteCost = subRouteTimeCost + subRouteTranCost
        totalCost = totalCost + subRouteCost
    fitness = 1.0 / totalCost
    return fitness,


def evalVRPMS(individual, instance, unitCost=1.0, waitCost=0, delayCost=0,
              lightUnitCost=1.0, lightWaitCost=0, lightDelayCost=0):
    route = ind2routeMS(individual, instance)
    totalCost = 0
    totalCostTwoResource = 0
    for subRoute in route:
        subRouteTimeCost = 0
        subRouteDistance = 0
        elapsedTime = 0
        lastCustomerID = 0
        subSubRouteCount = 0
        lightSubRouteDistance = 0
        heavySubRouteDistance = 0
        heavyRendezvousDistance = 0
        lightRendezvousDistance = 0

        for subSubRoute in subRoute:
            subSubRouteCount += 1
            lightSubRouteTimeCost = 0
            heavySubRouteTimeCost = 0

            if subSubRouteCount % 3 == 2:
                isLightSubRoute = True
                heavyRendezvousDistance = heavyRendezvousDistance + instance['distance_matrix'][subRoute[subSubRouteCount-2][-1]][subRoute[subSubRouteCount][0]]
                lightRendezvousDistance = lightRendezvousDistance + instance['distance_matrix'][subRoute[subSubRouteCount-1][-1]][subRoute[subSubRouteCount][0]]
            else:
                isLightSubRoute = False
            isHeavySubRoute = not isLightSubRoute

            for customerID in subSubRoute:
                distance = instance['distance_matrix'][lastCustomerID][customerID]
                subRouteDistance = subRouteDistance + distance
                lightSubRouteDistance = lightSubRouteDistance + (distance * isLightSubRoute)
                heavySubRouteDistance = heavySubRouteDistance + (distance * isHeavySubRoute)
                arrivalTime = elapsedTime + distance
                timeCost = waitCost * max(instance['customer_%d' % customerID]['ready_time'] - arrivalTime, 0) + delayCost * max(arrivalTime - instance['customer_%d' % customerID]['due_time'], 0)
                lightTimeCost = (lightWaitCost * max(instance['customer_%d' % customerID]['ready_time'] - arrivalTime, 0) + lightDelayCost * max(arrivalTime - instance['customer_%d' % customerID]['due_time'], 0)) * isLightSubRoute
                subRouteTimeCost = subRouteTimeCost + timeCost
                lightSubRouteTimeCost = lightSubRouteTimeCost + lightTimeCost
                heavySubRouteTimeCost = heavySubRouteTimeCost + timeCost * isHeavySubRoute
                elapsedTime = arrivalTime + instance['customer_%d' % customerID]['service_time']
                lastCustomerID = customerID

        subRouteDistance = subRouteDistance + instance['distance_matrix'][lastCustomerID][0]
        subRouteTranCost = unitCost * subRouteDistance
        lightSubRouteTransCost = lightUnitCost * (lightSubRouteDistance + lightRendezvousDistance)
        heavySubRouteDistance = heavySubRouteDistance + heavyRendezvousDistance + instance['distance_matrix'][lastCustomerID][0]
        heavySubRouteTransCost = unitCost * heavySubRouteDistance
        subRouteCost = subRouteTimeCost + subRouteTranCost
        lightSubRouteCost = lightSubRouteTimeCost + lightSubRouteTransCost
        heavySubRouteCost = heavySubRouteTimeCost + heavySubRouteTransCost
        totalCost = totalCost + subRouteCost
        totalCostTwoResource = totalCostTwoResource + lightSubRouteCost + heavySubRouteCost

    fitness = 1.0 / totalCostTwoResource
    return fitness,


def cxPartialyMatched(ind1, ind2):
    """Executes a partially matched crossover (PMX) on 1-indexed individuals."""
    size = min(len(ind1), len(ind2))
    p1, p2 = [0] * size, [0] * size

    # Initialize the position of each indices in the individuals
    for i in range(size):
        p1[ind1[i] - 1] = i
        p2[ind2[i] - 1] = i
    # Choose crossover points
    cxpoint1 = random.randint(0, size)
    cxpoint2 = random.randint(0, size - 1)
    if cxpoint2 >= cxpoint1:
        cxpoint2 += 1
    else:
        cxpoint1, cxpoint2 = cxpoint2, cxpoint1

    # Apply crossover between cx points
    for i in range(cxpoint1, cxpoint2):
        temp1 = ind1[i]
        temp2 = ind2[i]
        ind1[i], ind1[p1[temp2 - 1]] = temp2, temp1
        ind2[i], ind2[p2[temp1 - 1]] = temp1, temp2
        p1[temp1 - 1], p1[temp2 - 1] = p1[temp2 - 1], p1[temp1 - 1]
        p2[temp1 - 1], p2[temp2 - 1] = p2[temp2 - 1], p2[temp1 - 1]

    return ind1, ind2


def mutInverseIndexes(individual):
    start, stop = sorted(random.sample(range(len(individual)), 2))
    individual = individual[:start] + individual[stop:start - 1:-1] + individual[stop + 1:]
    return individual,


def two_opt_subroute(subroute, dist_matrix):
    """Applies 2-opt local search to a single subroute starting and ending at depot (0)."""
    full_route = [0] + list(subroute) + [0]
    improved = True
    while improved:
        improved = False
        n = len(full_route)
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                curr_dist = dist_matrix[full_route[i - 1]][full_route[i]] + dist_matrix[full_route[j]][full_route[j + 1]]
                new_dist = dist_matrix[full_route[i - 1]][full_route[j]] + dist_matrix[full_route[i]][full_route[j + 1]]
                if new_dist < curr_dist - 1e-6:
                    full_route[i:j + 1] = reversed(full_route[i:j + 1])
                    improved = True
                    break
            if improved:
                break
    return full_route[1:-1]


def two_opt(individual, instance, speed=1.0):
    """Applies 2-opt local search to each sub-route of an individual and re-flattens it."""
    routes = ind2route(individual, instance, speed=speed)
    dist_matrix = instance['distance_matrix']
    opt_routes = [two_opt_subroute(r, dist_matrix) for r in routes]
    return [cust for sub in opt_routes for cust in sub]



def gaVRPTW(instName, unitCost, waitCost, delayCost, indSize, popSize, cxPb, mutPb, NGen, exportCSV=False, customizeData=False, speed=1.0):
    if customizeData:
        jsonDataDir = os.path.join(BASE_DIR, 'data', 'json_customize')
    else:
        jsonDataDir = os.path.join(BASE_DIR, 'data', 'json')
    jsonFile = os.path.join(jsonDataDir, '%s.json' % instName)
    with open(jsonFile) as f:
        instance = load(f)
    creator.create('FitnessMax', base.Fitness, weights=(1.0,))
    creator.create('Individual', list, fitness=creator.FitnessMax)
    toolbox = base.Toolbox()

    toolbox.register('indexes', random.sample, range(1, indSize + 1), indSize)
    toolbox.register('individual', tools.initIterate, creator.Individual, toolbox.indexes)
    toolbox.register('population', tools.initRepeat, list, toolbox.individual)
    toolbox.register('evaluate', evalVRPTW, instance=instance, unitCost=unitCost, waitCost=waitCost, delayCost=delayCost, speed=speed)
    toolbox.register('select', tools.selRoulette)
    toolbox.register('mate', cxPartialyMatched)
    toolbox.register('mutate', mutInverseIndexes)

    pop = toolbox.population(n=popSize)
    csvData = []
    print('Start of evolution')
    fitnesses = list(toolbox.map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    for g in range(NGen):
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
    printRoute(ind2route(bestInd, instance, speed=speed))
    print('Total cost: %s' % (1 / bestInd.fitness.values[0]))

    if exportCSV:
        csvFilename = '%s_uC%s_wC%s_dC%s_iS%s_pS%s_cP%s_mP%s_nG%s.csv' % (instName, unitCost, waitCost, delayCost, indSize, popSize, cxPb, mutPb, NGen)
        csvPathname = os.path.join(BASE_DIR, 'results', csvFilename)
        print('Write to file: %s' % csvPathname)
        makeDirsForFile(pathname=csvPathname)
        if not exist(pathname=csvPathname, overwrite=True):
            with open(csvPathname, 'w', newline='') as f:
                fieldnames = ['generation', 'evaluated_individuals', 'min_fitness', 'max_fitness', 'avg_fitness', 'std_fitness', 'avg_cost']
                writer = DictWriter(f, fieldnames=fieldnames, dialect='excel')
                writer.writeheader()
                for csvRow in csvData:
                    writer.writerow(csvRow)
    return bestInd