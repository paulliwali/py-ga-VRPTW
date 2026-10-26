# -*- coding: utf-8 -*-

import os
import fnmatch
import matplotlib.pyplot as plt
import json
import pandas as pd
from . import BASE_DIR


def makeDirsForFile(pathname):
    try:
        os.makedirs(os.path.split(pathname)[0], exist_ok=True)
    except Exception:
        pass


def exist(pathname, overwrite=False, displayInfo=True):
    def __pathType(pathname):
        if os.path.isfile(pathname):
            return 'File'
        if os.path.isdir(pathname):
            return 'Directory'
        if os.path.islink(pathname):
            return 'Symbolic Link'
        if os.path.ismount(pathname):
            return 'Mount Point'
        return 'Path'

    if os.path.exists(pathname):
        if overwrite:
            if displayInfo:
                print('%s: %s exists. Overwrite.' % (__pathType(pathname), pathname))
            os.remove(pathname)
            return False
        else:
            if displayInfo:
                print('%s: %s exists.' % (__pathType(pathname), pathname))
            return True
    else:
        if displayInfo:
            print('%s: %s does not exist.' % (__pathType(pathname), pathname))
        return False


def text2json(customize=False):
    def __distance(customer1, customer2):
        return ((customer1['coordinates']['x'] - customer2['coordinates']['x']) ** 2 +
                (customer1['coordinates']['y'] - customer2['customer2']['coordinates']['y'] if 'customer2' in customer2 else (customer1['coordinates']['y'] - customer2['coordinates']['y']) ** 2)) ** 0.5

    def _dist(c1, c2):
        return ((c1['coordinates']['x'] - c2['coordinates']['x']) ** 2 +
                (c1['coordinates']['y'] - c2['coordinates']['y']) ** 2) ** 0.5

    if customize:
        textDataDir = os.path.join(BASE_DIR, 'data', 'text_customize')
        jsonDataDir = os.path.join(BASE_DIR, 'data', 'json_customize')
    else:
        textDataDir = os.path.join(BASE_DIR, 'data', 'text')
        jsonDataDir = os.path.join(BASE_DIR, 'data', 'json')

    for textFilename in sorted(fnmatch.filter(os.listdir(textDataDir), '*.txt')):
        textFile = os.path.join(textDataDir, textFilename)
        jsonData = {}
        with open(textFile, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]

        # Find customer line start
        custLines = []
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            if len(parts) >= 7 and parts[0].isdigit():
                custLines.append(parts)

        # Parse instance name and vehicle parameters
        jsonData['instance_name'] = lines[0]
        # Line with vehicle info
        for line in lines[1:6]:
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit() and (parts[1].isdigit() or parts[1].replace('.', '', 1).isdigit()):
                jsonData['max_vehicle_number'] = int(parts[0])
                jsonData['vehicle_capacity'] = float(parts[1])
                if len(parts) >= 5:
                    jsonData['max_light_vehicle_number'] = int(parts[2])
                    jsonData['light_vehicle_capacity'] = float(parts[3])
                    jsonData['light_vehicle_range'] = float(parts[4])
                break

        for parts in custLines:
            cust_id = int(parts[0])
            node_data = {
                'coordinates': {
                    'x': float(parts[1]),
                    'y': float(parts[2]),
                },
                'demand': float(parts[3]),
                'ready_time': float(parts[4]),
                'due_time': float(parts[5]),
                'service_time': float(parts[6]),
            }
            if cust_id == 0:
                jsonData['deport'] = node_data
            else:
                jsonData['customer_%d' % cust_id] = node_data

        numOfCustomers = len(custLines)
        customers = ['deport'] + ['customer_%d' % x for x in range(1, numOfCustomers)]
        jsonData['distance_matrix'] = [[_dist(jsonData[c1], jsonData[c2]) for c1 in customers] for c2 in customers]

        jsonFilename = '%s.json' % jsonData['instance_name']
        jsonPathname = os.path.join(jsonDataDir, jsonFilename)
        print('Write to file: %s' % jsonPathname)
        makeDirsForFile(pathname=jsonPathname)
        with open(jsonPathname, 'w') as f:
            json.dump(jsonData, f, sort_keys=True, indent=4, separators=(',', ': '))


def plotResults():
    plt.style.use('ggplot')
    resultsDataDir = os.path.join(BASE_DIR, 'results')
    if not os.path.exists(resultsDataDir):
        print('No results directory found at %s' % resultsDataDir)
        return
    for csvFile in map(lambda csvFilename: os.path.join(resultsDataDir, csvFilename), fnmatch.filter(os.listdir(resultsDataDir), '*.csv')):
        df = pd.read_csv(csvFile)
        # Drop columns not needed for fitness plot
        cols_to_drop = [c for c in ['generation', 'evaluated_individuals', 'std_fitness', 'avg_cost'] if c in df.columns]
        df_plot = df.drop(columns=cols_to_drop)

        plt.figure()
        ax = df_plot.plot(figsize=(20, 10))
        ax.set_xlabel('Generation')
        ax.set_ylabel('Fitness')

        filename = os.path.splitext(csvFile)[0]
        plt.savefig(filename + '.png')
        plt.close('all')


def visualizeRoutes(instanceName, instance, route, containsLightResource=False):
    rows = []
    for customer in instance:
        if customer.startswith("customer"):
            rows.append({
                "customer_number": str(customer),
                "x_pos": float(instance[customer]["coordinates"]["x"]),
                "y_pos": float(instance[customer]["coordinates"]["y"])
            })
        elif customer.startswith("deport"):
            rows.append({
                "customer_number": "customer_0",
                "x_pos": float(instance[customer]["coordinates"]["x"]),
                "y_pos": float(instance[customer]["coordinates"]["y"])
            })
    df = pd.DataFrame(rows)

    plt.style.use('ggplot')
    plotDataDir = os.path.join(BASE_DIR, 'data', 'plot')
    makeDirsForFile(os.path.join(plotDataDir, 'dummy.txt'))

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.scatter(df['x_pos'], df['y_pos'], color='red', zorder=5)

    x_depot = float(df.loc[df['customer_number'] == "customer_0"]['x_pos'].iloc[0])
    y_depot = float(df.loc[df['customer_number'] == "customer_0"]['y_pos'].iloc[0])
    ax.text(x_depot + 1, y_depot + 1, "depot (0)", fontweight='bold', color='black')

    for _, row in df.iterrows():
        if row['customer_number'] != "customer_0":
            c_num = row['customer_number'].replace("customer_", "")
            ax.text(row['x_pos'] + 0.5, row['y_pos'] + 0.5, c_num, fontsize=9)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title(f'Route Visualization: {instanceName}')

    def get_pos(c_id):
        key = "customer_0" if c_id == 0 else f"customer_{c_id}"
        r = df.loc[df['customer_number'] == key]
        return float(r['x_pos'].iloc[0]), float(r['y_pos'].iloc[0])

    if not containsLightResource:
        colors = ['blue', 'green', 'purple', 'orange', 'cyan', 'magenta', 'brown']
        for idx, subRoute in enumerate(route):
            color = colors[idx % len(colors)]
            full_sub = [0] + subRoute + [0]
            xs = [get_pos(c)[0] for c in full_sub]
            ys = [get_pos(c)[1] for c in full_sub]
            ax.plot(xs, ys, color=color, linewidth=2, label=f'Vehicle {idx + 1}')
    else:
        # Mixed heavy & light routes: route = [[L1, L2, ..., H], ...]
        colors = ['blue', 'purple', 'brown', 'teal', 'darkorange']
        for idx, subRoute in enumerate(route):
            base_color = colors[idx % len(colors)]
            heavy_route = subRoute[-1]
            full_heavy = [0] + heavy_route + [0]
            xs_h = [get_pos(c)[0] for c in full_heavy]
            ys_h = [get_pos(c)[1] for c in full_heavy]
            ax.plot(xs_h, ys_h, color=base_color, linewidth=2.5, label=f'Heavy Vehicle {idx + 1}')

            for l_idx, light_sub in enumerate(subRoute[:-1]):
                xs_l = [get_pos(c)[0] for c in light_sub]
                ys_l = [get_pos(c)[1] for c in light_sub]
                ax.plot(xs_l, ys_l, color='limegreen', linestyle='--', linewidth=2,
                        label='Light Resource' if idx == 0 and l_idx == 0 else "")

    ax.legend()
    filelocation = os.path.join(plotDataDir, instanceName)
    plt.savefig(filelocation + '.png', bbox_inches='tight')
    plt.close(fig)
