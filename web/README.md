# VRPMV Interactive Web Visualizer

A zero-dependency, modern static web application to visualize and run the **Vehicle Routing Problem with Movement Synchronization (VRPMV)** two-stage Genetic Algorithm.

Built to be hosted on [pauldeng.me](https://pauldeng.me) or deployed statically on GitHub Pages / Vercel / Netlify.

## Features

- **Interactive Canvas Map**:
  - Auto-scaled coordinates with pan and zoom.
  - Hover tooltips for customer demands, time windows, and coordinates.
  - Color-coded solid routes for heavy trucks and dashed glowing green routes for light drones.
  - Highlighting of drone takeoff (🛫) and landing/reunion (🛬) rendezvous points.
  - Route playback animation with moving 🚚 trucks and 🚁 drones.
- **Two-Stage Comparison**:
  - Toggle between **Stage 1 (Pure Truck VRPTW)** and **Stage 2 (Movement Synchronized VRPMV)**.
  - Live metric KPI cards: Total Cost, Fleet Size, Drone Sorties, and Efficiency Savings.
- **Temporal Movement Synchronization (Gantt Chart)**:
  - Visualizes truck tours, drone delivery clusters, and synchronization waiting penalties.
- **In-Browser Genetic Algorithm Solver**:
  - Client-side GA engine executing PMX crossover, 2-opt local search refinement, and greedy drone clustering live in the browser.

## Local Preview

Start any local web server:

```bash
python3 -m http.server 8080 --directory web
```

Then open `http://localhost:8080` in your browser.

## Hosting on pauldeng.me

Because this app is completely client-side and requires no backend server:
1. Copy the files in `web/` (`index.html`, `style.css`, `app.js`, and `data/instances.js`) into your website repository (e.g. at `pauldeng.me/vrpmv/` or similar path).
2. Alternatively, embed it as an `<iframe>` within any page on `pauldeng.me`.
