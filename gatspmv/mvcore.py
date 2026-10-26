# -*- coding: utf-8 -*-
"""mvcore.py docstring

This module includes functions required for the genetic algorithm
process to solve a travelling salesman problem with movement synchronization (VRPMV / VRPMS).
"""

import os
import random
import numpy
from json import load
from csv import DictWriter
from deap import base, creator, tools


def distanceList(instance, individual):
    # Use the distance matrix and find the distances between all the
    # customers in the TSP tour
    # NOTE: this distance list has depot and first customer, but not the last
    # customer back to depot!
    distance = []
    lastCustomerID = 0
    for customerID in individual:
        distance.append(instance['distance_matrix'][lastCustomerID][customerID])
        lastCustomerID = customerID
    return distance


def demandList(instance, individual):
    # Use the distance matrix and find the demand of all the
    # customers in the TSP tour
    demand = []
    for customerID in individual:
        demand.append(instance['customer_%d' % customerID]['demand'])
    return demand


def culmulativeDistance(instance, individual, startIndex, endIndex):
    # Returns the distance between the start and end index of customers.
    # If the customer is at the beginning or end, includes the depot
    distList = distanceList(instance, individual)

    if startIndex == 0 or endIndex > len(individual):
        distance = 9999999999999999999
    elif endIndex < len(individual):
        distance = sum(distList[startIndex:endIndex+1])
    elif endIndex == len(individual):
        distance = sum(distList[startIndex:endIndex+1])
        distance += instance['distance_matrix'][individual[endIndex-1]][0]
    return distance


def culmulativeDemand(instance, individual, startIndex, endIndex):
    # Returns the total demand of the start and end index of customers.
    dmdList = demandList(instance, individual)
    demand = sum(dmdList[startIndex:endIndex+1])
    return demand


def distanceBetweenCustomers(instance, fromCustomer, toCustomer):
    return instance['distance_matrix'][fromCustomer][toCustomer]


def splitLightCustomers(instance, individual, lightRange=100, lightCapacity=50, verbose=False):
    # The method takes in a TSP tour, the light resource's
    # range and capacity constraint
    # Returns a list indicating customers that the light resource
    # is able to deliver to - [0, 0, 1, 1, 0, 0, 1, 1, 0, 0]
    # The range will include the rendezvous points
    # The capacity does not include the rendezvous points
    considerList = [False] * len(individual)  # zero list with length of individual
    considerList[0] = True
    considerList[-1] = True
    clusterList = [0] * len(individual)  # zero list with length of individual

    # Determine the order of the distance list
    distList = distanceList(instance, individual)
    if verbose:
        print(distList)
    sortedDistanceList = [0] * len(distList)
    for i, x in enumerate(sorted(range(len(distList)), key=lambda y: distList[y])):
        sortedDistanceList[x] = i

    # Start the cluster with the closest pair and add neighbouring customers until
    # the range or capacity constraint is reached. Then find the next closest pair
    # not part of any cluster and repeat until all customers are considered
    for i in range(len(individual)):
        considerCustomer = sortedDistanceList.index(i)
        if verbose:
            print("consider customer index: %d" % considerCustomer)
        # Determine the neighbouring nodes of the considerCustomer
        # Calculate the distance (include rendezvous)
        if considerCustomer == 0:
            clusterEdgeLocation = [considerCustomer, considerCustomer + 1]
            distance = 99999999999  # don't consider the first customer as light resource deliverable
        elif considerCustomer == (len(individual) - 1):
            clusterEdgeLocation = [considerCustomer - 1, considerCustomer]
            distance = 99999999999  # don't consider the last customer as light resource deliverable
        else:
            clusterEdgeLocation = [considerCustomer - 1, considerCustomer + 1]
            distance = culmulativeDistance(instance, individual,
                                           clusterEdgeLocation[0], clusterEdgeLocation[1])

        # Calculate the demand of considerCustomer
        demand = culmulativeDemand(instance, individual, considerCustomer, considerCustomer)

        # First check if the customer is already considered, range feasibility and demand feasibility
        if (any(considerList[clusterEdgeLocation[0]:clusterEdgeLocation[1] + 1])
                or distance > lightRange or demand > lightCapacity):
            continue
        # Passes all tests, initialize considerCustomer as lightCluster
        else:
            considerList[clusterEdgeLocation[0]:clusterEdgeLocation[1] + 1] = [True] * (clusterEdgeLocation[1] - clusterEdgeLocation[0] + 1)
            clusterList[considerCustomer] = 1

            # Incrementally add the neighbouring customers until the edge of cluster reaches the ends of the list
            # Check range feasibility
            # Check demand feasibility
            while clusterEdgeLocation[0] != 0 or clusterEdgeLocation[1] + 1 != len(individual):
                distanceForward = culmulativeDistance(instance, individual,
                                                      clusterEdgeLocation[0], clusterEdgeLocation[1] + 1)
                distanceBackward = culmulativeDistance(instance, individual,
                                                       clusterEdgeLocation[0] - 1, clusterEdgeLocation[1])
                demandForward = culmulativeDemand(instance, individual,
                                                  clusterEdgeLocation[0] + 1, clusterEdgeLocation[1])
                demandBackward = culmulativeDemand(instance, individual,
                                                   clusterEdgeLocation[0], clusterEdgeLocation[1] - 1)
                if verbose:
                    print("Demand from %d to %d is: %d" % (clusterEdgeLocation[0] + 1, clusterEdgeLocation[1], demandForward))
                    print("Demand from %d to %d is: %d" % (clusterEdgeLocation[0], clusterEdgeLocation[1] - 1, demandBackward))
                    print("Range is: %d and %d" % (distanceForward, distanceBackward))

                # Greedy approach: look at the shortest distance neighbouring node to add to cluster
                # If neighbouring node succesfully pass the demand and range constraint
                # Update the cluster list and the consider list
                # Also check if there is a space for light resource to rendezvous
                if (distanceForward <= distanceBackward and distanceForward < lightRange and demandForward < lightCapacity
                        and clusterList[clusterEdgeLocation[1] + 1] == 0):
                    considerList[clusterEdgeLocation[0] + 1:clusterEdgeLocation[1] + 1] = [True] * (clusterEdgeLocation[1] - clusterEdgeLocation[0])
                    clusterList[clusterEdgeLocation[0] + 1:clusterEdgeLocation[1] + 1] = [1] * (clusterEdgeLocation[1] - clusterEdgeLocation[0])
                    if clusterEdgeLocation[1] + 1 != len(individual) - 1:
                        # Make sure you don't add the first node or the end node
                        clusterEdgeLocation[1] = clusterEdgeLocation[1] + 1
                        if verbose:
                            print("Cluster forwards is added")
                    else:
                        break
                elif (distanceForward > distanceBackward and distanceBackward < lightRange and demandBackward < lightCapacity
                        and clusterList[clusterEdgeLocation[0] - 1] == 0):
                    considerList[clusterEdgeLocation[0]:clusterEdgeLocation[1]] = [True] * (clusterEdgeLocation[1] - clusterEdgeLocation[0])
                    clusterList[clusterEdgeLocation[0]:clusterEdgeLocation[1]] = [1] * (clusterEdgeLocation[1] - clusterEdgeLocation[0])
                    if clusterEdgeLocation[0] - 1 != 0:
                        clusterEdgeLocation[0] = clusterEdgeLocation[0] - 1
                        if verbose:
                            print("Cluster backwards is added")
                    else:
                        break
                else:
                    break
                if verbose:
                    print(clusterList)
                    print("The cluster edge is at: %d and %d" % (clusterEdgeLocation[0], clusterEdgeLocation[1]))
    return clusterList


def initMVIndividuals(icls, lightList, individual):
    # Custom method to produce individuals for GA
    # individual = [[L], [L], ..., [H]]
    # [L] = [depart, delivery, delivery, ..., rejoin]
    # The current implmentation will create overlapping rendezvous points for consecutive
    # light resource subRoutes. This could be problematic for the "driver-helper" scenario
    # but efficient for "drone" scenario
    genome = list()

    # Find the indicies of where lightList change from 0 to 1
    splitLocation = numpy.where(numpy.roll(lightList, 1) != lightList)[0]

    # Split the individual
    splitList = numpy.split(individual, splitLocation)

    # Flatten a list of odd elements from the splitList
    heavyGenome = [int(item) for sublist in splitList[0::2] for item in sublist]

    for i in range(2, len(splitList), 2):
        lightGenome = list()
        lightGenome.extend([int(x) for x in random.sample(list(splitList[i - 2]), 1)])
        lightGenome.extend([int(x) for x in splitList[i - 1]])
        lightGenome.extend([int(x) for x in random.sample(list(splitList[i]), 1)])
        genome.append(lightGenome)

    genome.append(heavyGenome)
    return icls(genome)


def evalTSPMS(MVindividual, instance, unitCost=1.0, waitCost=0, delayCost=0, speed=1,
              lightUnitCost=1.0, lightWaitCost=0, lightDelayCost=0, lightSpeed=1):
    # Evaluate the cost of a MVIndividual, created by the initMVIndividual method
    # Includes: travel cost and delay cost of light and heavy resource
    # speed and lightSpeed are speed multipliers for the heavy and light resource respectively 
    # Expects the MVindividual to be [[L], [L], ..., [H]] format
    # The waitCost is when the resource has to wait for the arrival of another resource
    # or the beginning of the delivery window
    # The delayCost is when the resource is late to the delivery window
    route = MVindividual
    totalCost = 0
    lightCost = 0
    heavyCost = 0

    # Dictionary to store the heavy arrival time at this customer
    heavyArrivalTime = dict()
    # Dictionary to store the heavy departure time at this customer
    heavyDepartureTime = dict()
    # Dictionary to store the delay time from the heavy POV at this customer
    # Updated as the light resource are rejoining at this customer
    # Calculated as light resource arrival time - heavy resource departure time
    # If value is positive then heavy resource was waiting
    # If value is negative then light resource was waiting
    resourceDelayTime = dict()

    # Update the heavyArrivalTime and heavyDepartureTime of
    # all heavy resource customers, and calculate the heavy travel cost
    lastCustomerID = 0
    heavyTravelTime = 0
    heavyServiceTime = 0
    heavyTimeCost = 0
    heavyTravelCost = 0
    heavyFinishedTime = 0
    customerID = 0
    for customerID in route[-1]:
        heavyTravelTime = instance['distance_matrix'][lastCustomerID][customerID] * speed
        heavyStartTime = heavyFinishedTime + heavyTravelTime
        heavyArrivalTime[str(customerID)] = heavyStartTime
        heavyServiceTime = instance['customer_%d' % customerID]['service_time'] * 2
        heavyFinishedTime = heavyStartTime + heavyServiceTime
        heavyDepartureTime[str(customerID)] = heavyFinishedTime
        heavyTimeCost = heavyTimeCost + (waitCost * max(instance['customer_%d' % customerID]['ready_time'] - (heavyTravelTime + heavyStartTime), 0)
                            + delayCost * max((heavyStartTime + heavyTravelTime) - instance['customer_%d' % customerID]['due_time'], 0))
        heavyTravelCost = heavyTravelCost + (unitCost * heavyTravelTime)
        lastCustomerID = customerID

    heavyCost = heavyTimeCost + heavyTravelCost + (instance['distance_matrix'][customerID][0] * speed * unitCost)

    # Given the heavyArrivalTime, calculate the light travel time and cost
    # Update the resourceDelayTime accordingly for the rendezvous customer points
    for subLightRoute in route[:-1]:
        lightElapsedTime = 0
        lightTravelTime = 0
        lightServiceTime = 0
        lightTimeCost = 0
        lightTravelCost = 0
        lastCustomerID = subLightRoute[0]
        lightStartTime = heavyArrivalTime[str(subLightRoute[0])]
        # Considers the travel cost and time cost of all light customers except rejoining back
        for cID in subLightRoute[1:-1]:
            lightTravelTime = instance['distance_matrix'][lastCustomerID][cID] * lightSpeed
            lightServiceTime = instance['customer_%d' % cID]['service_time']
            lightElapsedTime = lightElapsedTime + lightTravelTime + lightServiceTime
            lightTimeCost = lightTimeCost + (lightWaitCost * max(instance['customer_%d' % cID]['ready_time'] - (lightElapsedTime + lightStartTime), 0)
                            + lightDelayCost * max((lightStartTime + lightElapsedTime) - instance['customer_%d' % cID]['due_time'], 0))
            lightTravelCost = lightTravelCost + (lightUnitCost * lightTravelTime)
            lastCustomerID = cID
        # Add on the last rejoining leg
        lightTravelTime = instance['distance_matrix'][lastCustomerID][subLightRoute[-1]]
        lightFinishTime = lightStartTime + lightElapsedTime + lightTravelTime
        lightCost = lightCost + lightTravelCost + lightTimeCost + (lightUnitCost * lightTravelTime)
        # update the resourceDelayTime for the ending customer of the lightSubRoute
        resourceDelayTime[str(subLightRoute[-1])] = min(lightFinishTime - heavyDepartureTime[str(subLightRoute[-1])],
                                                        lightFinishTime - heavyArrivalTime[str(subLightRoute[-1])], key=abs)

    # Calculate the waiting penalty given the resourceDelayTime
    # If the value is negative, then the light resource waits for the heavy
    # If the value is positive, then the heavy resource waits for the light
    for cID in resourceDelayTime:
        if resourceDelayTime[cID] <= 0:
            totalCost = totalCost + (lightWaitCost * abs(resourceDelayTime[cID]))
        else:
            totalCost = totalCost + (waitCost * resourceDelayTime[cID])

    totalCost = totalCost + lightCost + heavyCost
    fitness = 1.0 / totalCost
    return fitness,


def cxSinglePointSwap(ind1, ind2):
    # A customized crossover method for a TSP route with light and heavy resource
    # Takes in two individuals and randomly swaps the rendezvous points of the light
    # resource subroutes, ignores the heavy resource subroute

    # Iterate both individuals simultaneously since ind1 and ind2
    # are the same length
    for (subRoute1, subRoute2) in zip(ind1[:-1], ind2[:-1]):
        # swap the depart customer if random number is less than 0.5
        if random.uniform(0, 1) < 0.5:
            temp1 = subRoute1[0]
            temp2 = subRoute2[0]
            subRoute1[0] = temp2
            subRoute2[0] = temp1
        # swap the reunion customer if random number is greater or equal to 0.5
        else:
            temp1 = subRoute1[-1]
            temp2 = subRoute2[-1]
            subRoute1[-1] = temp2
            subRoute2[-1] = temp1
    return ind1, ind2


def mutMVRendezvous(individual, lightList, subRoute, indpb=0.2):
    """Mutates an MV individual by re-sampling departure or reunion rendezvous points

    from valid adjacent heavy sub-route segments.
    """
    splitLocation = numpy.where(numpy.roll(lightList, 1) != lightList)[0]
    splitList = numpy.split(subRoute, splitLocation)

    for idx, i in enumerate(range(2, len(splitList), 2)):
        if random.random() < indpb:
            lightRoute = individual[idx]
            preceding_heavy = list(splitList[i - 2])
            succeeding_heavy = list(splitList[i])
            if random.random() < 0.5 and len(preceding_heavy) > 1:
                candidates = [c for c in preceding_heavy if c != lightRoute[0]]
                if candidates:
                    lightRoute[0] = int(random.choice(candidates))
            elif len(succeeding_heavy) > 1:
                candidates = [c for c in succeeding_heavy if c != lightRoute[-1]]
                if candidates:
                    lightRoute[-1] = int(random.choice(candidates))
    return individual,