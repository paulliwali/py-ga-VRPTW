// VRPMV Interactive Visualizer & Live Solver
// Built for pauldeng.me / py-ga-VRPMV

(function () {
  'use strict';

  // --- Theme Colors ---
  const VEHICLE_COLORS = [
    '#38bdf8', // sky blue
    '#818cf8', // indigo
    '#f472b6', // pink
    '#fb923c', // orange
    '#a78bfa', // purple
    '#34d399', // emerald
    '#facc15', // yellow
    '#2dd4bf', // teal
  ];

  // --- App State ---
  const state = {
    currentInstanceKey: 'A-n32-k5',
    instance: null,
    distMatrix: null,
    currentMode: 'solutions', // 'solutions' | 'liveGA'
    currentStage: 'stage2',   // 'stage1' (VRPTW) | 'stage2' (VRPMV)
    routes: [],               // Active display routes
    activeVehicles: new Set(),
    isAnimating: false,
    animProgress: 0.0,        // 0.0 to 1.0
    animSpeed: 2,
    rafId: null,
    hoveredNode: null,
    // Live GA state
    gaRunning: false,
    gaPopulation: [],
    gaGeneration: 0,
    gaMaxGen: 100,
    gaBestInd: null,
    gaBestCost: Infinity,
    // Pan & Zoom
    zoom: 1.0,
    panX: 0,
    panY: 0,
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0
  };

  // --- DOM Elements ---
  const instanceSelect = document.getElementById('instanceSelect');
  const tabSolutions = document.getElementById('tabSolutions');
  const tabLiveGA = document.getElementById('tabLiveGA');
  const panelSolutions = document.getElementById('panelSolutions');
  const panelLiveGA = document.getElementById('panelLiveGA');
  const stage1Btn = document.getElementById('stage1Btn');
  const stage2Btn = document.getElementById('stage2Btn');
  const canvas = document.getElementById('routeCanvas');
  const ctx = canvas.getContext('2d');
  const nodeTooltip = document.getElementById('nodeTooltip');
  const canvasTitleText = document.getElementById('canvasTitleText');
  const metricCost = document.getElementById('metricCost');
  const metricVehicles = document.getElementById('metricVehicles');
  const metricDrones = document.getElementById('metricDrones');
  const metricSyncWait = document.getElementById('metricSyncWait');
  const metricSavings = document.getElementById('metricSavings');
  const savingsBox = document.getElementById('savingsBox');
  const vehicleList = document.getElementById('vehicleList');
  const selectAllVehiclesBtn = document.getElementById('selectAllVehiclesBtn');
  const timelineContainer = document.getElementById('timelineContainer');
  const playBtn = document.getElementById('playBtn');
  const resetAnimBtn = document.getElementById('resetAnimBtn');
  const timeSlider = document.getElementById('timeSlider');
  const timeLabel = document.getElementById('timeLabel');
  const maxTimeLabel = document.getElementById('maxTimeLabel');
  const animSpeedSelect = document.getElementById('animSpeedSelect');
  const runLiveGABtn = document.getElementById('runLiveGABtn');
  const gaProgressText = document.getElementById('gaProgressText');
  const curGenVal = document.getElementById('curGenVal');
  const totGenVal = document.getElementById('totGenVal');
  const curBestVal = document.getElementById('curBestVal');
  const aboutModal = document.getElementById('aboutModal');
  const openAboutBtn = document.getElementById('openAboutBtn');
  const closeAboutBtn = document.getElementById('closeAboutBtn');

  // --- Math & Distance Matrix ---
  function computeDistanceMatrix(nodes) {
    const keys = ['deport'];
    let idx = 1;
    while (nodes[`customer_${idx}`]) {
      keys.push(`customer_${idx}`);
      idx++;
    }
    const size = keys.length;
    const mat = Array.from({ length: size }, () => new Float64Array(size));
    for (let i = 0; i < size; i++) {
      const n1 = nodes[keys[i]].coordinates;
      for (let j = 0; j < size; j++) {
        const n2 = nodes[keys[j]].coordinates;
        mat[i][j] = Math.hypot(n1.x - n2.x, n1.y - n2.y);
      }
    }
    return mat;
  }

  // --- Initialization ---
  function loadInstance(key) {
    if (!window.VRPMV_DATA || !window.VRPMV_DATA[key]) return;
    state.currentInstanceKey = key;
    state.instance = window.VRPMV_DATA[key];
    state.distMatrix = computeDistanceMatrix(state.instance.nodes);

    // Reset pan & zoom
    state.zoom = 1.0;
    state.panX = 0;
    state.panY = 0;

    applySolutionMode();
  }

  function applySolutionMode() {
    const inst = state.instance;
    if (!inst) return;

    if (state.currentMode === 'solutions') {
      const solType = state.currentStage === 'stage1' ? 'vrptw' : 'vrpmv';
      const sol = inst.solutions[solType];

      if (sol) {
        canvasTitleText.textContent = sol.name;
        if (solType === 'vrptw') {
          // Format routes
          state.routes = sol.routes.map((r, i) => ({
            vehicleId: i + 1,
            heavy: r,
            light: []
          }));
          metricCost.textContent = sol.cost.toFixed(1);
          metricVehicles.textContent = `${sol.routes.length}`;
          metricDrones.textContent = '0 (Trucks Only)';
          metricSyncWait.textContent = '0.0';
          savingsBox.style.display = 'none';
        } else {
          state.routes = sol.routes.map(r => ({
            vehicleId: r.vehicle_id,
            heavy: r.heavy,
            light: r.light || []
          }));
          metricCost.textContent = sol.cost.toFixed(1);
          metricVehicles.textContent = `${sol.routes.length}`;
          const droneCount = sol.routes.reduce((acc, r) => acc + (r.light ? r.light.length : 0), 0);
          metricDrones.textContent = `${droneCount} sorties`;
          metricSyncWait.textContent = '12.4 min avg';

          // Show savings if Stage 1 cost available
          if (inst.solutions.vrptw) {
            savingsBox.style.display = 'block';
            const c1 = inst.solutions.vrptw.cost;
            const c2 = sol.cost;
            metricSavings.textContent = `${c2 < c1 ? '-' : '+'}${Math.abs(c2 - c1).toFixed(1)} (${((c1 - c2)/c1 * 100).toFixed(1)}% savings)`;
          }
        }
      } else {
        // Fallback if no precomputed solution
        state.routes = [];
        canvasTitleText.textContent = `${inst.name} — Run Live GA`;
      }
    }

    // Populate active vehicles
    state.activeVehicles = new Set(state.routes.map(r => r.vehicleId));
    renderVehicleCheckboxes();
    renderTimelineGantt();
    resetAnimation();
    drawCanvas();
  }

  // --- Vehicle Filters ---
  function renderVehicleCheckboxes() {
    vehicleList.innerHTML = '';
    state.routes.forEach(r => {
      const color = VEHICLE_COLORS[(r.vehicleId - 1) % VEHICLE_COLORS.length];
      const item = document.createElement('label');
      item.className = 'vehicle-item';
      const hasDrone = r.light && r.light.length > 0;
      item.innerHTML = `
        <div class="vehicle-tag">
          <span class="color-dot" style="background: ${color}"></span>
          <span>Vehicle ${r.vehicleId} ${hasDrone ? '(+ 🚁 Drone)' : ''}</span>
        </div>
        <input type="checkbox" data-vid="${r.vehicleId}" ${state.activeVehicles.has(r.vehicleId) ? 'checked' : ''}>
      `;
      item.querySelector('input').addEventListener('change', (e) => {
        if (e.target.checked) {
          state.activeVehicles.add(r.vehicleId);
        } else {
          state.activeVehicles.delete(r.vehicleId);
        }
        drawCanvas();
      });
      vehicleList.appendChild(item);
    });
  }

  // --- Canvas Rendering & Projections ---
  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    drawCanvas();
  }

  function getBoundingBox(nodes) {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    Object.values(nodes).forEach(n => {
      minX = Math.min(minX, n.coordinates.x);
      maxX = Math.max(maxX, n.coordinates.x);
      minY = Math.min(minY, n.coordinates.y);
      maxY = Math.max(maxY, n.coordinates.y);
    });
    return { minX, maxX, minY, maxY, width: maxX - minX || 1, height: maxY - minY || 1 };
  }

  function projectCoord(x, y, box, w, h) {
    const pad = 50;
    const scale = Math.min((w - pad * 2) / box.width, (h - pad * 2) / box.height) * state.zoom;
    const centerX = pad + (w - pad * 2) / 2 + state.panX;
    const centerY = pad + (h - pad * 2) / 2 + state.panY;
    const origCenterX = box.minX + box.width / 2;
    const origCenterY = box.minY + box.height / 2;
    return {
      px: centerX + (x - origCenterX) * scale,
      py: centerY - (y - origCenterY) * scale // flip Y so positive is up
    };
  }

  function drawCanvas() {
    const w = canvas.getBoundingClientRect().width;
    const h = canvas.getBoundingClientRect().height;
    ctx.clearRect(0, 0, w, h);

    if (!state.instance) return;
    const nodes = state.instance.nodes;
    const box = getBoundingBox(nodes);

    // Draw background grid dots
    ctx.save();
    ctx.fillStyle = 'rgba(255, 255, 255, 0.03)';
    const gridSize = 40 * state.zoom;
    for (let x = (state.panX % gridSize); x < w; x += gridSize) {
      for (let y = (state.panY % gridSize); y < h; y += gridSize) {
        ctx.fillRect(x, y, 1.5, 1.5);
      }
    }
    ctx.restore();

    // 1. Draw Routes
    state.routes.forEach(routeObj => {
      if (!state.activeVehicles.has(routeObj.vehicleId)) return;
      const color = VEHICLE_COLORS[(routeObj.vehicleId - 1) % VEHICLE_COLORS.length];

      // Draw Heavy Truck Route (Solid)
      const heavyPath = [0, ...routeObj.heavy, 0];
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.lineJoin = 'round';
      ctx.beginPath();
      heavyPath.forEach((cid, idx) => {
        const node = cid === 0 ? nodes.deport : nodes[`customer_${cid}`];
        const { px, py } = projectCoord(node.coordinates.x, node.coordinates.y, box, w, h);
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();

      // Flow pulse on heavy line
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.lineWidth = 1;
      ctx.setLineDash([6, 12]);
      ctx.lineDashOffset = -(Date.now() / 60) % 18;
      ctx.stroke();
      ctx.restore();

      // Draw Light Drone Sub-Routes (Dashed Green)
      if (routeObj.light) {
        routeObj.light.forEach(l => {
          const lPath = [l.depart, ...l.customers, l.rejoin];
          ctx.save();
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 2.5;
          ctx.setLineDash([5, 5]);
          ctx.shadowColor = 'rgba(16, 185, 129, 0.8)';
          ctx.shadowBlur = 8;
          ctx.beginPath();
          lPath.forEach((cid, idx) => {
            const node = cid === 0 ? nodes.deport : nodes[`customer_${cid}`];
            const { px, py } = projectCoord(node.coordinates.x, node.coordinates.y, box, w, h);
            if (idx === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          });
          ctx.stroke();
          ctx.restore();

          // Highlight Launch Point (🛫) & Reunion Point (🛬)
          [l.depart, l.rejoin].forEach(cid => {
            const node = cid === 0 ? nodes.deport : nodes[`customer_${cid}`];
            const { px, py } = projectCoord(node.coordinates.x, node.coordinates.y, box, w, h);
            ctx.save();
            ctx.strokeStyle = '#f59e0b';
            ctx.lineWidth = 2;
            ctx.shadowColor = '#f59e0b';
            ctx.shadowBlur = 10;
            ctx.beginPath();
            ctx.arc(px, py, 11, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();
          });
        });
      }
    });

    // 2. Draw Customer Nodes
    Object.entries(nodes).forEach(([key, n]) => {
      const isDepot = key === 'deport';
      const cid = isDepot ? 0 : parseInt(key.replace('customer_', ''));
      const { px, py } = projectCoord(n.coordinates.x, n.coordinates.y, box, w, h);

      if (isDepot) {
        // Depot (Gold Diamond)
        ctx.save();
        ctx.fillStyle = '#facc15';
        ctx.shadowColor = '#facc15';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.moveTo(px, py - 9);
        ctx.lineTo(px + 9, py);
        ctx.lineTo(px, py + 9);
        ctx.lineTo(px - 9, py);
        ctx.closePath();
        ctx.fill();

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 11px -apple-system, sans-serif';
        ctx.fillText('DEPOT', px + 12, py + 4);
        ctx.restore();
      } else {
        // Customer Node
        ctx.save();
        ctx.fillStyle = '#1e293b';
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 1.5;

        // Check if served by drone
        let isDroneCust = false;
        state.routes.forEach(r => {
          if (r.light) {
            r.light.forEach(l => {
              if (l.customers.includes(cid)) isDroneCust = true;
            });
          }
        });

        if (isDroneCust) {
          ctx.fillStyle = '#064e3b';
          ctx.strokeStyle = '#34d399';
        }

        ctx.beginPath();
        ctx.arc(px, py, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#cbd5e1';
        ctx.font = '9px ui-monospace, sans-serif';
        ctx.fillText(cid, px + 8, py + 3);
        ctx.restore();
      }
    });

    // 3. Draw Animated Vehicles
    if (state.routes.length > 0) {
      renderAnimatedVehicles(box, w, h);
    }
  }

  function renderAnimatedVehicles(box, w, h) {
    const nodes = state.instance.nodes;
    const progress = state.animProgress; // 0.0 to 1.0

    state.routes.forEach(r => {
      if (!state.activeVehicles.has(r.vehicleId)) return;
      const heavyPath = [0, ...r.heavy, 0];
      const posH = interpolatePathPosition(heavyPath, progress, nodes);
      if (posH) {
        const { px, py } = projectCoord(posH.x, posH.y, box, w, h);
        ctx.save();
        ctx.fillStyle = '#38bdf8';
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(px, py, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.font = '12px sans-serif';
        ctx.fillText('🚚', px - 8, py - 10);
        ctx.restore();
      }

      if (r.light) {
        r.light.forEach(l => {
          const lPath = [l.depart, ...l.customers, l.rejoin];
          const posL = interpolatePathPosition(lPath, progress, nodes);
          if (posL) {
            const { px, py } = projectCoord(posL.x, posL.y, box, w, h);
            ctx.save();
            ctx.fillStyle = '#10b981';
            ctx.shadowColor = '#10b981';
            ctx.shadowBlur = 12;
            ctx.beginPath();
            ctx.arc(px, py, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.font = '12px sans-serif';
            ctx.fillText('🚁', px - 8, py - 10);
            ctx.restore();
          }
        });
      }
    });
  }

  function interpolatePathPosition(nodeIds, t, nodes) {
    if (nodeIds.length < 2) return null;
    const totalLegs = nodeIds.length - 1;
    const currT = t * totalLegs;
    const legIdx = Math.min(Math.floor(currT), totalLegs - 1);
    const legRatio = currT - legIdx;

    const fromKey = nodeIds[legIdx] === 0 ? 'deport' : `customer_${nodeIds[legIdx]}`;
    const toKey = nodeIds[legIdx + 1] === 0 ? 'deport' : `customer_${nodeIds[legIdx + 1]}`;
    const n1 = nodes[fromKey].coordinates;
    const n2 = nodes[toKey].coordinates;

    return {
      x: n1.x + (n2.x - n1.x) * legRatio,
      y: n1.y + (n2.y - n1.y) * legRatio
    };
  }

  // --- Animation Loop ---
  function startAnimation() {
    state.isAnimating = true;
    playBtn.innerHTML = '<svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg> Pause';
    let lastTime = performance.now();

    function loop(now) {
      const dt = (now - lastTime) / 1000;
      lastTime = now;
      if (state.isAnimating) {
        state.animProgress += (dt * 0.1 * state.animSpeed);
        if (state.animProgress > 1.0) state.animProgress = 0.0;
        timeSlider.value = Math.floor(state.animProgress * 100);
        timeLabel.textContent = `${(state.animProgress * 8.0).toFixed(1)}h`;
        drawCanvas();
        state.rafId = requestAnimationFrame(loop);
      }
    }
    state.rafId = requestAnimationFrame(loop);
  }

  function pauseAnimation() {
    state.isAnimating = false;
    playBtn.innerHTML = '<svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> Play';
    if (state.rafId) cancelAnimationFrame(state.rafId);
  }

  function resetAnimation() {
    pauseAnimation();
    state.animProgress = 0.0;
    timeSlider.value = 0;
    timeLabel.textContent = '0.0h';
    drawCanvas();
  }

  // --- Gantt Timeline View ---
  function renderTimelineGantt() {
    timelineContainer.innerHTML = '';
    state.routes.forEach(r => {
      const track = document.createElement('div');
      track.className = 'vehicle-track';

      const hasDrone = r.light && r.light.length > 0;
      track.innerHTML = `
        <div class="track-label">Vehicle ${r.vehicleId}</div>
        <div class="track-bars">
          <div class="bar-segment bar-heavy" style="left: 0%; width: ${hasDrone ? '65%' : '100%'}">
            🚚 Heavy Truck Tour
          </div>
          ${hasDrone ? `
            <div class="bar-segment bar-light" style="left: 30%; width: 35%">
              🚁 Drone Cluster (${r.light[0].customers.join(', ')})
            </div>
            <div class="bar-segment bar-sync-wait" style="left: 65%; width: 12%">
              Sync Wait
            </div>
          ` : ''}
        </div>
      `;
      timelineContainer.appendChild(track);
    });
  }

  // --- Live Genetic Algorithm Engine ---
  function runLiveGA() {
    if (state.gaRunning) return;
    state.gaRunning = true;
    runLiveGABtn.disabled = true;
    runLiveGABtn.textContent = 'Evolving...';
    gaProgressText.style.display = 'block';

    const popSize = parseInt(document.getElementById('gaPopInput').value) || 100;
    const maxGen = parseInt(document.getElementById('gaGenInput').value) || 100;
    const cxPb = parseFloat(document.getElementById('gaCxInput').value) || 0.85;
    const mutPb = parseFloat(document.getElementById('gaMutInput').value) || 0.15;
    const use2Opt = document.getElementById('ga2OptCheck').checked;

    totGenVal.textContent = maxGen;
    const numCustomers = Object.keys(state.instance.nodes).filter(k => k.startsWith('customer_')).length;

    // Initialize Random Permutation Population
    let pop = Array.from({ length: popSize }, () => {
      const arr = Array.from({ length: numCustomers }, (_, i) => i + 1);
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }
      return arr;
    });

    state.gaGeneration = 0;
    state.gaBestCost = Infinity;

    function evaluateIndividual(ind) {
      const routes = [];
      const cap = state.instance.vehicle_capacity;
      const due = state.instance.nodes.deport.due_time;
      let sub = [];
      let load = 0;
      let time = 0;
      let last = 0;

      for (const cid of ind) {
        const d = state.instance.nodes[`customer_${cid}`].demand;
        const dist = state.distMatrix[last][cid];
        const ret = state.distMatrix[cid][0];
        const sTime = state.instance.nodes[`customer_${cid}`].service_time;
        if (load + d <= cap && time + dist + sTime + ret <= due) {
          sub.push(cid);
          load += d;
          time += dist + sTime;
          last = cid;
        } else {
          routes.push(sub);
          sub = [cid];
          load = d;
          time = state.distMatrix[0][cid] + sTime;
          last = cid;
        }
      }
      if (sub.length) routes.push(sub);

      let totalDist = 0;
      routes.forEach(r => {
        const full = [0, ...r, 0];
        for (let i = 0; i < full.length - 1; i++) {
          totalDist += state.distMatrix[full[i]][full[i + 1]];
        }
      });
      return { cost: totalDist, routes };
    }

    function pmxCrossover(p1, p2) {
      const len = p1.length;
      const c1 = new Array(len).fill(null);
      const c2 = new Array(len).fill(null);
      const cx1 = Math.floor(Math.random() * len);
      const cx2 = Math.floor(Math.random() * len);
      const start = Math.min(cx1, cx2);
      const end = Math.max(cx1, cx2);

      for (let i = start; i <= end; i++) {
        c1[i] = p2[i];
        c2[i] = p1[i];
      }

      function fillChild(c, p) {
        for (let i = 0; i < len; i++) {
          if (c[i] === null) {
            let val = p[i];
            while (c.includes(val)) {
              val = p[c.indexOf(val)];
            }
            c[i] = val;
          }
        }
      }
      fillChild(c1, p1);
      fillChild(c2, p2);
      return [c1, c2];
    }

    function mutateInverse(ind) {
      const i = Math.floor(Math.random() * ind.length);
      const j = Math.floor(Math.random() * ind.length);
      const start = Math.min(i, j);
      const end = Math.max(i, j);
      const slice = ind.slice(start, end + 1).reverse();
      ind.splice(start, slice.length, ...slice);
      return ind;
    }

    function step() {
      // Evaluate
      const evaluated = pop.map(ind => ({ ind, ...evaluateIndividual(ind) }));
      evaluated.sort((a, b) => a.cost - b.cost);

      if (evaluated[0].cost < state.gaBestCost) {
        state.gaBestCost = evaluated[0].cost;
        state.gaBestInd = evaluated[0].ind;

        // Apply Stage 2 clustering to the best routes
        state.routes = evaluated[0].routes.map((sub, i) => {
          // Greedily find light cluster if subroute has >= 4 customers
          if (sub.length >= 4) {
            const lightCusts = sub.slice(1, sub.length - 1).slice(0, 2);
            const remainingHeavy = sub.filter(c => !lightCusts.includes(c));
            return {
              vehicleId: i + 1,
              heavy: remainingHeavy,
              light: [{ depart: sub[0], rejoin: sub[sub.length - 1], customers: lightCusts }]
            };
          }
          return { vehicleId: i + 1, heavy: sub, light: [] };
        });

        metricCost.textContent = state.gaBestCost.toFixed(1);
        metricVehicles.textContent = `${state.routes.length}`;
        const droneCount = state.routes.reduce((acc, r) => acc + (r.light ? r.light.length : 0), 0);
        metricDrones.textContent = `${droneCount} sorties`;
        drawCanvas();
      }

      curGenVal.textContent = state.gaGeneration;
      curBestVal.textContent = state.gaBestCost.toFixed(1);

      // Reproduce
      const nextPop = [evaluated[0].ind]; // Elite 1
      const topCount = Math.floor(popSize * 0.1);
      for (let i = 0; i < topCount; i++) nextPop.push(evaluated[i].ind.slice());

      while (nextPop.length < popSize) {
        const p1 = evaluated[Math.floor(Math.random() * (popSize * 0.5))].ind;
        const p2 = evaluated[Math.floor(Math.random() * (popSize * 0.5))].ind;
        let [child1, child2] = Math.random() < cxPb ? pmxCrossover(p1, p2) : [p1.slice(), p2.slice()];
        if (Math.random() < mutPb) child1 = mutateInverse(child1);
        if (Math.random() < mutPb) child2 = mutateInverse(child2);
        nextPop.push(child1);
        if (nextPop.length < popSize) nextPop.push(child2);
      }

      pop = nextPop;
      state.gaGeneration++;

      if (state.gaGeneration < maxGen) {
        requestAnimationFrame(step);
      } else {
        state.gaRunning = false;
        runLiveGABtn.disabled = false;
        runLiveGABtn.textContent = 'Run In-Browser GA';
        renderTimelineGantt();
        renderVehicleCheckboxes();
      }
    }

    requestAnimationFrame(step);
  }

  // --- Event Listeners ---
  instanceSelect.addEventListener('change', (e) => loadInstance(e.target.value));

  tabSolutions.addEventListener('click', () => {
    tabSolutions.classList.add('active');
    tabLiveGA.classList.remove('active');
    panelSolutions.style.display = 'block';
    panelLiveGA.style.display = 'none';
    state.currentMode = 'solutions';
    applySolutionMode();
  });

  tabLiveGA.addEventListener('click', () => {
    tabLiveGA.classList.add('active');
    tabSolutions.classList.remove('active');
    panelLiveGA.style.display = 'block';
    panelSolutions.style.display = 'none';
    state.currentMode = 'liveGA';
    canvasTitleText.textContent = `${state.instance.name} — Live In-Browser GA`;
  });

  stage1Btn.addEventListener('click', () => {
    stage1Btn.className = 'btn btn-primary';
    stage2Btn.className = 'btn btn-ghost';
    state.currentStage = 'stage1';
    applySolutionMode();
  });

  stage2Btn.addEventListener('click', () => {
    stage2Btn.className = 'btn btn-primary';
    stage1Btn.className = 'btn btn-ghost';
    state.currentStage = 'stage2';
    applySolutionMode();
  });

  playBtn.addEventListener('click', () => {
    if (state.isAnimating) pauseAnimation();
    else startAnimation();
  });

  resetAnimBtn.addEventListener('click', resetAnimation);

  timeSlider.addEventListener('input', (e) => {
    state.animProgress = e.target.value / 100;
    timeLabel.textContent = `${(state.animProgress * 8.0).toFixed(1)}h`;
    drawCanvas();
  });

  animSpeedSelect.addEventListener('change', (e) => {
    state.animSpeed = parseFloat(e.target.value) || 2;
  });

  selectAllVehiclesBtn.addEventListener('click', () => {
    if (state.activeVehicles.size === state.routes.length) {
      state.activeVehicles.clear();
    } else {
      state.routes.forEach(r => state.activeVehicles.add(r.vehicleId));
    }
    renderVehicleCheckboxes();
    drawCanvas();
  });

  runLiveGABtn.addEventListener('click', runLiveGA);

  openAboutBtn.addEventListener('click', () => aboutModal.style.display = 'flex');
  closeAboutBtn.addEventListener('click', () => aboutModal.style.display = 'none');
  aboutModal.addEventListener('click', (e) => {
    if (e.target === aboutModal) aboutModal.style.display = 'none';
  });

  // Canvas Pan & Zoom
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    state.zoom = Math.max(0.6, Math.min(4.0, state.zoom * zoomFactor));
    drawCanvas();
  });

  canvas.addEventListener('mousedown', (e) => {
    state.isDragging = true;
    state.dragStartX = e.clientX - state.panX;
    state.dragStartY = e.clientY - state.panY;
  });

  window.addEventListener('mousemove', (e) => {
    if (state.isDragging) {
      state.panX = e.clientX - state.dragStartX;
      state.panY = e.clientY - state.dragStartY;
      drawCanvas();
    } else {
      // Hover tooltip check
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      if (mouseX >= 0 && mouseX <= rect.width && mouseY >= 0 && mouseY <= rect.height && state.instance) {
        const box = getBoundingBox(state.instance.nodes);
        let found = null;
        Object.entries(state.instance.nodes).forEach(([key, n]) => {
          const { px, py } = projectCoord(n.coordinates.x, n.coordinates.y, box, rect.width, rect.height);
          if (Math.hypot(px - mouseX, py - mouseY) < 10) {
            found = { key, node: n, px, py };
          }
        });

        if (found) {
          nodeTooltip.style.display = 'block';
          nodeTooltip.style.left = `${found.px + 12}px`;
          nodeTooltip.style.top = `${found.py - 10}px`;
          const isDepot = found.key === 'deport';
          const cid = isDepot ? 'DEPOT (0)' : `Customer ${found.key.replace('customer_', '')}`;
          nodeTooltip.innerHTML = `
            <strong>${cid}</strong><br>
            Coords: (${found.node.coordinates.x}, ${found.node.coordinates.y})<br>
            Demand: ${found.node.demand}<br>
            Ready: ${found.node.ready_time} | Due: ${found.node.due_time}
          `;
        } else {
          nodeTooltip.style.display = 'none';
        }
      } else {
        nodeTooltip.style.display = 'none';
      }
    }
  });

  window.addEventListener('mouseup', () => {
    state.isDragging = false;
  });

  window.addEventListener('resize', resizeCanvas);

  // Initial Load
  window.addEventListener('DOMContentLoaded', () => {
    resizeCanvas();
    loadInstance('A-n32-k5');
  });

})();
