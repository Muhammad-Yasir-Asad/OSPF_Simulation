// network-simulator.js
// Main JavaScript file for Network Simulator with OSPF - COMPLETE UPDATED VERSION

class NetworkSimulator {
    constructor() {
        this.currentMode = 'select';
        this.selectedDevice = null;
        this.selectedLink = null;
        this.selectedTool = 'router';
        this.devices = new Map();
        this.links = new Map();
        this.nextDeviceId = 1;
        this.nextLinkId = 1;
        this.currentCLIRouter = null;
        this.pingAnimation = null;
        this.ospfStepIndex = 0;
        this.ospfSteps = [];
        this.isOSPFAnimating = false;
        
        // Device counter by type
        this.deviceCounters = {
            router: 1,
            switch: 1,
            pc: 1,
            laptop: 1,
            phone: 1,
            server: 1
        };
        
        this.init();
    }

    init() {
        this.initWorkspace();
        this.initEventListeners();
        this.initToolbar();
        this.updateStatus();
        this.logCLI('Network Simulator initialized. Ready to create network topology.');
    }

    initWorkspace() {
        // Initialize Cytoscape for network visualization
        this.cy = cytoscape({
            container: document.getElementById('workspace'),
            elements: [],
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#00a8ff',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'font-size': '14px',
                        'font-weight': 'bold',
                        'width': 50,
                        'height': 50,
                        'border-width': 2,
                        'border-color': '#fff',
                        'cursor': 'pointer'
                    }
                },
                {
                    selector: 'node[type="router"]',
                    style: {
                        'background-color': '#ff9966',
                        'shape': 'round-rectangle'
                    }
                },
                {
                    selector: 'node[type="switch"]',
                    style: {
                        'background-color': '#66ccff',
                        'shape': 'diamond'
                    }
                },
                {
                    selector: 'node[type="pc"]',
                    style: {
                        'background-color': '#99ff99',
                        'shape': 'rectangle'
                    }
                },
                {
                    selector: 'node[type="laptop"]',
                    style: {
                        'background-color': '#ffcc66',
                        'shape': 'rectangle'
                    }
                },
                {
                    selector: 'node[type="phone"]',
                    style: {
                        'background-color': '#cc99ff',
                        'shape': 'ellipse'
                    }
                },
                {
                    selector: 'node[type="server"]',
                    style: {
                        'background-color': '#ff6666',
                        'shape': 'round-rectangle'
                    }
                },
                {
                    selector: 'node.selected',
                    style: {
                        'border-color': '#00ffaa',
                        'border-width': 4,
                        'border-style': 'solid'
                    }
                },
                {
                    selector: 'node.ospf-active',
                    style: {
                        'background-color': '#ffff00',
                        'color': '#000'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 3,
                        'line-color': '#ccc',
                        'target-arrow-color': '#ccc',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'color': '#fff',
                        'font-size': '12px',
                        'text-background-color': '#1a1a2e',
                        'text-background-opacity': 0.8,
                        'text-background-padding': '3px',
                        'text-wrap': 'wrap',
                        'text-max-width': 100,
                        'cursor': 'pointer'
                    }
                },
                {
                    selector: 'edge.selected',
                    style: {
                        'line-color': '#ffff00',
                        'target-arrow-color': '#ffff00',
                        'width': 5,
                        'z-index': 999
                    }
                },
                {
                    selector: 'edge[type="ospf"]',
                    style: {
                        'line-color': '#00ffaa',
                        'target-arrow-color': '#00ffaa',
                        'line-style': 'solid'
                    }
                },
                {
                    selector: 'edge[type="access"]',
                    style: {
                        'line-color': '#66ccff',
                        'target-arrow-color': '#66ccff',
                        'line-style': 'dashed'
                    }
                },
                {
                    selector: 'edge.ping-active',
                    style: {
                        'line-color': '#ffff00',
                        'target-arrow-color': '#ffff00',
                        'width': 6,
                        'line-style': 'solid'
                    }
                },
                {
                    selector: 'edge.ospf-hello',
                    style: {
                        'line-color': '#ff9966',
                        'target-arrow-color': '#ff9966',
                        'width': 4,
                        'line-style': 'dashed',
                        'z-index': 998
                    }
                },
                {
                    selector: 'edge.ospf-lsa',
                    style: {
                        'line-color': '#00ffaa',
                        'target-arrow-color': '#00ffaa',
                        'width': 4,
                        'line-style': 'dashed',
                        'z-index': 998
                    }
                },
                {
                    selector: 'edge.ospf-route',
                    style: {
                        'line-color': '#ff00ff',
                        'target-arrow-color': '#ff00ff',
                        'width': 4,
                        'z-index': 997
                    }
                },
                {
                    selector: 'edge.area-0',
                    style: {
                        'line-color': '#00ffaa',
                        'target-arrow-color': '#00ffaa'
                    }
                },
                {
                    selector: 'edge.area-1',
                    style: {
                        'line-color': '#ff9966',
                        'target-arrow-color': '#ff9966'
                    }
                },
                {
                    selector: 'edge.area-2',
                    style: {
                        'line-color': '#66ccff',
                        'target-arrow-color': '#66ccff'
                    }
                },
                {
                    selector: 'edge.area-3',
                    style: {
                        'line-color': '#cc99ff',
                        'target-arrow-color': '#cc99ff'
                    }
                },
                {
                    selector: 'edge.area-4',
                    style: {
                        'line-color': '#ffcc66',
                        'target-arrow-color': '#ffcc66'
                    }
                },
                {
                    selector: 'edge.area-5',
                    style: {
                        'line-color': '#ff6666',
                        'target-arrow-color': '#ff6666'
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 500
            },
            minZoom: 0.1,
            maxZoom: 5,
            zoomingEnabled: true,
            userZoomingEnabled: true,
            panningEnabled: true,
            userPanningEnabled: true,
            wheelSensitivity: 0.2
        });

        // Add workspace event listeners
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            this.selectDevice(node.id());
        });

        this.cy.on('tap', 'edge', (evt) => {
            const edge = evt.target;
            this.selectLink(edge.id());
        });

        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                // Clicked on background
                this.deselectDevice();
                this.deselectLink();
                
                if (this.currentMode === 'place') {
                    this.placeDevice(evt.position);
                }
            }
        });

        this.cy.on('cxttap', 'node', (evt) => {
            evt.preventDefault();
            const node = evt.target;
            this.showDeviceContextMenu(evt.originalEvent, node.id());
        });

        this.cy.on('cxttap', 'edge', (evt) => {
            evt.preventDefault();
            const edge = evt.target;
            this.showLinkContextMenu(evt.originalEvent, edge.id());
        });

        // Update positions when nodes are moved
        this.cy.on('position', 'node', (evt) => {
            const node = evt.target;
            const device = this.devices.get(node.id());
            if (device) {
                device.position = { x: node.position('x'), y: node.position('y') };
            }
        });
    }

    initEventListeners() {
        // Tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            if (btn.id.startsWith('tool-')) {
                btn.addEventListener('click', () => this.selectTool(btn.id.replace('tool-', '')));
            }
        });

        // Control buttons
        document.getElementById('btn-new').addEventListener('click', () => this.newProject());
        document.getElementById('btn-clear').addEventListener('click', () => this.clearAll());
        document.getElementById('btn-refresh-info').addEventListener('click', () => this.refreshDeviceInfo());
        document.getElementById('btn-simulate-ospf').addEventListener('click', () => this.simulateOSPF());
        document.getElementById('btn-step-ospf').addEventListener('click', () => this.stepOSPF());
        document.getElementById('btn-show-steps').addEventListener('click', () => this.toggleStepPanel());
        document.getElementById('btn-show-ospf').addEventListener('click', () => this.showOSPFAreas());
        document.getElementById('btn-show-routing').addEventListener('click', () => this.showRoutingTables());
        document.getElementById('btn-close-steps').addEventListener('click', () => this.hideStepPanel());

        // Example network buttons
        document.getElementById('btn-example-single').addEventListener('click', () => this.loadSingleAreaExample());
        document.getElementById('btn-example-multi').addEventListener('click', () => this.loadMultiAreaExample());
        document.getElementById('btn-example-complex').addEventListener('click', () => this.loadComplexExample());

        // Save/Load buttons
        document.getElementById('btn-save').addEventListener('click', () => this.saveProject());
        document.getElementById('btn-load').addEventListener('click', () => this.loadProject());

        // Workspace controls
        document.getElementById('btn-zoom-in').addEventListener('click', () => this.cy.zoom(this.cy.zoom() * 1.2));
        document.getElementById('btn-zoom-out').addEventListener('click', () => this.cy.zoom(this.cy.zoom() * 0.8));
        document.getElementById('btn-fit-view').addEventListener('click', () => this.cy.fit());
        document.getElementById('btn-reset-view').addEventListener('click', () => {
            this.cy.zoom(1);
            this.cy.center();
        });

        // CLI input
        document.getElementById('cli-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.processCLICommand();
            }
        });

        // Connection modal
        document.getElementById('btn-conn-cancel').addEventListener('click', () => this.hideModal('connection-modal'));
        document.getElementById('btn-conn-ok').addEventListener('click', () => this.createConnection());

        // Ping modal
        document.getElementById('btn-ping-cancel').addEventListener('click', () => this.hideModal('ping-modal'));
        document.getElementById('btn-ping-start').addEventListener('click', () => this.startPing());

        // Edit Link modal
        document.getElementById('btn-edit-cancel').addEventListener('click', () => this.hideModal('edit-link-modal'));
        document.getElementById('btn-edit-save').addEventListener('click', () => this.saveLinkChanges());

        // Context menu items
        document.getElementById('ctx-config').addEventListener('click', () => this.configureDevice());
        document.getElementById('ctx-cli').addEventListener('click', () => this.openCLI());
        document.getElementById('ctx-ping').addEventListener('click', () => this.startPingFromDevice());
        document.getElementById('ctx-delete').addEventListener('click', () => this.deleteSelectedDevice());
        document.getElementById('ctx-info').addEventListener('click', () => this.showDeviceInfo());
        document.getElementById('ctx-edit-link').addEventListener('click', () => this.editSelectedLink());
        document.getElementById('ctx-delete-link').addEventListener('click', () => this.deleteSelectedLink());
        document.getElementById('ctx-link-info').addEventListener('click', () => this.showLinkInfo());

        // Close context menu on click outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.context-menu')) {
                document.getElementById('context-menu').style.display = 'none';
            }
        });

        // Close step panel on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideStepPanel();
            }
        });
    }

    initToolbar() {
        // Set default active tool
        this.selectTool('router');
    }

    selectTool(tool) {
        this.currentMode = tool === 'select' ? 'select' : 'place';
        this.selectedTool = tool;
        
        // Update UI
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        const toolBtn = document.getElementById(`tool-${tool}`);
        if (toolBtn) toolBtn.classList.add('active');
        
        // Update status
        document.getElementById('status-mode').textContent = 
            this.currentMode === 'place' ? `Place ${tool}` : 'Select';
        
        // Special handling for connect mode
        if (tool === 'connect') {
            this.enterConnectMode();
        } else if (tool === 'ping') {
            this.enterPingMode();
        } else if (tool === 'delete') {
            this.enterDeleteMode();
        }
        
        this.logCLI(`Tool changed to: ${tool}`);
    }

    placeDevice(position) {
        const type = this.selectedTool;
        const id = `${type}${this.deviceCounters[type]++}`;
        
        // Create device object
        const device = {
            id: id,
            type: type,
            label: id,
            position: { x: position.x, y: position.y },
            ip: this.generateIP(type),
            interfaces: [],
            ospf: type === 'router' ? {
                enabled: true,
                area: 0,
                neighbors: [],
                lsdb: {},
                routingTable: []
            } : null,
            mac: this.generateMAC(),
            config: {
                hostname: id,
                enablePassword: 'cisco'
            }
        };
        
        // Add to devices map
        this.devices.set(id, device);
        
        // Add to cytoscape
        this.cy.add({
            group: 'nodes',
            data: { 
                id: id,
                label: id,
                type: type
            },
            position: { x: position.x, y: position.y },
            classes: type
        });
        
        // Update status
        this.updateStatus();
        this.logCLI(`Created ${type}: ${id} at (${Math.round(position.x)}, ${Math.round(position.y)})`);
        
        // Select the new device
        this.selectDevice(id);
    }

    selectDevice(deviceId) {
        // Deselect previous
        this.deselectDevice();
        this.deselectLink();
        
        // Select new
        this.selectedDevice = deviceId;
        const node = this.cy.getElementById(deviceId);
        node.addClass('selected');
        
        // Update device info
        this.updateDeviceInfo();
        
        // If in connect mode, handle connection
        if (this.currentMode === 'place' && this.selectedTool === 'connect') {
            this.handleConnectionSelection(deviceId);
        }
        
        // If in ping mode, handle ping source
        if (this.currentMode === 'place' && this.selectedTool === 'ping') {
            this.handlePingSelection(deviceId);
        }
    }

    deselectDevice() {
        if (this.selectedDevice) {
            const node = this.cy.getElementById(this.selectedDevice);
            node.removeClass('selected');
            this.selectedDevice = null;
            this.updateDeviceInfo();
        }
    }

    selectLink(linkId) {
        // Deselect device and previous link
        this.deselectDevice();
        this.deselectLink();
        
        // Select new link
        this.selectedLink = linkId;
        const edge = this.cy.getElementById(linkId);
        edge.addClass('selected');
        
        // Update link info display
        this.updateLinkInfo();
        
        this.logCLI(`Selected link: ${linkId}`);
    }

    deselectLink() {
        if (this.selectedLink) {
            const edge = this.cy.getElementById(this.selectedLink);
            edge.removeClass('selected');
            this.selectedLink = null;
        }
    }

    showDeviceContextMenu(event, deviceId) {
        const menu = document.getElementById('context-menu');
        
        // Show device items, hide link items
        document.getElementById('ctx-config').style.display = 'block';
        document.getElementById('ctx-cli').style.display = 'block';
        document.getElementById('ctx-ping').style.display = 'block';
        document.getElementById('ctx-delete').style.display = 'block';
        document.getElementById('ctx-info').style.display = 'block';
        document.getElementById('ctx-edit-link').style.display = 'none';
        document.getElementById('ctx-delete-link').style.display = 'none';
        document.getElementById('ctx-link-info').style.display = 'none';
        
        menu.style.display = 'block';
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        
        this.selectDevice(deviceId);
    }

    showLinkContextMenu(event, linkId) {
        const menu = document.getElementById('context-menu');
        
        // Show link items, hide device items
        document.getElementById('ctx-config').style.display = 'none';
        document.getElementById('ctx-cli').style.display = 'none';
        document.getElementById('ctx-ping').style.display = 'none';
        document.getElementById('ctx-delete').style.display = 'none';
        document.getElementById('ctx-info').style.display = 'none';
        document.getElementById('ctx-edit-link').style.display = 'block';
        document.getElementById('ctx-delete-link').style.display = 'block';
        document.getElementById('ctx-link-info').style.display = 'block';
        
        menu.style.display = 'block';
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        
        this.selectLink(linkId);
    }

    enterConnectMode() {
        this.connectionState = {
            step: 0,
            device1: null,
            device2: null
        };
        this.logCLI('Connect mode: Select first device');
    }

    handleConnectionSelection(deviceId) {
        if (this.connectionState.step === 0) {
            this.connectionState.device1 = deviceId;
            this.connectionState.step = 1;
            this.logCLI(`Selected ${deviceId} as first device. Now select second device.`);
        } else if (this.connectionState.step === 1) {
            this.connectionState.device2 = deviceId;
            
            // Show connection modal
            document.getElementById('conn-device1').value = this.connectionState.device1;
            document.getElementById('conn-device2').value = this.connectionState.device2;
            
            // Set default values based on device types
            const dev1 = this.devices.get(this.connectionState.device1);
            const dev2 = this.devices.get(this.connectionState.device2);
            
            if (dev1.type === 'router' && dev2.type === 'router') {
                document.getElementById('conn-type').value = 'ospf';
                document.getElementById('conn-cost').value = '10';
                document.getElementById('conn-area').value = '0';
            } else {
                document.getElementById('conn-type').value = 'access';
                document.getElementById('conn-cost').value = '1';
                document.getElementById('conn-area').value = '0';
            }
            
            this.showModal('connection-modal');
            
            // Reset for next connection
            this.connectionState = { step: 0, device1: null, device2: null };
            this.selectTool('select');
        }
    }

    createConnection() {
        const device1 = document.getElementById('conn-device1').value;
        const device2 = document.getElementById('conn-device2').value;
        const cost = parseInt(document.getElementById('conn-cost').value);
        const area = parseInt(document.getElementById('conn-area').value);
        const type = document.getElementById('conn-type').value;
        
        // Check if link already exists between these devices
        const existingLink = Array.from(this.links.values()).find(link => 
            (link.source === device1 && link.target === device2) ||
            (link.source === device2 && link.target === device1)
        );
        
        if (existingLink) {
            if (confirm('A link already exists between these devices. Edit existing link instead?')) {
                this.selectLink(existingLink.id);
                this.editSelectedLink();
                this.hideModal('connection-modal');
                return;
            } else {
                this.logCLI('Link creation cancelled. Link already exists.', 'error');
                this.hideModal('connection-modal');
                return;
            }
        }
        
        // Create link ID
        const linkId = `link${this.nextLinkId++}`;
        
        // Create link object
        const link = {
            id: linkId,
            source: device1,
            target: device2,
            type: type,
            cost: cost,
            area: area,
            label: type === 'ospf' ? `Cost: ${cost}, Area: ${area}` : 'Access'
        };
        
        // Add to links map
        this.links.set(linkId, link);
        
        // Update device interfaces
        const dev1 = this.devices.get(device1);
        const dev2 = this.devices.get(device2);
        
        const intf1 = {
            id: `eth${dev1.interfaces.length}`,
            connectedTo: device2,
            linkId: linkId,
            type: type,
            ip: this.generateInterfaceIP(),
            state: 'up'
        };
        
        const intf2 = {
            id: `eth${dev2.interfaces.length}`,
            connectedTo: device1,
            linkId: linkId,
            type: type,
            ip: this.generateInterfaceIP(),
            state: 'up'
        };
        
        dev1.interfaces.push(intf1);
        dev2.interfaces.push(intf2);
        
        // Add OSPF neighbor if applicable
        if (type === 'ospf' && dev1.type === 'router' && dev2.type === 'router') {
            if (!dev1.ospf) dev1.ospf = { enabled: true, area: 0, neighbors: [], lsdb: {}, routingTable: [] };
            if (!dev2.ospf) dev2.ospf = { enabled: true, area: 0, neighbors: [], lsdb: {}, routingTable: [] };
            
            dev1.ospf.neighbors.push({
                routerId: device2,
                state: 'Init',
                area: area,
                interface: intf1.id
            });
            dev2.ospf.neighbors.push({
                routerId: device1,
                state: 'Init',
                area: area,
                interface: intf2.id
            });
        }
        
        // Add to cytoscape
        this.cy.add({
            group: 'edges',
            data: {
                id: linkId,
                source: device1,
                target: device2,
                label: link.label,
                type: type,
                cost: cost,
                area: area
            }
        });
        
        // Hide modal and update
        this.hideModal('connection-modal');
        this.updateStatus();
        this.logCLI(`Created ${type} link between ${device1} and ${device2}`);
        
        // Trigger OSPF simulation if routers are connected
        if (type === 'ospf' && dev1.type === 'router' && dev2.type === 'router') {
            setTimeout(() => this.simulateOSPF(), 500);
        }
    }

    enterPingMode() {
        this.pingState = {
            step: 0,
            source: null,
            destination: null
        };
        this.logCLI('Ping mode: Select source device');
    }

    handlePingSelection(deviceId) {
        if (this.pingState.step === 0) {
            this.pingState.source = deviceId;
            this.pingState.step = 1;
            
            // Populate destination dropdown
            const dropdown = document.getElementById('ping-dst');
            dropdown.innerHTML = '';
            
            this.devices.forEach((device, id) => {
                if (id !== deviceId) {
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = `${id} (${device.type})`;
                    dropdown.appendChild(option);
                }
            });
            
            // Show ping modal
            document.getElementById('ping-src').value = deviceId;
            this.showModal('ping-modal');
            
            // Reset for next ping
            this.pingState = { step: 0, source: null, destination: null };
            this.selectTool('select');
        }
    }

    enterDeleteMode() {
        this.logCLI('Delete mode: Select device or link to delete');
    }

    async startPing() {
        const source = document.getElementById('ping-src').value;
        const destination = document.getElementById('ping-dst').value;
        const count = parseInt(document.getElementById('ping-count').value);
        
        this.hideModal('ping-modal');
        
        // Find path using Dijkstra's algorithm
        const path = this.findShortestPath(source, destination);
        
        if (path && path.length > 0) {
            this.logCLI(`Pinging ${destination} from ${source}:`);
            this.logCLI(`Path: ${path.join(' → ')}`);
            this.logCLI(`Total hops: ${path.length - 1}`);
            this.logCLI(`Status: Success`);
            
            // Animate ping
            this.animatePing(path, count);
        } else {
            this.logCLI(`Ping from ${source} to ${destination}: Failed - No path found`, 'error');
        }
    }

    findShortestPath(source, destination) {
        // Simple Dijkstra's implementation
        const distances = new Map();
        const previous = new Map();
        const unvisited = new Set();
        
        // Initialize distances
        this.devices.forEach((device, id) => {
            distances.set(id, id === source ? 0 : Infinity);
            previous.set(id, null);
            unvisited.add(id);
        });
        
        while (unvisited.size > 0) {
            // Find node with smallest distance
            let current = null;
            let minDist = Infinity;
            
            unvisited.forEach(id => {
                if (distances.get(id) < minDist) {
                    minDist = distances.get(id);
                    current = id;
                }
            });
            
            if (current === null || current === destination) break;
            
            unvisited.delete(current);
            
            // Get neighbors through links
            this.links.forEach(link => {
                if (link.source === current || link.target === current) {
                    const neighbor = link.source === current ? link.target : link.source;
                    if (unvisited.has(neighbor)) {
                        const alt = distances.get(current) + (link.cost || 1);
                        if (alt < distances.get(neighbor)) {
                            distances.set(neighbor, alt);
                            previous.set(neighbor, current);
                        }
                    }
                }
            });
        }
        
        // Reconstruct path
        const path = [];
        let current = destination;
        
        while (current !== null) {
            path.unshift(current);
            current = previous.get(current);
        }
        
        return path[0] === source ? path : [];
    }

    animatePing(path, count = 4) {
        const overlay = document.getElementById('ping-overlay');
        overlay.innerHTML = '';
        
        // Clear previous highlights
        this.cy.edges().removeClass('ping-active');
        
        // Highlight path edges
        for (let i = 0; i < path.length - 1; i++) {
            const source = path[i];
            const target = path[i + 1];
            
            // Find edge between these nodes
            const edges = this.cy.edges().filter(edge => 
                (edge.data('source') === source && edge.data('target') === target) ||
                (edge.data('source') === target && edge.data('target') === source)
            );
            
            edges.forEach(edge => edge.addClass('ping-active'));
        }
        
        // Create ping packet animation
        const packet = document.createElement('div');
        packet.className = 'ping-packet';
        overlay.appendChild(packet);
        
        // Get workspace bounding rect for coordinate conversion
        const workspaceRect = document.getElementById('workspace').getBoundingClientRect();
        
        let pingCount = 0;
        const animateOneWay = (forward = true) => {
            const pathToUse = forward ? path : [...path].reverse();
            
            let currentHop = 0;
            const animateStep = () => {
                if (currentHop >= pathToUse.length) {
                    // End of this trip
                    if (forward && pingCount < count * 2) { // Send reply
                        pingCount++;
                        setTimeout(() => animateOneWay(false), 300);
                    } else if (pingCount < count * 2 - 1) { // Send next ping
                        pingCount++;
                        setTimeout(() => animateOneWay(true), 300);
                    } else {
                        // Clean up after last ping
                        setTimeout(() => {
                            this.cy.edges().removeClass('ping-active');
                            overlay.innerHTML = '';
                        }, 500);
                    }
                    return;
                }
                
                const deviceId = pathToUse[currentHop];
                const node = this.cy.getElementById(deviceId);
                
                if (!node) {
                    currentHop++;
                    setTimeout(animateStep, 400);
                    return;
                }
                
                // Get current rendered position
                const renderedPos = node.renderedPosition();
                
                // Convert to absolute coordinates
                const absoluteX = renderedPos.x + workspaceRect.left;
                const absoluteY = renderedPos.y + workspaceRect.top;
                
                packet.style.left = `${absoluteX}px`;
                packet.style.top = `${absoluteY}px`;
                
                currentHop++;
                setTimeout(animateStep, 400);
            };
            
            animateStep();
        };
        
        // Start first ping
        animateOneWay(true);
    }

    // ========== EXAMPLE NETWORKS ==========

    loadSingleAreaExample() {
        this.clearAll();
        this.logCLI('Loading Single Area OSPF Example...', 'info');
        
        // Create 4 routers in area 0
        const routers = [];
        for (let i = 1; i <= 4; i++) {
            const routerId = `R${i}`;
            const router = {
                id: routerId,
                type: 'router',
                label: routerId,
                position: { x: i * 150, y: 200 },
                ip: `10.0.${i}.1`,
                interfaces: [],
                ospf: {
                    enabled: true,
                    area: 0,
                    neighbors: [],
                    lsdb: {},
                    routingTable: []
                },
                mac: this.generateMAC()
            };
            this.devices.set(routerId, router);
            
            // Add to cytoscape
            this.cy.add({
                group: 'nodes',
                data: {
                    id: routerId,
                    label: routerId,
                    type: 'router'
                },
                position: { x: i * 150, y: 200 }
            });
            routers.push(router);
        }
        
        // Create connections (partial mesh)
        const connections = [
            { from: 'R1', to: 'R2', cost: 10 },
            { from: 'R2', to: 'R3', cost: 20 },
            { from: 'R3', to: 'R4', cost: 10 },
            { from: 'R1', to: 'R4', cost: 30 },
            { from: 'R2', to: 'R4', cost: 15 }
        ];
        
        connections.forEach((conn, index) => {
            const linkId = `link${index + 1}`;
            this.createExampleLink(conn.from, conn.to, conn.cost, 0, linkId);
        });
        
        // Add some end devices
        const devices = [
            { id: 'PC1', type: 'pc', router: 'R1', ip: '192.168.10.10', x: 150, y: 350 },
            { id: 'Server1', type: 'server', router: 'R2', ip: '192.168.20.10', x: 300, y: 350 },
            { id: 'Laptop1', type: 'laptop', router: 'R3', ip: '192.168.30.10', x: 450, y: 350 },
            { id: 'Phone1', type: 'phone', router: 'R4', ip: '192.168.40.10', x: 600, y: 350 }
        ];
        
        devices.forEach(device => {
            const deviceId = device.id;
            const deviceObj = {
                id: deviceId,
                type: device.type,
                label: deviceId,
                position: { x: device.x, y: device.y },
                ip: device.ip,
                interfaces: [],
                mac: this.generateMAC()
            };
            
            this.devices.set(deviceId, deviceObj);
            
            // Add to cytoscape
            this.cy.add({
                group: 'nodes',
                data: {
                    id: deviceId,
                    label: deviceId,
                    type: device.type
                },
                position: { x: device.x, y: device.y }
            });
            
            // Connect to router
            const linkId = `access_${deviceId}`;
            this.createExampleLink(device.router, deviceId, 1, 0, linkId, 'access');
        });
        
        this.updateStatus();
        this.cy.fit();
        this.logCLI('Single Area OSPF Example loaded successfully!', 'info');
        this.logCLI('Network: 4 routers in Area 0 (backbone) with 4 end devices');
        this.logCLI('Run OSPF simulation to see routing tables and LSDB');
    }

    loadMultiAreaExample() {
        this.clearAll();
        this.logCLI('Loading Multi-Area OSPF Example...', 'info');
        
        // Create Area Border Routers (ABRs) - connected to backbone
        const abrPositions = [
            { id: 'ABR1', x: 200, y: 200, area: 0 },
            { id: 'ABR2', x: 400, y: 200, area: 0 },
            { id: 'ABR3', x: 600, y: 200, area: 0 }
        ];
        
        abrPositions.forEach((abr, index) => {
            const router = {
                id: abr.id,
                type: 'router',
                label: abr.id,
                position: { x: abr.x, y: abr.y },
                ip: `10.0.${index + 1}.1`,
                interfaces: [],
                ospf: {
                    enabled: true,
                    area: 0,
                    neighbors: [],
                    lsdb: {},
                    routingTable: []
                },
                mac: this.generateMAC()
            };
            this.devices.set(abr.id, router);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: abr.id,
                    label: abr.id,
                    type: 'router'
                },
                position: { x: abr.x, y: abr.y }
            });
        });
        
        // Connect ABRs in backbone (Area 0)
        const backboneConnections = [
            { from: 'ABR1', to: 'ABR2', cost: 10, area: 0 },
            { from: 'ABR2', to: 'ABR3', cost: 15, area: 0 }
        ];
        
        backboneConnections.forEach((conn, index) => {
            const linkId = `backbone${index + 1}`;
            this.createExampleLink(conn.from, conn.to, conn.cost, conn.area, linkId);
        });
        
        // Create internal routers for each area
        const areaRouters = [
            // Area 1 routers (connected to ABR1)
            { id: 'R1-A1', abr: 'ABR1', area: 1, x: 100, y: 100 },
            { id: 'R2-A1', abr: 'ABR1', area: 1, x: 200, y: 100 },
            
            // Area 2 routers (connected to ABR2)
            { id: 'R1-A2', abr: 'ABR2', area: 2, x: 400, y: 100 },
            { id: 'R2-A2', abr: 'ABR2', area: 2, x: 500, y: 100 },
            
            // Area 3 routers (connected to ABR3)
            { id: 'R1-A3', abr: 'ABR3', area: 3, x: 600, y: 100 },
            { id: 'R2-A3', abr: 'ABR3', area: 3, x: 700, y: 100 }
        ];
        
        // Create area routers
        areaRouters.forEach(router => {
            const routerObj = {
                id: router.id,
                type: 'router',
                label: router.id,
                position: { x: router.x, y: router.y },
                ip: this.generateIP('router'),
                interfaces: [],
                ospf: {
                    enabled: true,
                    area: router.area,
                    neighbors: [],
                    lsdb: {},
                    routingTable: []
                },
                mac: this.generateMAC()
            };
            this.devices.set(router.id, routerObj);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: router.id,
                    label: router.id,
                    type: 'router'
                },
                position: { x: router.x, y: router.y }
            });
            
            // Connect to ABR
            const linkId = `area${router.area}_${router.id}`;
            this.createExampleLink(router.abr, router.id, 5, router.area, linkId);
        });
        
        // Create area mesh networks
        const areaMesh = [
            // Area 1 mesh
            { from: 'R1-A1', to: 'R2-A1', cost: 10, area: 1 },
            
            // Area 2 mesh
            { from: 'R1-A2', to: 'R2-A2', cost: 15, area: 2 },
            
            // Area 3 mesh
            { from: 'R1-A3', to: 'R2-A3', cost: 20, area: 3 }
        ];
        
        areaMesh.forEach((conn, index) => {
            const linkId = `mesh${index + 1}`;
            this.createExampleLink(conn.from, conn.to, conn.cost, conn.area, linkId);
        });
        
        // Add end devices in each area
        const areaDevices = [
            // Area 1 devices
            { id: 'PC-A1', type: 'pc', router: 'R1-A1', area: 1, x: 50, y: 50 },
            { id: 'Server-A1', type: 'server', router: 'R2-A1', area: 1, x: 250, y: 50 },
            
            // Area 2 devices
            { id: 'Laptop-A2', type: 'laptop', router: 'R1-A2', area: 2, x: 350, y: 50 },
            { id: 'Phone-A2', type: 'phone', router: 'R2-A2', area: 2, x: 550, y: 50 },
            
            // Area 3 devices
            { id: 'PC-A3', type: 'pc', router: 'R1-A3', area: 3, x: 550, y: 50 },
            { id: 'Server-A3', type: 'server', router: 'R2-A3', area: 3, x: 750, y: 50 }
        ];
        
        areaDevices.forEach(device => {
            const deviceId = device.id;
            const deviceObj = {
                id: deviceId,
                type: device.type,
                label: deviceId,
                position: { x: device.x, y: device.y },
                ip: this.generateIP(device.type),
                interfaces: [],
                mac: this.generateMAC()
            };
            
            this.devices.set(deviceId, deviceObj);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: deviceId,
                    label: deviceId,
                    type: device.type
                },
                position: { x: device.x, y: device.y }
            });
            
            // Connect to router
            const linkId = `access_${deviceId}`;
            this.createExampleLink(device.router, deviceId, 1, device.area, linkId, 'access');
        });
        
        this.updateStatus();
        this.cy.fit();
        this.logCLI('Multi-Area OSPF Example loaded successfully!', 'info');
        this.logCLI('Network Structure:');
        this.logCLI('  - Area 0 (Backbone): ABR1, ABR2, ABR3');
        this.logCLI('  - Area 1: R1-A1, R2-A1 (connected to ABR1)');
        this.logCLI('  - Area 2: R1-A2, R2-A2 (connected to ABR2)');
        this.logCLI('  - Area 3: R1-A3, R2-A3 (connected to ABR3)');
        this.logCLI('Run OSPF simulation to see inter-area routing!');
    }

    loadComplexExample() {
        this.clearAll();
        this.logCLI('Loading Complex Network Example...', 'info');
        
        // Create core routers (Area 0)
        const coreRouters = [
            { id: 'Core1', x: 300, y: 300, area: 0 },
            { id: 'Core2', x: 500, y: 300, area: 0 },
            { id: 'Core3', x: 400, y: 200, area: 0 }
        ];
        
        coreRouters.forEach((router, index) => {
            const routerObj = {
                id: router.id,
                type: 'router',
                label: router.id,
                position: { x: router.x, y: router.y },
                ip: `172.16.${index + 1}.1`,
                interfaces: [],
                ospf: {
                    enabled: true,
                    area: router.area,
                    neighbors: [],
                    lsdb: {},
                    routingTable: []
                },
                mac: this.generateMAC()
            };
            this.devices.set(router.id, routerObj);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: router.id,
                    label: router.id,
                    type: 'router'
                },
                position: { x: router.x, y: router.y }
            });
        });
        
        // Connect core routers (triangle)
        const coreConnections = [
            { from: 'Core1', to: 'Core2', cost: 5, area: 0 },
            { from: 'Core2', to: 'Core3', cost: 5, area: 0 },
            { from: 'Core3', to: 'Core1', cost: 5, area: 0 }
        ];
        
        coreConnections.forEach((conn, index) => {
            const linkId = `core${index + 1}`;
            this.createExampleLink(conn.from, conn.to, conn.cost, conn.area, linkId);
        });
        
        // Create distribution layer (different areas)
        const distributionRouters = [
            // Connected to Core1
            { id: 'Dist1-A1', core: 'Core1', area: 1, x: 200, y: 200 },
            { id: 'Dist2-A1', core: 'Core1', area: 1, x: 200, y: 400 },
            
            // Connected to Core2
            { id: 'Dist1-A2', core: 'Core2', area: 2, x: 600, y: 200 },
            { id: 'Dist2-A2', core: 'Core2', area: 2, x: 600, y: 400 },
            
            // Connected to Core3
            { id: 'Dist1-A3', core: 'Core3', area: 3, x: 400, y: 50 }
        ];
        
        distributionRouters.forEach(router => {
            const routerObj = {
                id: router.id,
                type: 'router',
                label: router.id,
                position: { x: router.x, y: router.y },
                ip: this.generateIP('router'),
                interfaces: [],
                ospf: {
                    enabled: true,
                    area: router.area,
                    neighbors: [],
                    lsdb: {},
                    routingTable: []
                },
                mac: this.generateMAC()
            };
            this.devices.set(router.id, routerObj);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: router.id,
                    label: router.id,
                    type: 'router'
                },
                position: { x: router.x, y: router.y }
            });
            
            // Connect to core
            const linkId = `dist_${router.id}`;
            this.createExampleLink(router.core, router.id, 10, router.area, linkId);
        });
        
        // Create access layer switches
        const switches = [
            { id: 'SW1-A1', router: 'Dist1-A1', area: 1, x: 100, y: 150 },
            { id: 'SW2-A1', router: 'Dist2-A1', area: 1, x: 100, y: 450 },
            { id: 'SW1-A2', router: 'Dist1-A2', area: 2, x: 700, y: 150 },
            { id: 'SW2-A2', router: 'Dist2-A2', area: 2, x: 700, y: 450 },
            { id: 'SW1-A3', router: 'Dist1-A3', area: 3, x: 400, y: 0 }
        ];
        
        switches.forEach(sw => {
            const switchObj = {
                id: sw.id,
                type: 'switch',
                label: sw.id,
                position: { x: sw.x, y: sw.y },
                ip: this.generateIP('switch'),
                interfaces: [],
                mac: this.generateMAC()
            };
            this.devices.set(sw.id, switchObj);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: sw.id,
                    label: sw.id,
                    type: 'switch'
                },
                position: { x: sw.x, y: sw.y }
            });
            
            // Connect to distribution router
            const linkId = `switch_${sw.id}`;
            this.createExampleLink(sw.router, sw.id, 1, sw.area, linkId, 'access');
        });
        
        // Create end devices
        const endDevices = [
            // Area 1 devices
            { id: 'PC1-A1', type: 'pc', switch: 'SW1-A1', x: 50, y: 100 },
            { id: 'PC2-A1', type: 'pc', switch: 'SW1-A1', x: 50, y: 200 },
            { id: 'Server-A1', type: 'server', switch: 'SW2-A1', x: 50, y: 400 },
            { id: 'Laptop-A1', type: 'laptop', switch: 'SW2-A1', x: 50, y: 500 },
            
            // Area 2 devices
            { id: 'PC1-A2', type: 'pc', switch: 'SW1-A2', x: 750, y: 100 },
            { id: 'PC2-A2', type: 'pc', switch: 'SW1-A2', x: 750, y: 200 },
            { id: 'Server-A2', type: 'server', switch: 'SW2-A2', x: 750, y: 400 },
            { id: 'Phone-A2', type: 'phone', switch: 'SW2-A2', x: 750, y: 500 },
            
            // Area 3 devices
            { id: 'Admin-PC', type: 'pc', switch: 'SW1-A3', x: 350, y: -50 },
            { id: 'NAS', type: 'server', switch: 'SW1-A3', x: 450, y: -50 }
        ];
        
        endDevices.forEach(device => {
            const deviceId = device.id;
            const deviceObj = {
                id: deviceId,
                type: device.type,
                label: deviceId,
                position: { x: device.x, y: device.y },
                ip: this.generateIP(device.type),
                interfaces: [],
                mac: this.generateMAC()
            };
            
            this.devices.set(deviceId, deviceObj);
            
            this.cy.add({
                group: 'nodes',
                data: {
                    id: deviceId,
                    label: deviceId,
                    type: device.type
                },
                position: { x: device.x, y: device.y }
            });
            
            // Connect to switch
            const linkId = `device_${deviceId}`;
            this.createExampleLink(device.switch, deviceId, 1, 0, linkId, 'access');
        });
        
        this.updateStatus();
        this.cy.fit();
        this.logCLI('Complex Network Example loaded successfully!', 'info');
        this.logCLI('Network Hierarchy:');
        this.logCLI('  - Core Layer: Core1, Core2, Core3 (Area 0)');
        this.logCLI('  - Distribution Layer: Routers in Areas 1, 2, 3');
        this.logCLI('  - Access Layer: Switches connected to distribution routers');
        this.logCLI('  - End Devices: PCs, servers, laptops, phones');
        this.logCLI('Test inter-area communication and OSPF path selection!');
    }

    createExampleLink(sourceId, targetId, cost, area, linkId, type = 'ospf') {
        const source = this.devices.get(sourceId);
        const target = this.devices.get(targetId);
        
        if (!source || !target) return;
        
        const link = {
            id: linkId,
            source: sourceId,
            target: targetId,
            type: type,
            cost: cost,
            area: area,
            label: type === 'ospf' ? `Cost: ${cost}, Area: ${area}` : 'Access'
        };
        
        this.links.set(linkId, link);
        
        // Add interfaces
        source.interfaces.push({
            id: `eth${source.interfaces.length}`,
            connectedTo: targetId,
            linkId: linkId,
            type: type,
            ip: this.generateInterfaceIP(),
            state: 'up'
        });
        
        target.interfaces.push({
            id: `eth${target.interfaces.length}`,
            connectedTo: sourceId,
            linkId: linkId,
            type: type,
            ip: this.generateInterfaceIP(),
            state: 'up'
        });
        
        // Add OSPF neighbors if applicable
        if (type === 'ospf' && source.type === 'router' && target.type === 'router') {
            if (!source.ospf) source.ospf = { enabled: true, area: area, neighbors: [], lsdb: {}, routingTable: [] };
            if (!target.ospf) target.ospf = { enabled: true, area: area, neighbors: [], lsdb: {}, routingTable: [] };
            
            source.ospf.neighbors.push({
                routerId: targetId,
                state: '2-Way',
                area: area,
                interface: source.interfaces[source.interfaces.length - 1].id
            });
            
            target.ospf.neighbors.push({
                routerId: sourceId,
                state: '2-Way',
                area: area,
                interface: target.interfaces[target.interfaces.length - 1].id
            });
        }
        
        // Add to cytoscape
        this.cy.add({
            group: 'edges',
            data: {
                id: linkId,
                source: sourceId,
                target: targetId,
                label: link.label,
                type: type,
                cost: cost,
                area: area
            }
        });
    }

    // ========== OSPF SIMULATION ==========

    async simulateOSPF() {
        this.logCLI('Starting OSPF simulation...', 'info');
        
        // Get topology data
        const topology = {
            devices: Array.from(this.devices.values()).map(device => ({
                id: device.id,
                type: device.type,
                label: device.label,
                position: device.position,
                ip: device.ip,
                interfaces: device.interfaces || [],
                ospf: device.ospf || (device.type === 'router' ? {
                    enabled: true,
                    area: 0,
                    neighbors: [],
                    lsdb: {},
                    routingTable: []
                } : null),
                mac: device.mac || "00:00:00:00:00:00"
            })),
            links: Array.from(this.links.values()).map(link => ({
                id: link.id,
                source: link.source,
                target: link.target,
                type: link.type,
                cost: link.cost || 1,
                area: link.area || 0,
                label: link.label || ""
            })),
            timestamp: new Date().toISOString()
        };
        
        // Prepare request data
        const requestData = {
            topology: topology,
            step_by_step: true
        };
        
        try {
            const response = await fetch('http://localhost:8000/ospf', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.logCLI('OSPF simulation completed successfully', 'info');
                this.logCLI(`Areas found: ${Object.keys(result.areas || {}).length}`);
                if (result.abrs) {
                    this.logCLI(`ABRs identified: ${result.abrs.join(', ')}`);
                }
                
                // Store steps for step-by-step animation
                if (result.steps) {
                    this.ospfSteps = result.steps;
                    this.ospfStepIndex = 0;
                    this.updateStepPanel();
                    this.logCLI(`OSPF simulation has ${this.ospfSteps.length} steps. Use 'Step OSPF' button to animate.`);
                }
                
                // Update routing tables
                if (result.routing_tables && result.routing_tables.length > 0) {
                    result.routing_tables.forEach(rt => {
                        const device = this.devices.get(rt.router);
                        if (device && device.ospf) {
                            device.ospf.routingTable = rt.routes || [];
                            device.ospf.lsdb = rt.lsdb || {};
                            device.ospf.neighbors = rt.neighbors || [];
                            device.ospf.is_abr = rt.is_abr || false;
                        }
                    });
                    this.logCLI(`Updated ${result.routing_tables.length} routing tables`);
                }
                
                // Highlight ABRs
                if (result.abrs) {
                    result.abrs.forEach(abrId => {
                        const node = this.cy.getElementById(abrId);
                        if (node) {
                            node.style('border-color', '#ff00ff');
                            node.style('border-width', 4);
                            node.style('border-style', 'double');
                        }
                    });
                }
                
                // Update device info
                this.updateDeviceInfo();
                this.updateStatus();
                
                // Show step panel
                this.showStepPanel();
                
            } else {
                this.logCLI(`OSPF simulation failed: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error("OSPF simulation error:", error);
            this.logCLI(`Network error: ${error.message}`, 'error');
            this.logCLI('Running local OSPF simulation...', 'info');
            this.runLocalOSPF();
        }
    }

    runLocalOSPF() {
        // Simple local OSPF simulation for testing
        this.ospfSteps = [
            {
                type: "hello",
                description: "Routers send Hello packets to discover neighbors",
                router_id: "R1",
                neighbors: ["R2", "R4"],
                neighbor_state: "2-Way"
            },
            {
                type: "lsa_generation",
                description: "Router R1 generates LSA with its link state",
                router_id: "R1",
                lsa_id: "LSA-R1",
                links_count: 2
            },
            {
                type: "lsa_flooding",
                description: "Flooding LSA from R1 to R2",
                source: "R1",
                target: "R2",
                lsa_id: "LSA-R1"
            },
            {
                type: "dijkstra",
                description: "Router R1 runs Dijkstra's algorithm",
                router_id: "R1",
                destinations_found: 3
            },
            {
                type: "routing_update",
                description: "Router R1 updates routing table",
                router_id: "R1",
                routes_count: 3
            }
        ];
        
        this.ospfStepIndex = 0;
        this.updateStepPanel();
        this.showStepPanel();
        this.logCLI('Local OSPF simulation completed with 5 steps');
        
        // Update sample routing tables for all routers
        this.devices.forEach((device, id) => {
            if (device.type === 'router' && device.ospf) {
                // Create sample routing table
                const routes = [];
                this.devices.forEach((targetDevice, targetId) => {
                    if (targetId !== id && targetDevice.type === 'router') {
                        routes.push({
                            destination: targetId,
                            next_hop: this.findNextHop(id, targetId),
                            cost: Math.floor(Math.random() * 50) + 1,
                            type: "intra-area"
                        });
                    }
                });
                device.ospf.routingTable = routes;
            }
        });
    }

    findNextHop(source, destination) {
        // Simple next hop finding for local simulation
        const neighbors = this.devices.get(source)?.ospf?.neighbors || [];
        if (neighbors.length > 0) {
            return neighbors[0].routerId;
        }
        return null;
    }

    stepOSPF() {
        if (!this.ospfSteps || this.ospfSteps.length === 0) {
            this.logCLI('No OSPF steps available. Run OSPF simulation first.', 'error');
            return;
        }
        
        if (this.ospfStepIndex >= this.ospfSteps.length) {
            this.logCLI('OSPF simulation completed. Reset to start again.', 'info');
            this.ospfStepIndex = 0;
            this.updateStepPanel();
            return;
        }
        
        const step = this.ospfSteps[this.ospfStepIndex];
        this.logCLI(`=== OSPF Step ${this.ospfStepIndex + 1}/${this.ospfSteps.length}: ${step.description} ===`, 'ospf-step');
        
        // Execute step
        this.executeOSPFStep(step);
        
        // Update step panel
        this.updateStepPanel();
        
        this.ospfStepIndex++;
        
        // If we've completed all steps, reset index
        if (this.ospfStepIndex >= this.ospfSteps.length) {
            this.logCLI('OSPF simulation completed!', 'info');
        }
    }

    executeOSPFStep(step) {
        switch (step.type) {
            case 'hello':
                this.animateOSPFHello(step);
                break;
            case 'lsa_generation':
                this.animateLSAGeneration(step);
                break;
            case 'lsa_flooding':
                this.animateLSAFlooding(step);
                break;
            case 'dijkstra':
                this.animateDijkstra(step);
                break;
            case 'routing_update':
                this.animateRoutingUpdate(step);
                break;
            case 'neighbor_update':
                this.updateNeighborStates(step);
                break;
        }
        
        // Update device info if a specific device is selected
        if (step.router_id && this.selectedDevice === step.router_id) {
            this.updateDeviceInfo();
        }
    }

    animateOSPFHello(step) {
        // Highlight router
        const routerNode = this.cy.getElementById(step.router_id);
        if (routerNode) {
            routerNode.animate({
                style: { 'background-color': '#ffcc00' }
            }, { duration: 500 });
            
            setTimeout(() => {
                routerNode.style('background-color', '#ff9966');
            }, 1500);
        }
        
        // Animate Hello packets on edges
        step.neighbors.forEach(neighborId => {
            const edge = this.cy.edges().filter(edge => 
                (edge.data('source') === step.router_id && edge.data('target') === neighborId) ||
                (edge.data('source') === neighborId && edge.data('target') === step.router_id)
            );
            
            if (edge.length > 0) {
                edge.addClass('ospf-hello');
                setTimeout(() => edge.removeClass('ospf-hello'), 1000);
                
                // Animate packet
                this.animatePacket(step.router_id, neighborId, '#ff9966', 'HELLO');
            }
        });
        
        // Update neighbor states
        setTimeout(() => {
            const router = this.devices.get(step.router_id);
            if (router && router.ospf) {
                step.neighbors.forEach(neighborId => {
                    const neighbor = router.ospf.neighbors.find(n => n.routerId === neighborId);
                    if (neighbor) {
                        neighbor.state = step.neighbor_state || '2-Way';
                    }
                });
            }
            this.updateDeviceInfo();
        }, 1000);
    }

    animateLSAGeneration(step) {
        // Highlight router
        const routerNode = this.cy.getElementById(step.router_id);
        if (routerNode) {
            routerNode.animate({
                style: { 'background-color': '#00ccff' }
            }, { duration: 500 });
            
            setTimeout(() => {
                routerNode.style('background-color', routerNode.data('type') === 'router' ? '#ff9966' : '#00a8ff');
            }, 1500);
        }
        
        // Update LSDB display
        setTimeout(() => {
            const router = this.devices.get(step.router_id);
            if (router && router.ospf) {
                router.ospf.lsdb = step.lsdb || router.ospf.lsdb || {};
            }
            this.updateDeviceInfo();
        }, 500);
    }

    animateLSAFlooding(step) {
        // Animate LSA packet along edge
        const edge = this.cy.edges().filter(edge => 
            (edge.data('source') === step.source && edge.data('target') === step.target) ||
            (edge.data('source') === step.target && edge.data('target') === step.source)
        );
        
        if (edge.length > 0) {
            edge.addClass('ospf-lsa');
            setTimeout(() => edge.removeClass('ospf-lsa'), 1500);
            
            // Animate packet
            this.animatePacket(step.source, step.target, '#00ffaa', 'LSA');
        }
        
        // Update target router's LSDB
        setTimeout(() => {
            const router = this.devices.get(step.target);
            if (router && router.ospf) {
                router.ospf.lsdb = step.lsdb_update || router.ospf.lsdb;
            }
            this.updateDeviceInfo();
        }, 1500);
    }

    animateDijkstra(step) {
        // Highlight router
        const routerNode = this.cy.getElementById(step.router_id);
        if (routerNode) {
            routerNode.animate({
                style: { 'background-color': '#00ffaa' }
            }, { duration: 1000 });
            
            setTimeout(() => {
                routerNode.style('background-color', routerNode.data('type') === 'router' ? '#ff9966' : '#00a8ff');
            }, 2000);
        }
        
        // Animate edges in the shortest path tree
        if (step.shortest_path_edges) {
            step.shortest_path_edges.forEach(([src, dst]) => {
                const edge = this.cy.edges().filter(edge => 
                    (edge.data('source') === src && edge.data('target') === dst) ||
                    (edge.data('source') === dst && edge.data('target') === src)
                );
                
                if (edge.length > 0) {
                    edge.animate({
                        style: { 'line-color': '#ffff00', 'width': 5 }
                    }, { duration: 1000 });
                    
                    setTimeout(() => {
                        edge.animate({
                            style: { 'line-color': edge.data('type') === 'ospf' ? '#00ffaa' : '#66ccff', 'width': 3 }
                        }, { duration: 500 });
                    }, 2000);
                }
            });
        }
    }

    animateRoutingUpdate(step) {
        const router = this.devices.get(step.router_id);
        if (router && router.ospf) {
            router.ospf.routingTable = step.routes || router.ospf.routingTable;
            
            // Flash router to indicate update
            const routerNode = this.cy.getElementById(step.router_id);
            if (routerNode) {
                routerNode.animate({
                    style: { 'background-color': '#9966ff' }
                }, { duration: 300 });
                
                setTimeout(() => {
                    routerNode.animate({
                        style: { 'background-color': '#ff9966' }
                    }, { duration: 300 });
                }, 600);
            }
        }
        
        this.updateDeviceInfo();
    }

    animatePacket(source, target, color, type) {
        const overlay = document.getElementById('ospf-overlay');
        const packet = document.createElement('div');
        packet.className = 'ospf-packet';
        packet.style.backgroundColor = color;
        packet.style.boxShadow = `0 0 10px ${color}`;
        overlay.appendChild(packet);
        
        const workspaceRect = document.getElementById('workspace').getBoundingClientRect();
        
        const sourceNode = this.cy.getElementById(source);
        const targetNode = this.cy.getElementById(target);
        
        if (!sourceNode || !targetNode) {
            overlay.removeChild(packet);
            return;
        }
        
        const startPos = sourceNode.renderedPosition();
        const endPos = targetNode.renderedPosition();
        
        const startX = startPos.x + workspaceRect.left;
        const startY = startPos.y + workspaceRect.top;
        const endX = endPos.x + workspaceRect.left;
        const endY = endPos.y + workspaceRect.top;
        
        packet.style.left = `${startX}px`;
        packet.style.top = `${startY}px`;
        
        setTimeout(() => {
            packet.style.left = `${endX}px`;
            packet.style.top = `${endY}px`;
            
            setTimeout(() => {
                if (packet.parentNode === overlay) {
                    overlay.removeChild(packet);
                }
            }, 500);
        }, 100);
    }

    updateNeighborStates(step) {
        if (step.neighbor_updates) {
            step.neighbor_updates.forEach(update => {
                const router = this.devices.get(update.router_id);
                if (router && router.ospf) {
                    const neighbor = router.ospf.neighbors.find(n => n.routerId === update.neighbor_id);
                    if (neighbor) {
                        neighbor.state = update.new_state;
                    }
                }
            });
        }
        this.updateDeviceInfo();
    }

    updateDeviceInfo() {
        const container = document.getElementById('device-info-content');
        
        if (this.selectedLink) {
            this.updateLinkInfo();
            return;
        }
        
        if (!this.selectedDevice) {
            container.innerHTML = '<div class="device-info"><h3>No Device Selected</h3><p>Click on a device to view its information</p></div>';
            return;
        }
        
        const device = this.devices.get(this.selectedDevice);
        if (!device) return;
        
        // Get areas this device is connected to
        const areas = new Set();
        device.interfaces.forEach(intf => {
            const link = this.links.get(intf.linkId);
            if (link && link.type === 'ospf') {
                areas.add(link.area);
            }
        });
        const areaList = Array.from(areas);
        
        let html = `
            <div class="device-info">
                <h3><i class="fas fa-${this.getDeviceIcon(device.type)}"></i> ${device.id}</h3>
                <div class="device-property">
                    <span>Type:</span>
                    <span>${device.type.toUpperCase()}</span>
                </div>
                <div class="device-property">
                    <span>IP Address:</span>
                    <span>${device.ip}</span>
                </div>
                <div class="device-property">
                    <span>MAC Address:</span>
                    <span>${device.mac}</span>
                </div>
                <div class="device-property">
                    <span>Interfaces:</span>
                    <span>${device.interfaces.length}</span>
                </div>
        `;
        
        if (device.ospf) {
            html += `
                <div class="device-property">
                    <span>OSPF Area:</span>
                    <span>${device.ospf.area}</span>
                </div>
                <div class="device-property">
                    <span>Connected Areas:</span>
                    <span>${areaList.join(', ') || 'None'}</span>
                </div>
                <div class="device-property">
                    <span>OSPF Neighbors:</span>
                    <span>${device.ospf.neighbors.length}</span>
                </div>
                <div class="device-property">
                    <span>LSDB Size:</span>
                    <span>${Object.keys(device.ospf.lsdb).length} LSAs</span>
                </div>
                <div class="device-property">
                    <span>Routing Table:</span>
                    <span>${device.ospf.routingTable.length} routes</span>
                </div>
                ${device.ospf.is_abr ? `<div class="device-property" style="color: #ff00ff;">
                    <span><i class="fas fa-exchange-alt"></i> ABR:</span>
                    <span>Yes</span>
                </div>` : ''}
            `;
        }
        
        html += `</div>`;
        
        // Add interfaces details
        if (device.interfaces.length > 0) {
            html += `<div class="device-info"><h3>Interfaces</h3>`;
            device.interfaces.forEach(intf => {
                const linkedDevice = this.devices.get(intf.connectedTo);
                const link = this.links.get(intf.linkId);
                html += `
                    <div class="device-property">
                        <span>${intf.id}:</span>
                        <span>${intf.ip} → ${intf.connectedTo} (${intf.type})</span>
                    </div>
                    ${link ? `<div class="device-property" style="font-size: 11px; color: #aaa;">
                        <span>Link:</span>
                        <span>${link.type === 'ospf' ? `Cost: ${link.cost}, Area: ${link.area}` : 'Access Link'}</span>
                    </div>` : ''}
                `;
            });
            html += `</div>`;
        }
        
        // Add OSPF neighbors for routers
        if (device.ospf && device.ospf.neighbors.length > 0) {
            html += `<div class="device-info"><h3>OSPF Neighbors</h3>`;
            device.ospf.neighbors.forEach(neighbor => {
                html += `
                    <div class="device-property">
                        <span>${neighbor.routerId}:</span>
                        <span>State: ${neighbor.state}, Area: ${neighbor.area}</span>
                    </div>
                `;
            });
            html += `</div>`;
        }
        
        // Add LSDB for routers
        if (device.ospf && Object.keys(device.ospf.lsdb).length > 0) {
            html += `<div class="device-info"><h3>Link State Database</h3>`;
            Object.entries(device.ospf.lsdb).forEach(([lsaId, lsa]) => {
                html += `
                    <div class="device-property">
                        <span>${lsaId}:</span>
                        <span>Type ${lsa.type || 'Router'}</span>
                    </div>
                    <div class="device-property" style="font-size: 11px; color: #aaa; padding-left: 10px;">
                        <span>Links:</span>
                        <span>${lsa.links ? lsa.links.length : 0}</span>
                    </div>
                `;
            });
            html += `</div>`;
        }
        
        // Add routing table for routers
        if (device.ospf && device.ospf.routingTable.length > 0) {
            html += `<div class="device-info"><h3>Routing Table (${device.ospf.routingTable.length} routes)</h3>`;
            device.ospf.routingTable.forEach(route => {
                const typeColor = route.type === 'inter-area' ? '#ff9966' : '#66ccff';
                html += `
                    <div class="device-property">
                        <span>${route.destination}:</span>
                        <span style="color: ${typeColor}">via ${route.next_hop || 'direct'} (Cost: ${route.cost || 0})</span>
                    </div>
                `;
            });
            html += `</div>`;
        }
        
        container.innerHTML = html;
    }

    updateLinkInfo() {
        if (!this.selectedLink) return;
        
        const link = this.links.get(this.selectedLink);
        if (!link) return;
        
        const container = document.getElementById('device-info-content');
        let html = `
            <div class="device-info">
                <h3><i class="fas fa-link"></i> Link ${link.id}</h3>
                <div class="device-property">
                    <span>Connected Devices:</span>
                    <span>${link.source} ↔ ${link.target}</span>
                </div>
                <div class="device-property">
                    <span>Link Type:</span>
                    <span>${link.type.toUpperCase()}</span>
                </div>
                <div class="device-property">
                    <span>Link Cost:</span>
                    <span>${link.cost}</span>
                </div>
                <div class="device-property">
                    <span>OSPF Area:</span>
                    <span>${link.area}</span>
                </div>
                <div class="device-property">
                    <span>Status:</span>
                    <span>Active</span>
                </div>
            </div>
        `;
        
        // Add connected device info
        const dev1 = this.devices.get(link.source);
        const dev2 = this.devices.get(link.target);
        
        if (dev1 && dev2) {
            html += `
                <div class="device-info">
                    <h3>Connected Devices</h3>
                    <div class="device-property">
                        <span>${link.source}:</span>
                        <span>${dev1.type} - ${dev1.ip}</span>
                    </div>
                    <div class="device-property">
                        <span>${link.target}:</span>
                        <span>${dev2.type} - ${dev2.ip}</span>
                    </div>
                </div>
            `;
        }
        
        // Add interface info
        const intf1 = dev1?.interfaces.find(i => i.linkId === link.id);
        const intf2 = dev2?.interfaces.find(i => i.linkId === link.id);
        
        if (intf1 && intf2) {
            html += `
                <div class="device-info">
                    <h3>Interface Details</h3>
                    <div class="device-property">
                        <span>${link.source} interface:</span>
                        <span>${intf1.id} (${intf1.ip || 'No IP'})</span>
                    </div>
                    <div class="device-property">
                        <span>${link.target} interface:</span>
                        <span>${intf2.id} (${intf2.ip || 'No IP'})</span>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }

    editSelectedLink() {
        if (!this.selectedLink) return;
        
        const link = this.links.get(this.selectedLink);
        if (!link) return;
        
        // Populate edit modal
        document.getElementById('edit-link-id').value = link.id;
        document.getElementById('edit-link-devices').value = `${link.source} ↔ ${link.target}`;
        document.getElementById('edit-link-cost').value = link.cost;
        document.getElementById('edit-link-area').value = link.area;
        document.getElementById('edit-link-type').value = link.type;
        
        this.showModal('edit-link-modal');
    }

    saveLinkChanges() {
        if (!this.selectedLink) return;
        
        const linkId = document.getElementById('edit-link-id').value;
        const newCost = parseInt(document.getElementById('edit-link-cost').value);
        const newArea = parseInt(document.getElementById('edit-link-area').value);
        const newType = document.getElementById('edit-link-type').value;
        
        const link = this.links.get(linkId);
        if (!link) return;
        
        // Store old values for comparison
        const oldCost = link.cost;
        const oldArea = link.area;
        const oldType = link.type;
        
        // Update link object
        link.cost = newCost;
        link.area = newArea;
        link.type = newType;
        link.label = newType === 'ospf' ? `Cost: ${newCost}, Area: ${newArea}` : 'Access';
        
        // Update cytoscape edge
        const edge = this.cy.getElementById(linkId);
        edge.data('label', link.label);
        edge.data('type', newType);
        edge.data('cost', newCost);
        edge.data('area', newArea);
        
        // Update edge style based on type
        if (newType === 'ospf') {
            edge.style('line-color', '#00ffaa');
            edge.style('target-arrow-color', '#00ffaa');
            edge.style('line-style', 'solid');
        } else {
            edge.style('line-color', '#66ccff');
            edge.style('target-arrow-color', '#66ccff');
            edge.style('line-style', 'dashed');
        }
        
        // Update device interfaces
        const dev1 = this.devices.get(link.source);
        const dev2 = this.devices.get(link.target);
        
        if (dev1) {
            const intf1 = dev1.interfaces.find(i => i.linkId === linkId);
            if (intf1) {
                intf1.type = newType;
            }
        }
        
        if (dev2) {
            const intf2 = dev2.interfaces.find(i => i.linkId === linkId);
            if (intf2) {
                intf2.type = newType;
            }
        }
        
        // Update OSPF neighbors if type changed
        if (oldType !== newType) {
            if (oldType === 'ospf' && newType !== 'ospf') {
                // Remove OSPF neighbor entries
                if (dev1 && dev1.ospf) {
                    dev1.ospf.neighbors = dev1.ospf.neighbors.filter(n => n.routerId !== link.target);
                }
                if (dev2 && dev2.ospf) {
                    dev2.ospf.neighbors = dev2.ospf.neighbors.filter(n => n.routerId !== link.source);
                }
            } else if (oldType !== 'ospf' && newType === 'ospf') {
                // Add OSPF neighbor entries
                if (dev1 && dev1.type === 'router' && dev2 && dev2.type === 'router') {
                    if (!dev1.ospf) dev1.ospf = { enabled: true, area: 0, neighbors: [], lsdb: {}, routingTable: [] };
                    if (!dev2.ospf) dev2.ospf = { enabled: true, area: 0, neighbors: [], lsdb: {}, routingTable: [] };
                    
                    const intf1 = dev1.interfaces.find(i => i.linkId === linkId);
                    const intf2 = dev2.interfaces.find(i => i.linkId === linkId);
                    
                    dev1.ospf.neighbors.push({
                        routerId: link.target,
                        state: '2-Way',
                        area: newArea,
                        interface: intf1?.id || 'eth0'
                    });
                    dev2.ospf.neighbors.push({
                        routerId: link.source,
                        state: '2-Way',
                        area: newArea,
                        interface: intf2?.id || 'eth0'
                    });
                }
            }
        } else if (newType === 'ospf' && (oldArea !== newArea || oldCost !== newCost)) {
            // Update OSPF neighbor area and cost
            if (dev1 && dev1.ospf) {
                const neighbor1 = dev1.ospf.neighbors.find(n => n.routerId === link.target);
                if (neighbor1) {
                    neighbor1.area = newArea;
                }
            }
            if (dev2 && dev2.ospf) {
                const neighbor2 = dev2.ospf.neighbors.find(n => n.routerId === link.source);
                if (neighbor2) {
                    neighbor2.area = newArea;
                }
            }
        }
        
        // Hide modal and update
        this.hideModal('edit-link-modal');
        this.updateLinkInfo();
        this.logCLI(`Updated link ${linkId}: Cost=${newCost}, Area=${newArea}, Type=${newType}`);
        
        // Trigger OSPF recalculation if OSPF link
        if (newType === 'ospf') {
            setTimeout(() => this.simulateOSPF(), 300);
        }
    }

    deleteSelectedLink() {
        if (!this.selectedLink) return;
        
        if (confirm('Delete this link? This will disconnect the devices.')) {
            this.deleteLink(this.selectedLink);
        }
    }

    deleteLink(linkId) {
        const link = this.links.get(linkId);
        if (!link) return;
        
        const { source, target, type } = link;
        
        // Remove from devices' interfaces
        const dev1 = this.devices.get(source);
        const dev2 = this.devices.get(target);
        
        if (dev1) {
            dev1.interfaces = dev1.interfaces.filter(i => i.linkId !== linkId);
        }
        
        if (dev2) {
            dev2.interfaces = dev2.interfaces.filter(i => i.linkId !== linkId);
        }
        
        // Remove OSPF neighbor entries if applicable
        if (type === 'ospf') {
            if (dev1 && dev1.ospf) {
                dev1.ospf.neighbors = dev1.ospf.neighbors.filter(n => n.routerId !== target);
            }
            if (dev2 && dev2.ospf) {
                dev2.ospf.neighbors = dev2.ospf.neighbors.filter(n => n.routerId !== source);
            }
        }
        
        // Remove from cytoscape
        this.cy.remove(`#${linkId}`);
        
        // Remove from links map
        this.links.delete(linkId);
        
        // Update
        this.deselectLink();
        this.updateStatus();
        this.logCLI(`Deleted link between ${source} and ${target}`);
        
        // Clear device info display
        const container = document.getElementById('device-info-content');
        container.innerHTML = '<div class="device-info"><h3>No Selection</h3><p>Click on a device or link to view information</p></div>';
        
        // Trigger OSPF recalculation if needed
        if (type === 'ospf') {
            setTimeout(() => this.simulateOSPF(), 300);
        }
    }

    deleteSelectedDevice() {
        if (!this.selectedDevice) return;
        
        if (confirm(`Delete device ${this.selectedDevice} and all connected links?`)) {
            this.deleteDevice(this.selectedDevice);
        }
    }

    deleteDevice(deviceId) {
        const device = this.devices.get(deviceId);
        if (!device) return;
        
        // Delete all connected links first
        device.interfaces.forEach(intf => {
            this.deleteLink(intf.linkId);
        });
        
        // Remove device
        this.devices.delete(deviceId);
        this.cy.remove(`#${deviceId}`);
        
        // Update
        this.deselectDevice();
        this.updateStatus();
        this.logCLI(`Deleted device: ${deviceId}`);
    }

    updateStatus() {
        document.getElementById('status-devices').textContent = this.devices.size;
        document.getElementById('status-links').textContent = this.links.size;
        
        // Count OSPF areas
        const areas = new Set();
        this.links.forEach(link => {
            if (link.type === 'ospf') {
                areas.add(link.area);
            }
        });
        document.getElementById('status-areas').textContent = areas.size;
        
        // Update OSPF step status
        if (this.ospfSteps.length > 0) {
            document.getElementById('status-message').textContent = 
                `OSPF: Step ${this.ospfStepIndex + 1}/${this.ospfSteps.length}`;
        } else {
            document.getElementById('status-message').textContent = 'Ready';
        }
    }

    updateStepPanel() {
        const content = document.getElementById('ospf-step-content');
        content.innerHTML = '';
        
        if (this.ospfSteps.length === 0) {
            content.innerHTML = '<div class="step-item">No OSPF steps available. Run OSPF simulation first.</div>';
            return;
        }
        
        this.ospfSteps.forEach((step, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step-item';
            if (index === this.ospfStepIndex) {
                stepDiv.classList.add('active');
            }
            stepDiv.textContent = `Step ${index + 1}: ${step.description}`;
            stepDiv.addEventListener('click', () => {
                this.ospfStepIndex = index;
                this.updateStepPanel();
                this.executeOSPFStep(step);
            });
            content.appendChild(stepDiv);
        });
    }

    showStepPanel() {
        document.getElementById('ospf-step-panel').style.display = 'block';
    }

    hideStepPanel() {
        document.getElementById('ospf-step-panel').style.display = 'none';
    }

    toggleStepPanel() {
        const panel = document.getElementById('ospf-step-panel');
        if (panel.style.display === 'block') {
            this.hideStepPanel();
        } else {
            this.showStepPanel();
        }
    }

    showOSPFAreas() {
        // Color code OSPF areas
        const areaColors = {
            0: '#00ffaa', // Backbone area
            1: '#ff9966',
            2: '#66ccff',
            3: '#cc99ff',
            4: '#ffcc66',
            5: '#ff6666'
        };
        
        this.cy.edges().forEach(edge => {
            if (edge.data('type') === 'ospf') {
                const area = edge.data('area') || 0;
                const color = areaColors[area] || '#ffffff';
                edge.style('line-color', color);
                edge.style('target-arrow-color', color);
            }
        });
        
        this.logCLI('OSPF areas color-coded on the network diagram');
    }

    showRoutingTables() {
        // Highlight routing paths for selected device
        if (!this.selectedDevice) {
            this.logCLI('Select a router to show its routing paths', 'error');
            return;
        }
        
        const device = this.devices.get(this.selectedDevice);
        if (!device.ospf || device.ospf.routingTable.length === 0) {
            this.logCLI('No routing table available for this device', 'error');
            return;
        }
        
        // Clear previous highlights
        this.cy.edges().removeClass('ospf-route');
        
        // Highlight routes
        device.ospf.routingTable.forEach(route => {
            if (route.path && route.path.length > 1) {
                for (let i = 0; i < route.path.length - 1; i++) {
                    const source = route.path[i];
                    const target = route.path[i + 1];
                    
                    const edge = this.cy.edges().filter(edge => 
                        (edge.data('source') === source && edge.data('target') === target) ||
                        (edge.data('source') === target && edge.data('target') === source)
                    );
                    
                    if (edge.length > 0) {
                        edge.addClass('ospf-route');
                    }
                }
            }
        });
        
        setTimeout(() => {
            this.cy.edges().removeClass('ospf-route');
        }, 5000);
        
        this.logCLI(`Showing routing paths for ${device.id}. Highlights will disappear in 5 seconds.`);
    }

    generateIP(type) {
        // Generate unique IP based on device type
        const baseIPs = {
            router: '10.0.0.',
            switch: '192.168.1.',
            pc: '192.168.10.',
            laptop: '192.168.20.',
            phone: '192.168.30.',
            server: '192.168.100.'
        };
        
        const base = baseIPs[type] || '192.168.0.';
        const octet = Math.floor(Math.random() * 254) + 1;
        return base + octet;
    }

    generateInterfaceIP() {
        const octet2 = Math.floor(Math.random() * 255);
        const octet3 = Math.floor(Math.random() * 255);
        return `172.${octet2}.${octet3}.1`;
    }

    generateMAC() {
        const hex = '0123456789ABCDEF';
        let mac = '';
        for (let i = 0; i < 6; i++) {
            mac += hex[Math.floor(Math.random() * 16)];
            mac += hex[Math.floor(Math.random() * 16)];
            if (i < 5) mac += ':';
        }
        return mac;
    }

    getDeviceIcon(type) {
        const icons = {
            router: 'route',
            switch: 'sitemap',
            pc: 'desktop',
            laptop: 'laptop',
            phone: 'mobile-alt',
            server: 'server'
        };
        return icons[type] || 'question-circle';
    }

    showModal(modalId) {
        document.getElementById(modalId).style.display = 'flex';
    }

    hideModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    // ========== CLI METHODS ==========

    logCLI(message, type = 'info') {
        const output = document.getElementById('cli-output');
        const line = document.createElement('div');
        line.className = `cli-line ${type}`;
        line.textContent = message;
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    }

    processCLICommand() {
        const input = document.getElementById('cli-input');
        const command = input.value.trim();
        input.value = '';
        
        if (!command) return;
        
        // Log command
        this.logCLI(`Router# ${command}`, 'cmd');
        
        // Process command
        const parts = command.split(' ');
        const cmd = parts[0].toLowerCase();
        
        switch (cmd) {
            case 'enable':
                this.logCLI('Privileged mode enabled');
                document.getElementById('cli-prompt').textContent = 'Router#';
                break;
                
            case 'configure':
            case 'conf':
            case 'conf t':
                this.logCLI('Enter configuration mode');
                document.getElementById('cli-prompt').textContent = 'Router(config)#';
                break;
                
            case 'exit':
                this.logCLI('Exited to privileged mode');
                document.getElementById('cli-prompt').textContent = 'Router#';
                break;
                
            case 'show':
                this.handleShowCommand(parts.slice(1));
                break;
                
            case 'ping':
                this.handlePingCommand(parts.slice(1));
                break;
                
            case 'ospf':
                this.handleOSPFCommand(parts.slice(1));
                break;
                
            case 'step':
                this.stepOSPF();
                break;
                
            case 'clear':
                document.getElementById('cli-output').innerHTML = '';
                break;
                
            case 'help':
                this.showCLIHelp();
                break;
                
            default:
                this.logCLI(`Unknown command: ${cmd}. Type 'help' for available commands.`, 'error');
        }
    }

    handleShowCommand(args) {
        if (args.length === 0) {
            this.logCLI('Usage: show [ip route | ip ospf neighbor | ip ospf database | ip ospf interface | topology | steps]', 'error');
            return;
        }
        
        const subcmd = args.join(' ').toLowerCase();
        
        if (subcmd === 'topology') {
            this.logCLI(`Topology Summary:`);
            this.logCLI(`  Devices: ${this.devices.size}`);
            this.logCLI(`  Links: ${this.links.size}`);
            
            // Count routers by area
            const areaRouters = {};
            this.devices.forEach(device => {
                if (device.type === 'router' && device.ospf) {
                    const area = device.ospf.area;
                    if (!areaRouters[area]) areaRouters[area] = [];
                    areaRouters[area].push(device.id);
                }
            });
            
            Object.keys(areaRouters).forEach(area => {
                this.logCLI(`  Area ${area}: ${areaRouters[area].length} routers`);
            });
            
            return;
        }
        
        if (subcmd === 'steps') {
            this.logCLI(`OSPF Steps (${this.ospfStepIndex}/${this.ospfSteps.length}):`);
            if (this.ospfSteps.length === 0) {
                this.logCLI('  No OSPF steps available');
            } else {
                this.ospfSteps.forEach((step, index) => {
                    const prefix = index === this.ospfStepIndex ? '▶ ' : '  ';
                    this.logCLI(`${prefix}Step ${index + 1}: ${step.description}`);
                });
            }
            return;
        }
        
        if (!this.selectedDevice) {
            this.logCLI('No device selected. Click on a router first.', 'error');
            return;
        }
        
        const device = this.devices.get(this.selectedDevice);
        if (!device.ospf) {
            this.logCLI('This device does not run OSPF.', 'error');
            return;
        }
        
        switch (subcmd) {
            case 'ip route':
                this.logCLI(`Routing Table for ${device.id}:`);
                if (device.ospf.routingTable.length === 0) {
                    this.logCLI('  No routes in routing table');
                } else {
                    device.ospf.routingTable.forEach(route => {
                        const type = route.type === 'inter-area' ? 'O IA' : 'O';
                        this.logCLI(`  ${type} ${route.destination} [${route.cost || 0}] via ${route.next_hop || 'direct'}`);
                    });
                }
                break;
                
            case 'ip ospf neighbor':
                this.logCLI(`OSPF Neighbors for ${device.id}:`);
                if (device.ospf.neighbors.length === 0) {
                    this.logCLI('  No OSPF neighbors');
                } else {
                    device.ospf.neighbors.forEach(neighbor => {
                        this.logCLI(`  ${neighbor.routerId} - State: ${neighbor.state}, Area: ${neighbor.area}`);
                    });
                }
                break;
                
            case 'ip ospf database':
                this.logCLI(`LSDB for ${device.id}:`);
                const lsdb = device.ospf.lsdb;
                if (Object.keys(lsdb).length === 0) {
                    this.logCLI('  LSDB is empty');
                } else {
                    Object.entries(lsdb).forEach(([lsaId, lsa]) => {
                        this.logCLI(`  ${lsaId}: Type ${lsa.type || 'Router'}, Links: ${lsa.links ? lsa.links.length : 0}`);
                    });
                }
                break;
                
            case 'ip ospf interface':
                this.logCLI(`OSPF Interfaces for ${device.id}:`);
                device.interfaces.forEach(intf => {
                    if (intf.type === 'ospf') {
                        const link = this.links.get(intf.linkId);
                        this.logCLI(`  ${intf.id}: ${intf.ip}, Area ${link.area}, Cost: ${link.cost}, State: ${intf.state}`);
                    }
                });
                break;
                
            default:
                this.logCLI(`Unknown show command: ${subcmd}`, 'error');
        }
    }

    handleOSPFCommand(args) {
        if (args.length === 0) {
            this.logCLI('Usage: ospf [simulate | step | reset | steps]', 'error');
            return;
        }
        
        const subcmd = args[0].toLowerCase();
        
        switch (subcmd) {
            case 'simulate':
                this.simulateOSPF();
                break;
                
            case 'step':
                this.stepOSPF();
                break;
                
            case 'reset':
                this.ospfSteps = [];
                this.ospfStepIndex = 0;
                this.updateStepPanel();
                this.logCLI('OSPF simulation reset');
                break;
                
            case 'steps':
                this.showStepPanel();
                break;
                
            default:
                this.logCLI(`Unknown OSPF command: ${subcmd}`, 'error');
        }
    }

    handlePingCommand(args) {
        if (args.length === 0) {
            this.logCLI('Usage: ping <destination>', 'error');
            return;
        }
        
        const destination = args[0];
        
        if (!this.selectedDevice) {
            this.logCLI('No source device selected', 'error');
            return;
        }
        
        const path = this.findShortestPath(this.selectedDevice, destination);
        
        if (path.length > 0) {
            this.logCLI(`Pinging ${destination} from ${this.selectedDevice}...`);
            this.logCLI(`Path: ${path.join(' -> ')}`);
            
            // Simulate ping with timeout
            setTimeout(() => {
                const rand = Math.random();
                if (rand > 0.3) {
                    this.logCLI(`Reply from ${destination}: bytes=32 time=${Math.floor(Math.random() * 100)}ms TTL=64`);
                } else {
                    this.logCLI(`Request timed out.`, 'error');
                }
            }, 500);
        } else {
            this.logCLI(`Destination ${destination} unreachable from ${this.selectedDevice}`, 'error');
        }
    }

    showCLIHelp() {
        this.logCLI('Available commands:');
        this.logCLI('  enable                    - Enter privileged mode');
        this.logCLI('  configure terminal       - Enter configuration mode');
        this.logCLI('  exit                     - Exit to previous mode');
        this.logCLI('  show ip route            - Show routing table');
        this.logCLI('  show ip ospf neighbor    - Show OSPF neighbors');
        this.logCLI('  show ip ospf database    - Show OSPF link-state database');
        this.logCLI('  show ip ospf interface   - Show OSPF interfaces');
        this.logCLI('  show topology            - Show topology summary');
        this.logCLI('  show steps               - Show OSPF steps');
        this.logCLI('  ping <destination>       - Ping a destination');
        this.logCLI('  ospf simulate            - Run OSPF simulation');
        this.logCLI('  ospf step                - Step through OSPF simulation');
        this.logCLI('  ospf reset               - Reset OSPF simulation');
        this.logCLI('  ospf steps               - Show OSPF step panel');
        this.logCLI('  step                     - Advance OSPF step');
        this.logCLI('  clear                    - Clear CLI screen');
        this.logCLI('  help                     - Show this help');
    }

           

    newProject() {
        if (confirm('Create new project? All unsaved changes will be lost.')) {
            this.clearAll();
            this.logCLI('New project created');
        }
    }

    clearAll() {
        if (confirm('Clear all devices and links?')) {
            this.devices.clear();
            this.links.clear();
            this.cy.elements().remove();
            this.deselectDevice();
            this.deselectLink();
            this.ospfSteps = [];
            this.ospfStepIndex = 0;
            this.updateStepPanel();
            this.hideStepPanel();
            this.updateStatus();
            this.logCLI('All devices and links cleared');
        }
    }

    saveProject() {
        const topology = {
            devices: Array.from(this.devices.values()),
            links: Array.from(this.links.values()),
            timestamp: new Date().toISOString()
        };
        
        const dataStr = JSON.stringify(topology, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = 'network-topology.json';
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        this.logCLI('Project saved as network-topology.json');
    }

    loadProject() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            const reader = new FileReader();
            
            reader.onload = (event) => {
                try {
                    const topology = JSON.parse(event.target.result);
                    this.loadTopology(topology);
                    this.logCLI('Project loaded successfully');
                } catch (error) {
                    this.logCLI(`Error loading project: ${error.message}`, 'error');
                }
            };
            
            reader.readAsText(file);
        };
        
        input.click();
    }

    loadTopology(topology) {
        // Clear existing topology
        this.clearAll();
        
        // Load devices
        topology.devices.forEach(deviceData => {
            this.devices.set(deviceData.id, deviceData);
            
            // Add to cytoscape
            this.cy.add({
                group: 'nodes',
                data: { 
                    id: deviceData.id,
                    label: deviceData.label,
                    type: deviceData.type
                },
                position: deviceData.position,
                classes: deviceData.type
            });
        });
        
        // Load links
        topology.links.forEach(linkData => {
            this.links.set(linkData.id, linkData);
            
            // Add to cytoscape
            this.cy.add({
                group: 'edges',
                data: {
                    id: linkData.id,
                    source: linkData.source,
                    target: linkData.target,
                    label: linkData.label,
                    type: linkData.type,
                    cost: linkData.cost,
                    area: linkData.area
                }
            });
        });
        
        // Update counters
        this.nextDeviceId = Math.max(...Array.from(this.devices.keys()).map(id => {
            const match = id.match(/(\D+)(\d+)/);
            return match ? parseInt(match[2]) : 0;
        })) + 1;
        
        this.nextLinkId = Math.max(...Array.from(this.links.keys()).map(id => {
            const match = id.match(/link(\d+)/);
            return match ? parseInt(match[1]) : 0;
        })) + 1;
        
        // Update UI
        this.updateStatus();
        this.cy.fit();
    }

    refreshDeviceInfo() {
        if (this.selectedLink) {
            this.updateLinkInfo();
        } else {
            this.updateDeviceInfo();
        }
    }
}

// Initialize simulator when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.simulator = new NetworkSimulator();
});