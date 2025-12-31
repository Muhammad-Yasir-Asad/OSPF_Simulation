# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import networkx as nx
from datetime import datetime
import math
import time

app = FastAPI(title="Network Simulator Backend", description="OSPF Simulation Backend API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class Interface(BaseModel):
    id: str
    connectedTo: str
    linkId: str
    type: str
    ip: Optional[str] = ""
    state: Optional[str] = "up"

class OSPFConfig(BaseModel):
    enabled: bool = True
    area: int = 0
    neighbors: List[Dict] = []
    lsdb: Dict[str, Any] = {}
    routingTable: List[Dict] = []

class Device(BaseModel):
    id: str
    type: str
    label: str
    position: Dict[str, float]
    ip: str
    interfaces: List[Interface] = []
    ospf: Optional[OSPFConfig] = None
    mac: str

class Link(BaseModel):
    id: str
    source: str
    target: str
    type: str
    cost: int = 10
    area: int = 0
    label: str = ""

class Topology(BaseModel):
    devices: List[Device]
    links: List[Link]
    timestamp: str

class PingRequest(BaseModel):
    source: str
    destination: str
    topology: Dict

class OSPSimulation(BaseModel):
    topology: Topology
    step_by_step: Optional[bool] = False

class LSAPacket(BaseModel):
    """Link State Advertisement packet model"""
    router_id: str
    sequence: int
    age: int
    links: List[Dict]
    area: int

class OSPFSimulator:
    """Enhanced OSPF simulation engine with step-by-step capability"""
    
    def __init__(self):
        self.graph = nx.Graph()
        self.lsdb = {}  # Global Link State Database
        self.areas = {}
        self.steps = []
        
    def build_topology(self, topology: Topology):
        """Build network graph from topology"""
        self.graph.clear()
        
        # Add nodes
        for device in topology.devices:
            self.graph.add_node(device.id, 
                               type=device.type,
                               ip=device.ip,
                               area=device.ospf.area if device.ospf else 0,
                               device_data=device.dict())
        
        # Add edges (links)
        for link in topology.links:
            if link.type == 'ospf':
                self.graph.add_edge(link.source, link.target,
                                   weight=link.cost,
                                   area=link.area,
                                   type='ospf',
                                   link_data=link.dict())
            else:
                self.graph.add_edge(link.source, link.target,
                                   weight=1,
                                   type='access',
                                   link_data=link.dict())
        
        return self.graph
    
    def simulate_ospf(self, topology: Topology, step_by_step: bool = False):
        """Run OSPF simulation with optional step-by-step mode"""
        self.steps = []
        self.build_topology(topology)
        
        # Step 1: Neighbor Discovery (Hello packets)
        self.step_neighbor_discovery(topology)
        
        # Step 2: LSA Generation
        self.step_lsa_generation(topology)
        
        # Step 3: LSA Flooding
        self.step_lsa_flooding(topology)
        
        # Step 4: Dijkstra Calculation
        self.step_dijkstra_calculation(topology)
        
        # Step 5: Routing Table Update
        routing_tables = self.step_routing_table_update(topology)
        
        # Identify areas
        areas = self.identify_areas()
        
        if step_by_step:
            return {
                "success": True,
                "steps": self.steps,
                "routing_tables": routing_tables,
                "areas": areas,
                "graph_nodes": len(self.graph.nodes()),
                "graph_edges": len(self.graph.edges())
            }
        else:
            return {
                "success": True,
                "routing_tables": routing_tables,
                "areas": areas,
                "graph_nodes": len(self.graph.nodes()),
                "graph_edges": len(self.graph.edges())
            }
    
    def step_neighbor_discovery(self, topology: Topology):
        """Step 1: Neighbor discovery via Hello packets"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        for router in routers:
            # Find OSPF neighbors
            ospf_neighbors = []
            for interface in router.interfaces:
                if interface.type == 'ospf':
                    # Find connected device
                    for link in topology.links:
                        if link.id == interface.linkId:
                            neighbor_id = link.target if link.source == router.id else link.source
                            ospf_neighbors.append(neighbor_id)
            
            # Add step
            self.steps.append({
                "type": "hello",
                "description": f"Router {router.id} sends Hello packets",
                "router_id": router.id,
                "neighbors": ospf_neighbors,
                "neighbor_state": "2-Way"
            })
            
            # Update neighbor states
            neighbor_updates = []
            for neighbor_id in ospf_neighbors:
                neighbor_updates.append({
                    "router_id": router.id,
                    "neighbor_id": neighbor_id,
                    "new_state": "2-Way"
                })
            
            if neighbor_updates:
                self.steps.append({
                    "type": "neighbor_update",
                    "description": f"Update neighbor states for {router.id}",
                    "neighbor_updates": neighbor_updates
                })
    
    def step_lsa_generation(self, topology: Topology):
        """Step 2: Generate LSAs for each router"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        for router in routers:
            # Generate LSA
            lsa = {
                "id": f"LSA-{router.id}",
                "router_id": router.id,
                "sequence": 1,
                "age": 0,
                "area": router.ospf.area,
                "type": "Router",
                "links": []
            }
            
            # Add links from interfaces
            for interface in router.interfaces:
                if interface.type == 'ospf':
                    link = next((l for l in topology.links if l.id == interface.linkId), None)
                    if link:
                        neighbor_id = link.target if link.source == router.id else link.source
                        lsa["links"].append({
                            "neighbor": neighbor_id,
                            "cost": link.cost,
                            "interface": interface.id
                        })
            
            # Store in global LSDB
            self.lsdb[router.id] = lsa
            
            # Add step
            self.steps.append({
                "type": "lsa_generation",
                "description": f"Router {router.id} generates LSA",
                "router_id": router.id,
                "lsa_id": lsa["id"],
                "lsdb": {router.id: lsa}
            })
    
    def step_lsa_flooding(self, topology: Topology):
        """Step 3: Flood LSAs through the network"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        # Simple flooding simulation
        for router in routers:
            for neighbor in self.graph.neighbors(router.id):
                if self.graph[router.id][neighbor].get('type') == 'ospf':
                    # Simulate LSA packet transmission
                    self.steps.append({
                        "type": "lsa_flooding",
                        "description": f"Flooding LSA from {router.id} to {neighbor}",
                        "source": router.id,
                        "target": neighbor,
                        "lsa_id": f"LSA-{router.id}",
                        "lsdb_update": self.lsdb
                    })
    
    def step_dijkstra_calculation(self, topology: Topology):
        """Step 4: Run Dijkstra's algorithm on each router"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        for router in routers:
            # Create subgraph for OSPF area
            ospf_edges = [(u, v) for u, v, d in self.graph.edges(data=True) 
                         if d.get('type') == 'ospf']
            
            if not ospf_edges:
                continue
                
            # Create area-specific graph
            area_graph = nx.Graph()
            
            # Add OSPF routers and links
            for device in routers:
                area_graph.add_node(device.id)
            
            for u, v, data in self.graph.edges(data=True):
                if data.get('type') == 'ospf':
                    area_graph.add_edge(u, v, weight=data['weight'])
            
            # Run Dijkstra's algorithm
            try:
                # Calculate shortest paths from this router
                paths = nx.single_source_dijkstra_path(area_graph, router.id)
                
                # Find edges in shortest path tree
                shortest_path_edges = []
                for target, path in paths.items():
                    if target != router.id and len(path) > 1:
                        for i in range(len(path) - 1):
                            edge = (path[i], path[i + 1])
                            if edge not in shortest_path_edges and (edge[1], edge[0]) not in shortest_path_edges:
                                shortest_path_edges.append(edge)
                
                # Add step
                self.steps.append({
                    "type": "dijkstra",
                    "description": f"Router {router.id} runs Dijkstra's algorithm",
                    "router_id": router.id,
                    "shortest_path_edges": shortest_path_edges
                })
                
            except nx.NetworkXNoPath:
                pass
    
    def step_routing_table_update(self, topology: Topology):
        """Step 5: Build routing tables for each router"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        routing_tables = []
        
        for router in routers:
            # Create subgraph for OSPF area
            ospf_edges = [(u, v) for u, v, d in self.graph.edges(data=True) 
                         if d.get('type') == 'ospf']
            
            if not ospf_edges:
                routing_tables.append({
                    "router": router.id,
                    "area": router.ospf.area,
                    "routes": [],
                    "lsdb": self.lsdb,
                    "neighbors": router.ospf.neighbors
                })
                continue
                
            # Create area-specific graph
            area_graph = nx.Graph()
            
            # Add OSPF routers and links
            for device in routers:
                area_graph.add_node(device.id)
            
            for u, v, data in self.graph.edges(data=True):
                if data.get('type') == 'ospf':
                    area_graph.add_edge(u, v, weight=data['weight'])
            
            # Build routing table
            routes = []
            try:
                # Calculate shortest paths from this router
                paths = nx.single_source_dijkstra_path(area_graph, router.id)
                lengths = nx.single_source_dijkstra_path_length(area_graph, router.id)
                
                for target, path in paths.items():
                    if target != router.id:
                        # Find next hop
                        next_hop = path[1] if len(path) > 1 else None
                        
                        routes.append({
                            "destination": target,
                            "next_hop": next_hop,
                            "cost": lengths[target],
                            "path": path
                        })
                
            except nx.NetworkXNoPath:
                routes = []
            
            # Add step
            self.steps.append({
                "type": "routing_update",
                "description": f"Router {router.id} updates routing table",
                "router_id": router.id,
                "routes": routes
            })
            
            routing_tables.append({
                "router": router.id,
                "area": router.ospf.area,
                "routes": routes,
                "lsdb": self.lsdb,
                "neighbors": router.ospf.neighbors
            })
        
        return routing_tables
    
    def identify_areas(self):
        """Identify OSPF areas in the topology"""
        areas = {}
        
        for node, data in self.graph.nodes(data=True):
            if data.get('type') == 'router':
                area = data.get('area', 0)
                if area not in areas:
                    areas[area] = []
                areas[area].append(node)
        
        return areas

class PingSimulator:
    """Ping path calculation simulator"""
    
    def __init__(self):
        self.path_cache = {}
    
    def calculate_ping_path(self, source: str, destination: str, topology: Dict):
        """Calculate hop-by-hop ping path"""
        try:
            # Convert topology to graph
            G = nx.Graph()
            
            # Add devices
            devices = topology.get('devices', [])
            for device in devices:
                G.add_node(device['id'], type=device['type'])
            
            # Add links
            links = topology.get('links', [])
            for link in links:
                G.add_edge(link['source'], link['target'], 
                          type=link['type'],
                          cost=link.get('cost', 1))
            
            # Find shortest path using Dijkstra
            try:
                path = nx.shortest_path(G, source, destination, weight='cost')
                
                # Calculate total hops
                hops = len(path) - 1
                
                return {
                    "success": True,
                    "path": path,
                    "hops": hops,
                    "source": source,
                    "destination": destination
                }
                
            except nx.NetworkXNoPath:
                return {
                    "success": False,
                    "message": f"No path found between {source} and {destination}",
                    "path": [],
                    "hops": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error calculating path: {str(e)}",
                "path": [],
                "hops": 0
            }

# Initialize simulators
ospf_simulator = OSPFSimulator()
ping_simulator = PingSimulator()

@app.get("/")
async def root():
    return {
        "message": "Network Simulator Backend API",
        "endpoints": {
            "GET /": "This information",
            "POST /ospf": "Run OSPF simulation",
            "POST /ping": "Calculate ping path",
            "GET /health": "Health check"
        },
        "version": "2.0.0",
        "features": ["OSPF simulation", "Step-by-step animation", "Ping routing"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "simulators": {
            "ospf": "ready",
            "ping": "ready"
        }
    }

@app.post("/ospf")
async def run_ospf_simulation(request: OSPSimulation):
    """
    Run OSPF simulation on the provided topology.
    
    This endpoint:
    1. Builds the network graph from topology
    2. Generates LSAs for each router
    3. Floods LSAs through the network
    4. Calculates routing tables using Dijkstra's algorithm
    5. Returns routing tables and area information
    """
    try:
        result = ospf_simulator.simulate_ospf(
            request.topology, 
            request.step_by_step
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSPF simulation failed: {str(e)}")

@app.post("/ping")
async def calculate_ping_path(request: PingRequest):
    """
    Calculate ping path between source and destination.
    
    This endpoint:
    1. Builds graph from topology
    2. Finds shortest path using graph algorithms
    3. Returns hop-by-hop path for animation
    """
    try:
        result = ping_simulator.calculate_ping_path(
            request.source,
            request.destination,
            request.topology
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping calculation failed: {str(e)}")

@app.get("/ospf/dijkstra-example")
async def dijkstra_example():
    """
    Example of Dijkstra's algorithm for educational purposes
    """
    # Create a simple example graph
    G = nx.Graph()
    G.add_edge('A', 'B', weight=4)
    G.add_edge('A', 'C', weight=2)
    G.add_edge('B', 'C', weight=1)
    G.add_edge('B', 'D', weight=5)
    G.add_edge('C', 'D', weight=8)
    G.add_edge('C', 'E', weight=10)
    G.add_edge('D', 'E', weight=2)
    
    # Run Dijkstra from node A
    path_lengths = nx.single_source_dijkstra_path_length(G, 'A')
    paths = nx.single_source_dijkstra_path(G, 'A')
    
    return {
        "graph": {
            "nodes": list(G.nodes()),
            "edges": [{"from": u, "to": v, "weight": d['weight']} 
                     for u, v, d in G.edges(data=True)]
        },
        "dijkstra_from_A": {
            "shortest_paths": paths,
            "shortest_distances": path_lengths
        },
        "explanation": "Dijkstra's algorithm finds the shortest path from a source node to all other nodes in a weighted graph."
    }

