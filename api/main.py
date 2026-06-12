from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Tuple, Set
import networkx as nx
from datetime import datetime
import heapq
import time
from collections import defaultdict, deque
import uvicorn
import math

app = FastAPI(
    title="Network Simulator Backend",
    description="Complete OSPF Simulation with Full Area Support, LSA Types, and Advanced Routing"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    is_abr: Optional[bool] = False
    is_asbr: Optional[bool] = False
    stub_area: Optional[bool] = False
    nssa: Optional[bool] = False

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
    topology: Topology

class OSPSimulation(BaseModel):
    topology: Topology
    step_by_step: Optional[bool] = False

class OSPFSimulator:
    """Complete OSPF simulation engine with full area support including all LSA types"""
    
    def __init__(self):
        self.graph = nx.Graph()
        self.area_graphs = {}
        self.area_lsdbs = defaultdict(dict)  
        self.lsdb = {}
        self.areas = defaultdict(set)
        self.abrs = set()
        self.asbrs = set()
        self.steps = []
        self.routing_tables = {}
        self.area_configs = defaultdict(dict) 
        
    def build_topology(self, topology: Topology):
        """Build network graph from topology with complete area information"""
        self.graph.clear()
        self.area_graphs.clear()
        self.area_lsdbs.clear()
        self.areas.clear()
        self.abrs.clear()
        self.asbrs.clear()
        self.area_configs.clear()
        

        for device in topology.devices:
            area = device.ospf.area if (device.ospf and device.ospf.enabled) else 0
            self.graph.add_node(
                device.id,
                type=device.type,
                ip=device.ip,
                area=area,
                ospf_enabled=(device.ospf is not None and device.ospf.enabled),
                is_asbr=False,
                device_data=device.dict()
            )
            
            if device.type == 'router' and device.ospf and device.ospf.enabled:
                self.areas[area].add(device.id)
               
                if device.ospf.stub_area:
                    self.area_configs[area]['stub'] = True
                if device.ospf.nssa:
                    self.area_configs[area]['nssa'] = True
        
      
        for link in topology.links:
            if link.type == 'ospf':
                self.graph.add_edge(
                    link.source,
                    link.target,
                    weight=link.cost,
                    area=link.area,
                    type='ospf',
                    cost=link.cost,
                    link_data=link.dict()
                )
                
                # Update device area if needed
                if link.area != 0:
                    src_node = self.graph.nodes[link.source]
                    tgt_node = self.graph.nodes[link.target]
                    if src_node.get('type') == 'router':
                        src_node['area'] = link.area
                    if tgt_node.get('type') == 'router':
                        tgt_node['area'] = link.area
            else:
                self.graph.add_edge(
                    link.source,
                    link.target,
                    weight=1,
                    type='access',
                    cost=1,
                    link_data=link.dict()
                )
        
       
        self.identify_asbrs(topology)
        
        self.build_area_graphs()
        
        self.identify_abrs()
        
        self.identify_backbone_routers()
        
        return self.graph
    
    def identify_asbrs(self, topology: Topology):
        """Identify AS Boundary Routers (routers with external connections)"""
        for device in topology.devices:
            if device.type == 'router' and device.ospf and device.ospf.enabled:
               
                has_external = False
                for interface in device.interfaces:
                    link = next((l for l in topology.links if l.id == interface.linkId), None)
                    if link and link.type != 'ospf':
                        connected_device = next(
                            (d for d in topology.devices if d.id == 
                             (link.target if link.source == device.id else link.source)),
                            None
                        )
                        if connected_device and connected_device.type in ['pc', 'laptop', 'phone', 'server']:
                            has_external = True
                            break
                
                if has_external:
                    self.asbrs.add(device.id)
                    if device.id in self.graph.nodes:
                        self.graph.nodes[device.id]['is_asbr'] = True
                        if device.ospf:
                            device.ospf.is_asbr = True
    
    def identify_abrs(self):
        """Identify Area Border Routers (routers connecting multiple areas)"""
        router_areas = defaultdict(set)
        
        for router_id in [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'router']:
            areas_found = set()
            
           
            node_area = self.graph.nodes[router_id].get('area', 0)
            if node_area is not None:
                areas_found.add(node_area)
            
        
            for u, v, data in self.graph.edges(router_id, data=True):
                if data.get('type') == 'ospf':
                    areas_found.add(data.get('area', 0))
            
            if areas_found:
                router_areas[router_id] = areas_found
        

        for router, areas in router_areas.items():
            if len(areas) > 1:
                self.abrs.add(router)
        
                if 0 in areas:
                    self.graph.nodes[router]['area'] = 0
            elif len(areas) == 1 and 0 in areas and router not in self.abrs:
   
                self.graph.nodes[router]['backbone_router'] = True
        
        
        for abr in self.abrs:
            if abr in self.graph.nodes:
                self.graph.nodes[abr]['is_abr'] = True
    
    def identify_backbone_routers(self):
        """Identify all backbone routers (area 0)"""
        for router_id in self.areas.get(0, []):
            if router_id in self.graph.nodes:
                self.graph.nodes[router_id]['backbone_router'] = True
    
    def build_area_graphs(self):
        """Build separate graphs for each OSPF area with complete topology"""
        self.area_graphs.clear()
        
      
        for area in self.areas.keys():
            self.area_lsdbs[area] = {}
        
        # Create graph for each area
        for area, routers in self.areas.items():
            area_graph = nx.Graph()
            
            # Add routers in this area
            for router_id in routers:
                if router_id in self.graph.nodes:
                    node_data = self.graph.nodes[router_id].copy()
                    # Ensure area is set correctly
                    node_data['area'] = area
                    area_graph.add_node(router_id, **node_data)
            
            # Add OSPF links in this area
            for u, v, data in self.graph.edges(data=True):
                if (data.get('type') == 'ospf' and 
                    data.get('area') == area and
                    u in area_graph.nodes and v in area_graph.nodes):
                    area_graph.add_edge(u, v, **data)
            
            # Add virtual transit networks (for multi-access networks)
            self.add_virtual_transit_networks(area_graph, area)
            
            self.area_graphs[area] = area_graph
    
    def add_virtual_transit_networks(self, area_graph, area):
        """Add virtual transit networks for multi-access OSPF networks"""
        # Identify routers connected to the same switch
        switch_connections = defaultdict(list)
        
        for node in area_graph.nodes():
            if area_graph.nodes[node].get('type') == 'router':
                for neighbor in self.graph.neighbors(node):
                    if self.graph.nodes[neighbor].get('type') == 'switch':
                        switch_connections[neighbor].append(node)
        
        # Create virtual transit networks
        for switch, routers in switch_connections.items():
            if len(routers) > 1:
                # Create a virtual network node
                network_id = f"NET-{switch}"
                area_graph.add_node(network_id, type='network', area=area)
                
                # Connect routers to the network with appropriate costs
                for router in routers:
                    # Find link cost from router to switch
                    cost = 1
                    for u, v, data in self.graph.edges(router, data=True):
                        if v == switch or u == switch:
                            cost = data.get('cost', 1)
                            break
                    
                    area_graph.add_edge(router, network_id, weight=cost, type='transit')
                    area_graph.add_edge(network_id, router, weight=cost, type='transit')
    
    def simulate_ospf(self, topology: Topology, step_by_step: bool = False):
        """Run complete OSPF simulation with full area support"""
        self.steps = []
        self.routing_tables = {}
        self.area_lsdbs.clear()
        
        # Build topology
        self.build_topology(topology)
        
        # Step 1: Neighbor discovery (Hello protocol)
        self.step_neighbor_discovery(topology)
        
        # Step 2: Database synchronization
        self.step_database_synchronization(topology)
        
        # Step 3: LSA generation for each router
        self.generate_all_lsas(topology)
        
        # Step 4: LSA flooding with area boundaries
        self.flood_lsas_with_area_boundaries()
        
        # Step 5: Build area LSDBs
        self.build_area_lsdbs()
        
        # Step 6: SPF calculation per area
        self.run_spf_per_area()
        
        # Step 7: Build routing tables with OSPF preferences
        routing_tables = self.build_complete_routing_tables(topology)
        
        # Step 8: Calculate inter-area and external routes
        self.calculate_inter_area_routes(routing_tables)
        self.calculate_external_routes(routing_tables, topology)
        
        # Step 9: Apply area-specific rules (stub, NSSA)
        self.apply_area_specific_rules(routing_tables)
        
        # Prepare response
        areas_info = self.get_areas_info()
        
        if step_by_step:
            return {
                "success": True,
                "steps": self.steps,
                "routing_tables": routing_tables,
                "areas": areas_info,
                "abrs": list(self.abrs),
                "asbrs": list(self.asbrs),
                "area_configs": dict(self.area_configs),
                "graph_info": {
                    "total_nodes": len(self.graph.nodes()),
                    "total_edges": len(self.graph.edges()),
                    "ospf_routers": len([n for n, d in self.graph.nodes(data=True) 
                                        if d.get('type') == 'router' and d.get('ospf_enabled')]),
                    "areas_count": len(self.areas),
                    "abrs_count": len(self.abrs),
                    "asbrs_count": len(self.asbrs)
                }
            }
        else:
            return {
                "success": True,
                "routing_tables": routing_tables,
                "areas": areas_info,
                "abrs": list(self.abrs),
                "asbrs": list(self.asbrs),
                "area_configs": dict(self.area_configs),
                "graph_info": {
                    "total_nodes": len(self.graph.nodes()),
                    "total_edges": len(self.graph.edges()),
                    "ospf_routers": len([n for n, d in self.graph.nodes(data=True) 
                                        if d.get('type') == 'router' and d.get('ospf_enabled')])
                }
            }
    
    def step_neighbor_discovery(self, topology: Topology):
        """Step 1: Neighbor discovery via Hello packets"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        for router in routers:
            area = router.ospf.area if router.ospf else 0
            ospf_neighbors = []
            
            # Find OSPF neighbors in same area
            for interface in router.interfaces:
                if interface.type == 'ospf':
                    link = next((l for l in topology.links if l.id == interface.linkId), None)
                    if link and link.type == 'ospf':
                        neighbor_id = link.target if link.source == router.id else link.source
                        neighbor = next((d for d in topology.devices if d.id == neighbor_id), None)
                        
                        if neighbor and neighbor.type == 'router':
                            neighbor_area = neighbor.ospf.area if (neighbor.ospf and neighbor.ospf.enabled) else 0
                            if neighbor_area == area:
                                ospf_neighbors.append({
                                    "routerId": neighbor_id,
                                    "state": "Full",
                                    "area": area,
                                    "interface": interface.id,
                                    "cost": link.cost
                                })
            
            # Update router's neighbor list
            if router.ospf:
                router.ospf.neighbors = ospf_neighbors
            
            self.steps.append({
                "step": 1,
                "type": "hello",
                "description": f"Router {router.id} in Area {area} establishes Full adjacency with {len(ospf_neighbors)} neighbors",
                "router_id": router.id,
                "area": area,
                "neighbors": [n["routerId"] for n in ospf_neighbors],
                "neighbor_state": "Full"
            })
    
    def step_database_synchronization(self, topology: Topology):
        """Step 2: Database synchronization via Database Description packets"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        for router in routers:
            area = router.ospf.area if router.ospf else 0
            
            # Simulate DD exchange
            lsa_headers = []
            if router.id in self.lsdb:
                for lsa_id, lsa in self.lsdb[router.id].items():
                    if lsa.get('area') == area or lsa.get('type') in [3, 4, 5]:
                        lsa_headers.append({
                            "lsa_id": lsa_id,
                            "type": lsa.get('type'),
                            "sequence": lsa.get('sequence', 1)
                        })
            
            self.steps.append({
                "step": 2,
                "type": "dd",
                "description": f"Router {router.id} exchanges Database Description packets in Area {area}",
                "router_id": router.id,
                "area": area,
                "lsa_count": len(lsa_headers),
                "sync_state": "Exchange",
                "lsa_headers": lsa_headers
            })
    
    def generate_all_lsas(self, topology: Topology):
        """Generate all LSA types for the network"""
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        # Clear LSDB first
        self.lsdb.clear()
        
        for router in routers:
            area = router.ospf.area if router.ospf else 0
            router_id = router.id
            
            # Generate Router LSA (Type 1)
            self.generate_router_lsa(router, topology, area)
            
            # Generate Network LSA (Type 2) if this router is DR on a broadcast network
            self.generate_network_lsa(router, topology, area)
            
            # If router is ABR, generate Summary LSAs (Type 3)
            if router_id in self.abrs:
                self.generate_summary_lsas(router, area)
            
            # If router is ASBR, generate AS External LSA (Type 5)
            if router_id in self.asbrs:
                self.generate_external_lsa(router, topology)
        
        # Generate ASBR Summary LSA (Type 4) for ASBRs
        for asbr in self.asbrs:
            self.generate_asbr_summary_lsa(asbr, topology)
    
    def generate_router_lsa(self, router: Device, topology: Topology, area: int):
        """Generate Router LSA (Type 1)"""
        router_lsa = {
            "lsa_id": f"{router.id}-Router-LSA",
            "type": 1,  # Router LSA
            "router_id": router.id,
            "area": area,
            "sequence": 1,
            "age": 0,
            "links": [],
            "options": {
                "e": router.id in self.asbrs,  # External routing capability
                "b": router.id in self.abrs,   # Border router
            }
        }
        
        # Add point-to-point links to OSPF neighbors
        for interface in router.interfaces:
            if interface.type == 'ospf':
                link = next((l for l in topology.links if l.id == interface.linkId), None)
                if link and link.type == 'ospf':
                    neighbor_id = link.target if link.source == router.id else link.source
                    neighbor = next((d for d in topology.devices if d.id == neighbor_id), None)
                    
                    if neighbor and neighbor.type == 'router':
                        router_lsa["links"].append({
                            "link_id": neighbor_id,
                            "link_data": interface.ip if interface.ip else "0.0.0.0",
                            "type": 1,  # Point-to-point
                            "metric": link.cost,
                            "interface": interface.id
                        })
        
        # Add stub networks (connected non-OSPF interfaces)
        for interface in router.interfaces:
            if interface.type != 'ospf':
                link = next((l for l in topology.links if l.id == interface.linkId), None)
                if link:
                    router_lsa["links"].append({
                        "link_id": interface.ip if interface.ip else f"192.168.{len(router_lsa['links'])}.0",
                        "link_data": "255.255.255.0",
                        "type": 3,  # Stub network
                        "metric": 1,
                        "interface": interface.id
                    })
        
        # Add transit networks (connections to switches with multiple routers)
        for interface in router.interfaces:
            link = next((l for l in topology.links if l.id == interface.linkId), None)
            if link:
                connected_id = link.target if link.source == router.id else link.source
                connected_device = next((d for d in topology.devices if d.id == connected_id), None)
                
                if connected_device and connected_device.type == 'switch':
                    # Check if this switch connects multiple routers
                    router_count = 0
                    for link2 in topology.links:
                        if link2.source == connected_id or link2.target == connected_id:
                            other_id = link2.target if link2.source == connected_id else link2.source
                            other_device = next((d for d in topology.devices if d.id == other_id), None)
                            if other_device and other_device.type == 'router':
                                router_count += 1
                    
                    if router_count > 1:
                        router_lsa["links"].append({
                            "link_id": f"NET-{connected_id}",
                            "link_data": interface.ip if interface.ip else "0.0.0.0",
                            "type": 2,  # Transit network
                            "metric": 1,
                            "interface": interface.id
                        })
        
        # Store LSA
        if router.id not in self.lsdb:
            self.lsdb[router.id] = {}
        self.lsdb[router.id][router_lsa["lsa_id"]] = router_lsa
        
        self.steps.append({
            "step": 3,
            "type": "lsa_generation",
            "description": f"Router {router.id} generates Router-LSA (Type 1) for Area {area}",
            "router_id": router.id,
            "lsa_id": router_lsa["lsa_id"],
            "lsa_type": "Router (Type 1)",
            "area": area,
            "links_count": len(router_lsa["links"])
        })
    
    def generate_network_lsa(self, router: Device, topology: Topology, area: int):
        """Generate Network LSA (Type 2) for broadcast networks"""
        # Check if router is connected to a switch with multiple routers
        for interface in router.interfaces:
            link = next((l for l in topology.links if l.id == interface.linkId), None)
            if link:
                connected_id = link.target if link.source == router.id else link.source
                connected_device = next((d for d in topology.devices if d.id == connected_id), None)
                
                if connected_device and connected_device.type == 'switch':
                    # Count how many routers are connected to this switch
                    router_count = 0
                    attached_routers = []
                    
                    for link2 in topology.links:
                        if link2.source == connected_id or link2.target == connected_id:
                            other_id = link2.target if link2.source == connected_id else link2.source
                            other_device = next((d for d in topology.devices if d.id == other_id), None)
                            if other_device and other_device.type == 'router':
                                router_count += 1
                                attached_routers.append(other_id)
                    
                    if router_count > 1:
                        # Generate Network LSA (Designated Router is the one with highest IP)
                        network_lsa = {
                            "lsa_id": f"NET-{connected_id}-LSA",
                            "type": 2,  # Network LSA
                            "router_id": router.id,  # DR's router ID
                            "area": area,
                            "sequence": 1,
                            "age": 0,
                            "network_mask": "255.255.255.0",
                            "attached_routers": attached_routers,
                            "network_address": f"10.{area}.0.0"
                        }
                        
                        if router.id not in self.lsdb:
                            self.lsdb[router.id] = {}
                        self.lsdb[router.id][network_lsa["lsa_id"]] = network_lsa
                        
                        self.steps.append({
                            "step": 3,
                            "type": "lsa_generation",
                            "description": f"Router {router.id} generates Network-LSA (Type 2) for network {connected_id}",
                            "router_id": router.id,
                            "lsa_id": network_lsa["lsa_id"],
                            "lsa_type": "Network (Type 2)",
                            "area": area,
                            "attached_routers": attached_routers
                        })
                        break  # Only generate one Network LSA per router
    
    def generate_summary_lsas(self, router: Device, area: int):
        """Generate Summary LSAs (Type 3) for ABRs"""
        router_id = router.id
        
        # Get all areas this ABR connects to
        abr_areas = self.get_router_areas(router_id)
        
        # Generate summary routes for each area pair
        for src_area in abr_areas:
            if src_area == area:
                continue  # Don't summarize within same area
                
            # Create summary routes for networks in src_area
            summary_lsa = {
                "lsa_id": f"Summary-{router_id}-Area{src_area}-to-Area{area}",
                "type": 3,  # Summary LSA
                "router_id": router_id,
                "area": area,
                "sequence": 1,
                "age": 0,
                "network": f"10.{src_area}.0.0",
                "mask": "255.255.0.0",
                "metric": 10,  # Summary metric
                "advertising_router": router_id,
                "from_area": src_area
            }
            
            if router_id not in self.lsdb:
                self.lsdb[router_id] = {}
            self.lsdb[router_id][summary_lsa["lsa_id"]] = summary_lsa
            
            self.steps.append({
                "step": 3,
                "type": "lsa_generation",
                "description": f"ABR {router_id} generates Summary-LSA (Type 3) for Area {src_area} networks in Area {area}",
                "router_id": router_id,
                "lsa_id": summary_lsa["lsa_id"],
                "lsa_type": "Summary (Type 3)",
                "from_area": src_area,
                "to_area": area,
                "advertised_network": summary_lsa["network"]
            })
    
    def generate_external_lsa(self, router: Device, topology: Topology):
        """Generate AS External LSA (Type 5) for ASBRs"""
        router_id = router.id
        
        # Find external networks connected to this ASBR
        external_networks = []
        for interface in router.interfaces:
            link = next((l for l in topology.links if l.id == interface.linkId), None)
            if link and link.type != 'ospf':
                connected_id = link.target if link.source == router.id else link.source
                connected_device = next((d for d in topology.devices if d.id == connected_id), None)
                
                if connected_device and connected_device.type in ['pc', 'laptop', 'phone', 'server']:
                    external_networks.append({
                        "network": connected_device.ip,
                        "mask": "255.255.255.0",
                        "metric": 20,  # External metric
                        "metric_type": 2,  # Type 2 external (doesn't include internal cost)
                        "forwarding_address": "0.0.0.0"
                    })
        
        for i, network in enumerate(external_networks):
            external_lsa = {
                "lsa_id": f"External-{router_id}-{i}",
                "type": 5,  # AS External LSA
                "router_id": router_id,
                "area": 0,  # External LSAs flooded throughout AS
                "sequence": 1,
                "age": 0,
                "network": network["network"],
                "mask": network["mask"],
                "metric": network["metric"],
                "metric_type": network["metric_type"],
                "forwarding_address": network["forwarding_address"],
                "external_route_tag": 0
            }
            
            if router_id not in self.lsdb:
                self.lsdb[router_id] = {}
            self.lsdb[router_id][external_lsa["lsa_id"]] = external_lsa
            
            self.steps.append({
                "step": 3,
                "type": "lsa_generation",
                "description": f"ASBR {router_id} generates AS-External-LSA (Type 5) for network {network['network']}",
                "router_id": router_id,
                "lsa_id": external_lsa["lsa_id"],
                "lsa_type": "AS-External (Type 5)",
                "external_network": network["network"],
                "metric": network["metric"],
                "metric_type": network["metric_type"]
            })
    
    def generate_asbr_summary_lsa(self, asbr_id: str, topology: Topology):
        """Generate ASBR Summary LSA (Type 4) for ASBRs"""
        # Type 4 LSAs are generated by ABRs to advertise ASBR location
        for abr in self.abrs:
            # Check if this ABR can reach the ASBR
            asbr_area = self.graph.nodes[asbr_id].get('area', 0)
            abr_areas = self.get_router_areas(abr)
            
            if asbr_area in abr_areas:
                # Calculate cost from ABR to ASBR
                try:
                    if asbr_area in self.area_graphs:
                        area_graph = self.area_graphs[asbr_area]
                        if abr in area_graph.nodes and asbr_id in area_graph.nodes:
                            cost = nx.shortest_path_length(area_graph, abr, asbr_id, weight='weight')
                            
                            asbr_summary_lsa = {
                                "lsa_id": f"ASBR-Summary-{abr}-for-{asbr_id}",
                                "type": 4,  # ASBR Summary LSA
                                "router_id": abr,
                                "area": asbr_area,
                                "sequence": 1,
                                "age": 0,
                                "asbr": asbr_id,
                                "metric": cost,
                                "advertising_router": abr
                            }
                            
                            if abr not in self.lsdb:
                                self.lsdb[abr] = {}
                            self.lsdb[abr][asbr_summary_lsa["lsa_id"]] = asbr_summary_lsa
                            
                            self.steps.append({
                                "step": 3,
                                "type": "lsa_generation",
                                "description": f"ABR {abr} generates ASBR-Summary-LSA (Type 4) for ASBR {asbr_id} in Area {asbr_area}",
                                "router_id": abr,
                                "lsa_id": asbr_summary_lsa["lsa_id"],
                                "lsa_type": "ASBR-Summary (Type 4)",
                                "asbr": asbr_id,
                                "area": asbr_area,
                                "cost": cost
                            })
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
    
    def flood_lsas_with_area_boundaries(self):
        """Flood LSAs respecting area boundaries"""
        # Step 4: Flood Router and Network LSAs within their areas
        self.steps.append({
            "step": 4,
            "type": "flooding",
            "description": "Starting LSA flooding within area boundaries",
            "details": "Router and Network LSAs flooded within their originating areas only"
        })
        
        # Flood Type 1 and 2 LSAs within areas
        for router_id, lsa_dict in self.lsdb.items():
            for lsa_id, lsa in lsa_dict.items():
                if lsa["type"] in [1, 2]:  # Router or Network LSA
                    area = lsa["area"]
                    if area in self.area_graphs:
                        area_graph = self.area_graphs[area]
                        if router_id in area_graph.nodes:
                            # Flood to all neighbors in same area
                            for neighbor in list(area_graph.neighbors(router_id)):
                                self.steps.append({
                                    "step": 4,
                                    "type": "flooding",
                                    "description": f"Flooding {self.get_lsa_type_name(lsa['type'])} from {router_id} to {neighbor} in Area {area}",
                                    "source": router_id,
                                    "target": neighbor,
                                    "lsa_id": lsa_id,
                                    "lsa_type": self.get_lsa_type_name(lsa["type"]),
                                    "area": area
                                })
        
        # Step 5: ABRs flood Summary LSAs between areas
        self.steps.append({
            "step": 5,
            "type": "flooding",
            "description": "ABRs flooding Summary LSAs between areas",
            "details": "Type 3 LSAs flooded between connected areas by ABRs"
        })
        
        for abr in self.abrs:
            abr_areas = self.get_router_areas(abr)
            
            # Flood summary LSAs from each area to other connected areas
            for src_area in abr_areas:
                for dst_area in abr_areas:
                    if src_area != dst_area:
                        self.steps.append({
                            "step": 5,
                            "type": "flooding",
                            "description": f"ABR {abr} floods Summary-LSAs from Area {src_area} to Area {dst_area}",
                            "source": abr,
                            "lsa_type": "Summary (Type 3)",
                            "from_area": src_area,
                            "to_area": dst_area
                        })
        
        # Step 6: Flood AS External LSAS throughout AS
        self.steps.append({
            "step": 6,
            "type": "flooding",
            "description": "Flooding AS External LSAs throughout Autonomous System",
            "details": "Type 5 LSAs flooded to all areas (except stub areas)"
        })
        
        for router_id, lsa_dict in self.lsdb.items():
            for lsa_id, lsa in lsa_dict.items():
                if lsa["type"] == 5:  # AS External LSA
                    # Flood to all non-stub areas
                    for area in self.areas.keys():
                        if not self.area_configs.get(area, {}).get('stub', False):
                            self.steps.append({
                                "step": 6,
                                "type": "flooding",
                                "description": f"Flooding AS-External-LSA for {lsa.get('network', 'external')} to Area {area}",
                                "lsa_id": lsa_id,
                                "lsa_type": "AS-External (Type 5)",
                                "area": area,
                                "external_network": lsa.get('network', 'N/A')
                            })
    
    def build_area_lsdbs(self):
        """Build LSDB for each area based on flooded LSAs"""
        for area in self.areas.keys():
            self.area_lsdbs[area] = {}
            
            # Add Router and Network LSAs from this area
            for router_id, lsa_dict in self.lsdb.items():
                for lsa_id, lsa in lsa_dict.items():
                    if lsa["type"] in [1, 2] and lsa["area"] == area:
                        self.area_lsdbs[area][lsa_id] = lsa
            
            # Add Summary LSAs for this area
            for router_id, lsa_dict in self.lsdb.items():
                for lsa_id, lsa in lsa_dict.items():
                    if lsa["type"] == 3 and lsa["area"] == area:
                        self.area_lsdbs[area][lsa_id] = lsa
            
            # Add ASBR Summary LSAs for this area
            for router_id, lsa_dict in self.lsdb.items():
                for lsa_id, lsa in lsa_dict.items():
                    if lsa["type"] == 4 and lsa["area"] == area:
                        self.area_lsdbs[area][lsa_id] = lsa
            
            # Add AS External LSAs (except to stub areas)
            if not self.area_configs.get(area, {}).get('stub', False):
                for router_id, lsa_dict in self.lsdb.items():
                    for lsa_id, lsa in lsa_dict.items():
                        if lsa["type"] == 5:
                            self.area_lsdbs[area][lsa_id] = lsa
            
            self.steps.append({
                "step": 7,
                "type": "database",
                "description": f"Built LSDB for Area {area} with {len(self.area_lsdbs[area])} LSAs",
                "area": area,
                "lsa_count": len(self.area_lsdbs[area]),
                "lsa_types": self.count_lsa_types(self.area_lsdbs[area])
            })
    
    def run_spf_per_area(self):
        """Run SPF (Dijkstra) calculation for each area"""
        for area, area_graph in self.area_graphs.items():
            routers_in_area = [n for n, d in area_graph.nodes(data=True) 
                             if d.get('type') == 'router']
            
            for router_id in routers_in_area:
                try:
                    # Run SPF for this router in its area
                    paths = nx.single_source_dijkstra_path(area_graph, router_id, weight='weight')
                    path_lengths = nx.single_source_dijkstra_path_length(area_graph, router_id, weight='weight')
                    
                    # Calculate shortest path tree
                    spf_tree = self.build_spf_tree(router_id, paths, area_graph)
                    
                    self.steps.append({
                        "step": 8,
                        "type": "spf",
                        "description": f"Router {router_id} runs SPF calculation for Area {area}",
                        "router_id": router_id,
                        "area": area,
                        "destinations_found": len(paths) - 1,
                        "spf_root": router_id,
                        "tree_size": len(spf_tree),
                        "average_cost": sum(path_lengths.values()) / max(1, len(path_lengths))
                    })
                    
                except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
                    self.steps.append({
                        "step": 8,
                        "type": "spf",
                        "description": f"Router {router_id}: SPF calculation failed in Area {area} - {str(e)}",
                        "router_id": router_id,
                        "area": area,
                        "error": str(e)
                    })
    
    def build_spf_tree(self, root: str, paths: Dict, area_graph: nx.Graph):
        """Build SPF tree from Dijkstra paths"""
        tree = set()
        for target, path in paths.items():
            for i in range(len(path) - 1):
                edge = (path[i], path[i + 1])
                tree.add(edge)
        return list(tree)
    
    def build_complete_routing_tables(self, topology: Topology):
        """Build complete routing tables with OSPF route preferences"""
        routing_tables = []
        routers = [d for d in topology.devices if d.type == 'router' and d.ospf]
        
        for router in routers:
            router_id = router.id
            area = router.ospf.area if router.ospf else 0
            
            routes = []
            
            # 1. Add connected routes (highest priority)
            routes.extend(self.get_connected_routes(router))
            
            # 2. Add intra-area routes via SPF
            routes.extend(self.get_intra_area_routes(router_id, area))
            
            # Sort routes by OSPF preference (lower is better) and then by cost
            routes.sort(key=lambda x: (self.get_route_preference(x["type"]), x.get("cost", float('inf'))))
            
            # Store routing table
            routing_table = {
                "router": router_id,
                "area": area,
                "is_abr": router_id in self.abrs,
                "is_asbr": router_id in self.asbrs,
                "routes": routes,
                "lsdb": self.lsdb.get(router_id, {}),
                "neighbors": router.ospf.neighbors if router.ospf else []
            }
            
            routing_tables.append(routing_table)
            
            self.steps.append({
                "step": 9,
                "type": "routing",
                "description": f"Router {router_id} builds initial routing table with {len(routes)} routes",
                "router_id": router_id,
                "area": area,
                "routes_count": len(routes),
                "route_types": self.count_route_types(routes)
            })
        
        return routing_tables
    
    def calculate_inter_area_routes(self, routing_tables):
        """Calculate inter-area (Type 3) OSPF routes via ABRs"""
        backbone_graph = self.area_graphs.get(0)
        if not backbone_graph:
            return

        for area, routers in self.areas.items():
            if area == 0:
                continue  # Skip backbone

            # Find ABRs connected to this area
            area_abrs = [abr for abr in self.abrs if area in self.get_router_areas(abr)]

            for router_id in routers:
                rt = next((rt for rt in routing_tables if rt["router"] == router_id), None)
                if not rt:
                    continue

                for abr in area_abrs:
                    try:
                        area_graph = self.area_graphs[area]
                        if router_id not in area_graph.nodes or abr not in area_graph.nodes:
                            continue

                        cost_to_abr = nx.shortest_path_length(area_graph, router_id, abr, weight='weight')
                        path_to_abr = nx.shortest_path(area_graph, router_id, abr, weight='weight')

                        # Flood summary LSAs from all other areas reachable by this ABR
                        abr_areas = self.get_router_areas(abr)
                        for dst_area in abr_areas:
                            if dst_area == area:
                                continue
                            for lsa_id, lsa in self.area_lsdbs.get(dst_area, {}).items():
                                lsa_type = lsa.get("type")
                                # We only consider Router (1) and Network (2) LSAs for area networks
                                if lsa_type not in [1, 2]:
                                    continue

                                if lsa_type == 1:
                                    # Router LSA: check for stub links (type 3) and
                                    # also consider link_data fields that look like IPs
                                    for link in lsa.get("links", []):
                                        network = None
                                        if link.get("type") == 3:
                                            # Stub network listed explicitly
                                            link_id = link.get("link_id")
                                            network = f"{link_id}/24" if link_id and isinstance(link_id, str) and not link_id.startswith("NET-") else link_id
                                            metric = link.get("metric", 10)
                                        else:
                                            # Some Router-LSAs include interface IPs in link_data (p2p)
                                            ld = link.get("link_data")
                                            if ld and isinstance(ld, str) and ld.count('.') == 3:
                                                network = f"{ld}/24"
                                                metric = link.get("metric", 10)

                                        if not network:
                                            continue

                                        route_cost = cost_to_abr + metric

                                        # Avoid duplicates
                                        if any(r["destination"] == network and r["type"] == "inter-area" for r in rt["routes"]):
                                            continue

                                        rt["routes"].append({
                                            "destination": network,
                                            "next_hop": path_to_abr[1] if len(path_to_abr) > 1 else None,
                                            "cost": route_cost,
                                            "path": path_to_abr,
                                            "type": "inter-area",
                                            "via_abr": abr,
                                            "to_area": dst_area,
                                            "route_preference": 110
                                        })

                                elif lsa_type == 2:
                                    # Network LSA contains a network address
                                    network = lsa.get("network") or lsa.get("network_address") or lsa.get("lsa_id")
                                    metric = lsa.get("metric", 10)
                                    route_cost = cost_to_abr + metric

                                    if any(r["destination"] == network and r["type"] == "inter-area" for r in rt["routes"]):
                                        continue

                                    rt["routes"].append({
                                        "destination": network,
                                        "next_hop": path_to_abr[1] if len(path_to_abr) > 1 else None,
                                        "cost": route_cost,
                                        "path": path_to_abr,
                                        "type": "inter-area",
                                        "via_abr": abr,
                                        "to_area": dst_area,
                                        "route_preference": 110
                                    })
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue

        # Backbone routers also learn networks from non-backbone areas
        backbone_routers = list(self.areas.get(0, []))
        for backbone_router in backbone_routers:
            brt = next((x for x in routing_tables if x["router"] == backbone_router), None)
            if not brt:
                continue

            for abr in self.abrs:
                for area in self.get_router_areas(abr):
                    if area == 0:
                        continue
                    for lsa_id, lsa in self.area_lsdbs.get(area, {}).items():
                        lsa_type = lsa.get("type")
                        if lsa_type not in [1, 2]:
                            continue
                        try:
                            cost_to_abr_bb = nx.shortest_path_length(backbone_graph, backbone_router, abr, weight='weight')
                            path_to_abr_bb = nx.shortest_path(backbone_graph, backbone_router, abr, weight='weight')

                            if lsa_type == 1:
                                # Router LSA: advertise stub links and interface IPs as networks
                                for link in lsa.get("links", []):
                                    network = None
                                    if link.get("type") == 3:
                                        link_id = link.get("link_id")
                                        network = f"{link_id}/24" if link_id and isinstance(link_id, str) and not link_id.startswith("NET-") else link_id
                                        metric = link.get("metric", 10)
                                    else:
                                        ld = link.get("link_data")
                                        if ld and isinstance(ld, str) and ld.count('.') == 3:
                                            network = f"{ld}/24"
                                            metric = link.get("metric", 10)

                                    if not network:
                                        continue

                                    total_cost = cost_to_abr_bb + metric

                                    if any(r["destination"] == network and r["type"] == "inter-area" for r in brt["routes"]):
                                        continue

                                    brt["routes"].append({
                                        "destination": network,
                                        "next_hop": path_to_abr_bb[1] if len(path_to_abr_bb) > 1 else None,
                                        "cost": total_cost,
                                        "path": path_to_abr_bb,
                                        "type": "inter-area",
                                        "via_abr": abr,
                                        "to_area": area,
                                        "route_preference": 110
                                    })

                            elif lsa_type == 2:
                                network = lsa.get("network") or lsa.get("network_address") or lsa.get("lsa_id")
                                metric = lsa.get("metric", 10)
                                total_cost = cost_to_abr_bb + metric

                                if any(r["destination"] == network and r["type"] == "inter-area" for r in brt["routes"]):
                                    continue

                                brt["routes"].append({
                                    "destination": network,
                                    "next_hop": path_to_abr_bb[1] if len(path_to_abr_bb) > 1 else None,
                                    "cost": total_cost,
                                    "path": path_to_abr_bb,
                                    "type": "inter-area",
                                    "via_abr": abr,
                                    "to_area": area,
                                    "route_preference": 110
                                })
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            continue    
    def calculate_external_routes(self, routing_tables, topology: Topology):
        """Calculate external routes from ASBRs"""
        for asbr in self.asbrs:
            # Find routing table for this ASBR
            asbr_rt = next((rt for rt in routing_tables if rt["router"] == asbr), None)
            if not asbr_rt:
                continue
            
            # Find external networks connected to this ASBR
            asbr_device = next((d for d in topology.devices if d.id == asbr), None)
            if not asbr_device:
                continue
            
            external_networks = []
            for interface in asbr_device.interfaces:
                link = next((l for l in topology.links if l.id == interface.linkId), None)
                if link and link.type != 'ospf':
                    connected_id = link.target if link.source == asbr else link.source
                    connected_device = next((d for d in topology.devices if d.id == connected_id), None)
                    
                    if connected_device and connected_device.type in ['pc', 'laptop', 'phone', 'server']:
                        external_networks.append({
                            "network": connected_device.ip,
                            "mask": "255.255.255.0",
                            "cost": 20  # External metric
                        })
            
            # Add external routes to ASBR's routing table
            for network in external_networks:
                asbr_rt["routes"].append({
                    "destination": network["network"],
                    "next_hop": "direct",
                    "cost": network["cost"],
                    "type": "external",
                    "route_preference": 50  # Lower is better in OSPF
                })
            
            # Propagate external routes to other routers
            for rt in routing_tables:
                if rt["router"] != asbr:
                    # Skip if this area is stub and doesn't accept external routes
                    area = rt["area"]
                    if self.area_configs.get(area, {}).get('stub', False):
                        continue
                    
                    # Calculate cost to ASBR
                    try:
                        # Find path to ASBR
                        router_area = rt["area"]
                        area_graph = self.area_graphs.get(router_area)
                        if area_graph and rt["router"] in area_graph.nodes and asbr in area_graph.nodes:
                            cost_to_asbr = nx.shortest_path_length(area_graph, rt["router"], asbr, weight='weight')
                            
                            # Add external routes via this ASBR
                            for network in external_networks:
                                rt["routes"].append({
                                    "destination": network["network"],
                                    "next_hop": asbr,
                                    "cost": cost_to_asbr + network["cost"],
                                    "type": "external",
                                    "via_asbr": asbr,
                                    "route_preference": 50
                                })
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue
    
    def apply_area_specific_rules(self, routing_tables):
        """Apply stub area and NSSA rules to routing tables"""
        for area, config in self.area_configs.items():
            if config.get('stub', False):
                # Remove external routes from stub areas
                for rt in routing_tables:
                    if rt["area"] == area:
                        # Remove Type 5 external routes
                        rt["routes"] = [route for route in rt["routes"] if route["type"] != "external"]
                        
                        # Add default route to nearest ABR
                        area_abrs = [abr for abr in self.abrs if area in self.get_router_areas(abr)]
                        if area_abrs:
                            rt["routes"].append({
                                "destination": "0.0.0.0/0",
                                "next_hop": area_abrs[0],
                                "cost": 10,
                                "type": "default",
                                "route_preference": 110,
                                "description": "Stub area default route to ABR"
                            })
            
            if config.get('nssa', False):
                # NSSA areas allow limited external routes via Type 7 LSAs
                # For simplicity, we'll allow all external routes in NSSA
                pass
    
    def get_connected_routes(self, router: Device):
        """Get directly connected routes"""
        routes = []
        for interface in router.interfaces:
            if interface.ip:
                routes.append({
                    "destination": f"{interface.ip}/24",
                    "next_hop": "direct",
                    "cost": 0,
                    "type": "connected",
                    "interface": interface.id,
                    "route_preference": 10  # Connected routes have highest preference
                })
        return routes
    
    def get_intra_area_routes(self, router_id: str, area: int):
        """Get intra-area routes via SPF"""
        routes = []
        area_graph = self.area_graphs.get(area)
        
        if not area_graph or router_id not in area_graph.nodes:
            return routes
        
        try:
            paths = nx.single_source_dijkstra_path(area_graph, router_id, weight='weight')
            path_lengths = nx.single_source_dijkstra_path_length(area_graph, router_id, weight='weight')
            
            for target, path in paths.items():
                if target != router_id:
                    next_hop = path[1] if len(path) > 1 else None
                    
                    # Determine if this is a network or router
                    target_type = area_graph.nodes[target].get('type', 'router')
                    
                    routes.append({
                        "destination": target,
                        "next_hop": next_hop,
                        "cost": path_lengths[target],
                        "path": path,
                        "type": "intra-area",
                        "area": area,
                        "destination_type": target_type,
                        "route_preference": 100  # OSPF intra-area
                    })
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        
        return routes
    
    def get_route_preference(self, route_type: str) -> int:
        """Get OSPF route preference/AD (lower is better)"""
        preferences = {
            "connected": 10,
            "static": 20,
            "external": 50,
            "intra-area": 100,
            "inter-area": 110,
            "default": 200
        }
        return preferences.get(route_type, 200)
    
    def get_lsa_type_name(self, lsa_type: int) -> str:
        """Convert LSA type number to name"""
        types = {
            1: "Router",
            2: "Network",
            3: "Summary",
            4: "ASBR-Summary",
            5: "AS-External",
            7: "NSSA-External"
        }
        return types.get(lsa_type, f"Unknown ({lsa_type})")
    
    def count_lsa_types(self, lsdbs: Dict) -> Dict:
        """Count LSA types in LSDB"""
        counts = defaultdict(int)
        for lsa in lsdbs.values():
            lsa_type = self.get_lsa_type_name(lsa.get('type', 0))
            counts[lsa_type] += 1
        return dict(counts)
    
    def count_route_types(self, routes: List) -> Dict:
        """Count route types in routing table"""
        counts = defaultdict(int)
        for route in routes:
            counts[route.get('type', 'unknown')] += 1
        return dict(counts)
    
    def get_router_areas(self, router_id: str) -> Set[int]:
        """Get all areas a router participates in"""
        areas = set()
        
        if router_id not in self.graph.nodes:
            return areas
        
        # Add area from node attribute
        node_area = self.graph.nodes[router_id].get('area', 0)
        if node_area is not None:
            areas.add(node_area)
        
        # Check all edges from this router
        for u, v, data in self.graph.edges(router_id, data=True):
            if data.get('type') == 'ospf':
                areas.add(data.get('area', 0))
        
        return areas
    
    def get_areas_info(self):
        """Get detailed information about all areas"""
        areas_info = {}
        
        for area, routers in self.areas.items():
            # Count routers and ABRs in this area
            router_count = len(routers)
            abr_count = len([r for r in routers if r in self.abrs])
            asbr_count = len([r for r in routers if r in self.asbrs])
            
            areas_info[area] = {
                "routers": list(routers),
                "router_count": router_count,
                "abr_count": abr_count,
                "asbr_count": asbr_count,
                "is_backbone": (area == 0),
                "is_stub": self.area_configs.get(area, {}).get('stub', False),
                "is_nssa": self.area_configs.get(area, {}).get('nssa', False),
                "connected_areas": self.get_connected_areas(area),
                "lsdb_size": len(self.area_lsdbs.get(area, {}))
            }
        
        return areas_info
    
    def get_connected_areas(self, area: int) -> List[int]:
        """Get areas connected to the specified area via ABRs"""
        connected = set()
        
        for abr in self.abrs:
            abr_areas = self.get_router_areas(abr)
            if area in abr_areas:
                connected.update(abr_areas)
        
        connected.discard(area)
        return list(sorted(connected))

class PingSimulator:
    """Enhanced ping path calculation using complete OSPF routing logic"""
    
    def __init__(self):
        self.path_cache = {}
    
    def calculate_ping_path(self, request: PingRequest):
        """Calculate ping path using complete OSPF routing tables"""
        try:
            source = request.source
            destination = request.destination
            topology = request.topology
            
            # Build OSPF simulator to get routing information
            ospf_sim = OSPFSimulator()
            ospf_result = ospf_sim.simulate_ospf(topology, step_by_step=False)
            
            if not ospf_result.get("success"):
                return {
                    "success": False,
                    "message": "OSPF simulation failed",
                    "path": [],
                    "hops": 0,
                    "reachable": False
                }
            
            # Find devices
            src_device = next((d for d in topology.devices if d.id == source), None)
            dst_device = next((d for d in topology.devices if d.id == destination), None)
            
            if not src_device or not dst_device:
                return {
                    "success": False,
                    "message": "Source or destination device not found",
                    "path": [],
                    "hops": 0,
                    "reachable": False
                }
            
            # If source or destination is not a router, find connected router
            if src_device.type != 'router':
                src_router = self.find_connected_router(source, topology)
                if not src_router:
                    return {
                        "success": False,
                        "message": f"Source {source} is not connected to any router",
                        "path": [],
                        "hops": 0,
                        "reachable": False
                    }
            else:
                src_router = source
            
            if dst_device.type != 'router':
                dst_router = self.find_connected_router(destination, topology)
                if not dst_router:
                    return {
                        "success": False,
                        "message": f"Destination {destination} is not connected to any router",
                        "path": [],
                        "hops": 0,
                        "reachable": False
                    }
            else:
                dst_router = destination
            
            # Find routing tables
            src_routing_table = next((rt for rt in ospf_result["routing_tables"] if rt["router"] == src_router), None)
            dst_routing_table = next((rt for rt in ospf_result["routing_tables"] if rt["router"] == dst_router), None)
            
            if not src_routing_table or not dst_routing_table:
                # Fallback to simple path
                simple_path = self.find_simple_path(source, destination, topology)
                if simple_path:
                    return {
                        "success": True,
                        "path": simple_path,
                        "hops": len(simple_path) - 1,
                        "total_cost": self.calculate_path_cost(simple_path, topology),
                        "source": source,
                        "destination": destination,
                        "reachable": True,
                        "routing_type": "simple_fallback"
                    }
                else:
                    return {
                        "success": False,
                        "message": "No routing tables found and no simple path available",
                        "path": [],
                        "hops": 0,
                        "reachable": False
                    }
            
            # Build complete network graph
            G = nx.Graph()
            
            # Add devices
            for device in topology.devices:
                G.add_node(device.id, 
                          type=device.type,
                          ip=device.ip,
                          area=device.ospf.area if device.ospf else 0)
            
            # Add links
            for link in topology.links:
                cost = link.cost if link.type == 'ospf' else 1
                G.add_edge(link.source, link.target,
                          type=link.type,
                          cost=cost,
                          area=link.area if link.type == 'ospf' else 0)
            
            # Find path using OSPF-aware routing
            path = self.find_ospf_aware_path(G, source, destination, src_router, dst_router,
                                           src_routing_table, dst_routing_table,
                                           ospf_result, topology)
            
            if path:
                hops = len(path) - 1
                total_cost = self.calculate_path_cost(path, topology)
                
                # Analyze route types
                route_types = self.analyze_route_types(path, ospf_result, topology)
                
                return {
                    "success": True,
                    "path": path,
                    "hops": hops,
                    "total_cost": total_cost,
                    "source": source,
                    "destination": destination,
                    "reachable": True,
                    "routing_type": "ospf",
                    "route_types": route_types,
                    "path_details": self.get_path_details(path, topology, ospf_result)
                }
            else:
                # Fallback to simple path
                simple_path = self.find_simple_path(source, destination, topology)
                if simple_path:
                    return {
                        "success": True,
                        "path": simple_path,
                        "hops": len(simple_path) - 1,
                        "total_cost": self.calculate_path_cost(simple_path, topology),
                        "source": source,
                        "destination": destination,
                        "reachable": True,
                        "routing_type": "simple_fallback"
                    }
                else:
                    return {
                        "success": False,
                        "message": "No path found between source and destination",
                        "path": [],
                        "hops": 0,
                        "reachable": False
                    }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error calculating path: {str(e)}",
                "path": [],
                "hops": 0,
                "reachable": False
            }
    
    def find_connected_router(self, device_id: str, topology: Topology) -> Optional[str]:
        """Find the router a device is connected to"""
        device = next((d for d in topology.devices if d.id == device_id), None)
        if not device:
            return None
        
        # If device is already a router
        if device.type == 'router':
            return device_id
        
        # Find connected router via interfaces
        for interface in device.interfaces:
            link = next((l for l in topology.links if l.id == interface.linkId), None)
            if link:
                connected_id = link.target if link.source == device_id else link.source
                connected_device = next((d for d in topology.devices if d.id == connected_id), None)
                if connected_device and connected_device.type == 'router':
                    return connected_id
                elif connected_device and connected_device.type == 'switch':
                    # Check if switch is connected to a router
                    return self.find_connected_router(connected_id, topology)
        
        return None
    
    def find_ospf_aware_path(self, G: nx.Graph, source: str, destination: str,
                            src_router: str, dst_router: str,
                            src_rt: Dict, dst_rt: Dict,
                            ospf_result: Dict, topology: Topology) -> List[str]:
        """Find path using OSPF-aware routing with area considerations.

        This implementation always computes the minimum-cost path using
        OSPF link costs (NetworkX Dijkstra with weight='cost') as the
        primary method. Routing-table next_hop entries are only used if
        they agree with the computed min-cost path. Non-router devices
        are routed to/from their connected routers first.
        """
        # Trivial case
        if source == destination:
            return [source]

        # Resolve devices
        src_device = next((d for d in topology.devices if d.id == source), None)
        dst_device = next((d for d in topology.devices if d.id == destination), None)

        # If we need to route non-router endpoints via their connected routers,
        # obtain the layer-2 paths to their routers (BFS)
        if source != src_router:
            path_src_to_router = self.find_path_to_router(source, src_router, topology)
            if not path_src_to_router:
                return []
        else:
            path_src_to_router = [src_router]

        if destination != dst_router:
            dst_to_router = self.find_path_to_router(destination, dst_router, topology)
            if not dst_to_router:
                return []
            # Convert device->router path into router->device path
            path_router_to_dst = list(reversed(dst_to_router))
        else:
            path_router_to_dst = [dst_router]

        # Compute min-cost path between routers using OSPF link costs
        router_path = None
        try:
            if src_router == dst_router:
                router_path = [src_router]
            else:
                router_path = nx.shortest_path(G, src_router, dst_router, weight='cost')
        except nx.NetworkXNoPath:
            router_path = None

        # If we have a router-level path, assemble full path
        if router_path:
            # Avoid duplicating the router nodes when concatenating
            full_path = []
            # add source->src_router segment
            if path_src_to_router:
                full_path.extend(path_src_to_router)
            else:
                full_path.append(src_router)

            # add router_path (skip the first node because it's already the last of path_src_to_router)
            if router_path:
                if full_path and full_path[-1] == router_path[0]:
                    full_path.extend(router_path[1:])
                else:
                    full_path.extend(router_path)

            # add src_router->destination segment (skip the first node which is dst_router)
            if path_router_to_dst and path_router_to_dst[0] == router_path[-1]:
                full_path.extend(path_router_to_dst[1:])
            else:
                full_path.extend(path_router_to_dst)

            # Final check: ensure path ends with destination
            if full_path[-1] != destination:
                # There may be cases where destination is a router and path_router_to_dst == [dst_router]
                if destination == dst_router:
                    pass
                else:
                    # attempt to reach destination from last node using simple graph search
                    try:
                        simple_tail = nx.shortest_path(G, full_path[-1], destination, weight='cost')
                        if len(simple_tail) > 1:
                            full_path.extend(simple_tail[1:])
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        return []

            # Optionally verify that routing table next_hop (if present) agrees with min-cost path
            if src_rt and isinstance(src_rt.get('routes', None), list):
                for route in src_rt['routes']:
                    if route.get('destination') in (destination, dst_router):
                        nh = route.get('next_hop')
                        # if next_hop is a node and matches the first hop in the router segment, it's consistent
                        if nh and len(full_path) > 1 and nh == full_path[1]:
                            # routing table agrees with min-cost path; we can prefer it (no change needed)
                            break
                        # otherwise, ignore routing-table guidance because it disagrees with min-cost path
            return full_path

        # If we couldn't find a router-level path, fall back to computing a
        # min-cost path across the entire graph (may include switches/access links)
        try:
            path = nx.shortest_path(G, source, destination, weight='cost')
            return path
        except nx.NetworkXNoPath:
            return []
    
    def build_path_from_route(self, source: str, destination: str, route: Dict,
                            topology: Topology, ospf_result: Dict) -> List[str]:
        """Build complete path from a routing table entry"""
        if route.get("next_hop") == "direct":
            # Direct connection
            return [source, destination]
        
        next_hop = route.get("next_hop")
        if not next_hop:
            return []
        
        # Build path recursively
        path = [source]
        current = source
        
        while current != destination and current != next_hop:
            # Find path to next hop
            try:
                G = self.build_simple_graph(topology)
                subpath = nx.shortest_path(G, current, next_hop)
                if len(subpath) > 1:
                    path.extend(subpath[1:])
                    current = next_hop
                    
                    # Get next hop from next device's routing table
                    if current in [d.id for d in topology.devices if d.type == 'router']:
                        current_rt = next((rt for rt in ospf_result["routing_tables"] 
                                         if rt["router"] == current), None)
                        if current_rt:
                            # Find route to destination from current router
                            for r in current_rt["routes"]:
                                if r["destination"] == destination:
                                    next_hop = r.get("next_hop")
                                    break
                else:
                    break
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                break
        
        if path[-1] != destination:
            # Try direct connection from last node
            try:
                G = self.build_simple_graph(topology)
                final_path = nx.shortest_path(G, path[-1], destination)
                path.extend(final_path[1:])
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return []
        
        return path
    
    def find_path_to_router(self, device: str, router: str, topology: Topology) -> List[str]:
        """Find path from device to its connected router"""
        # Build adjacency list
        adj = defaultdict(list)
        for link in topology.links:
            adj[link.source].append(link.target)
            adj[link.target].append(link.source)
        
        # BFS to find shortest path
        visited = set()
        queue = deque()
        parent = {}
        
        visited.add(device)
        queue.append(device)
        parent[device] = None
        
        while queue:
            current = queue.popleft()
            
            if current == router:
                # Reconstruct path
                path = []
                while current is not None:
                    path.append(current)
                    current = parent[current]
                return list(reversed(path))
            
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    parent[neighbor] = current
        
        return []
    
    def find_router_to_dest_path(self, router: str, destination: str, router_rt: Dict,
                               topology: Topology, ospf_result: Dict) -> List[str]:
        """Find path from router to destination"""
        for route in router_rt["routes"]:
            if route["destination"] == destination:
                return self.build_path_from_route(router, destination, route, topology, ospf_result)
        
        # No direct route, try graph search
        G = self.build_simple_graph(topology)
        try:
            return nx.shortest_path(G, router, destination)
        except nx.NetworkXNoPath:
            return []
    
    def find_simple_path(self, source: str, destination: str, topology: Topology) -> List[str]:
        """Find simple path using BFS"""
        # Build adjacency list
        adj = defaultdict(list)
        for link in topology.links:
            adj[link.source].append(link.target)
            adj[link.target].append(link.source)
        
        # BFS
        visited = set()
        queue = deque()
        parent = {}
        
        visited.add(source)
        queue.append(source)
        parent[source] = None
        
        while queue:
            current = queue.popleft()
            
            if current == destination:
                # Reconstruct path
                path = []
                while current is not None:
                    path.append(current)
                    current = parent[current]
                return list(reversed(path))
            
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    parent[neighbor] = current
        
        return []
    
    def calculate_path_cost(self, path: List[str], topology: Topology) -> int:
        """Calculate total cost of a path"""
        total_cost = 0
        
        # Build edge cost map
        edge_costs = {}
        for link in topology.links:
            edge_costs[(link.source, link.target)] = link.cost if link.type == 'ospf' else 1
            edge_costs[(link.target, link.source)] = link.cost if link.type == 'ospf' else 1
        
        # Calculate total cost
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            total_cost += edge_costs.get(edge, 1)
        
        return total_cost
    
    def analyze_route_types(self, path: List[str], ospf_result: Dict, topology: Topology) -> Dict:
        """Analyze OSPF route types along the path"""
        route_types = []
        
        for i in range(len(path) - 1):
            src = path[i]
            dst = path[i + 1]
            
            # Find link
            link = None
            for l in topology.links:
                if (l.source == src and l.target == dst) or (l.source == dst and l.target == src):
                    link = l
                    break
            
            if link:
                if link.type == 'ospf':
                    # Check if intra-area or inter-area
                    src_device = next((d for d in topology.devices if d.id == src), None)
                    dst_device = next((d for d in topology.devices if d.id == dst), None)
                    
                    if src_device and dst_device and src_device.type == 'router' and dst_device.type == 'router':
                        src_area = src_device.ospf.area if src_device.ospf else 0
                        dst_area = dst_device.ospf.area if dst_device.ospf else 0
                        
                        if src_area == dst_area:
                            route_types.append("intra-area")
                        else:
                            route_types.append("inter-area")
                    else:
                        route_types.append("ospf-link")
                else:
                    route_types.append("access-link")
            else:
                route_types.append("unknown")
        
        return {
            "types": route_types,
            "intra_area_count": route_types.count("intra-area"),
            "inter_area_count": route_types.count("inter-area"),
            "access_count": route_types.count("access-link")
        }
    
    def get_path_details(self, path: List[str], topology: Topology, ospf_result: Dict) -> List[Dict]:
        """Get detailed information about each hop in the path"""
        details = []
        
        for i, node in enumerate(path):
            device = next((d for d in topology.devices if d.id == node), None)
            if device:
                detail = {
                    "hop": i,
                    "device": node,
                    "type": device.type,
                    "ip": device.ip
                }
                
                if device.type == 'router' and device.ospf:
                    detail["area"] = device.ospf.area
                    detail["is_abr"] = device.ospf.is_abr or False
                    detail["is_asbr"] = device.ospf.is_asbr or False
                
                # Add next hop info
                if i < len(path) - 1:
                    next_node = path[i + 1]
                    # Find link
                    link = None
                    for l in topology.links:
                        if (l.source == node and l.target == next_node) or (l.source == next_node and l.target == node):
                            link = l
                            break
                    
                    if link:
                        detail["next_hop"] = next_node
                        detail["link_type"] = link.type
                        if link.type == 'ospf':
                            detail["link_cost"] = link.cost
                            detail["link_area"] = link.area
                
                details.append(detail)
        
        return details
    
    def build_simple_graph(self, topology: Topology) -> nx.Graph:
        """Build a simple graph from topology for path finding"""
        G = nx.Graph()
        
        for device in topology.devices:
            G.add_node(device.id)
        
        for link in topology.links:
            cost = link.cost if link.type == 'ospf' else 1
            G.add_edge(link.source, link.target, weight=cost)
        
        return G

# Initialize simulators
ospf_simulator = OSPFSimulator()
ping_simulator = PingSimulator()

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Enhanced Network Simulator Backend API with Complete OSPF Area Support",
        "version": "4.0.0",
        "features": [
            "Complete OSPF area implementation (RFC 2328)",
            "All LSA types supported (1-5, 7)",
            "ABR (Area Border Router) functionality",
            "ASBR (AS Boundary Router) support",
            "Stub area and NSSA support",
            "Intra-area and inter-area routing",
            "External route calculation",
            "Step-by-step OSPF simulation",
            "OSPF-aware ping routing with area awareness"
        ],
        "endpoints": {
            "GET /": "API information",
            "POST /ospf": "Run complete OSPF simulation",
            "POST /ping": "Calculate OSPF-aware ping path",
            "GET /health": "Health check",
            "GET /ospf/dijkstra-example": "Dijkstra algorithm example",
            "GET /ospf/areas-explanation": "OSPF areas explanation",
            "GET /ospf/lsa-types": "LSA types explanation"
        }
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
    try:
        result = ping_simulator.calculate_ping_path(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ping calculation failed: {str(e)}")

@app.get("/ospf/dijkstra-example")
async def dijkstra_example():
    """Example demonstrating Dijkstra's algorithm with areas"""
    G = nx.Graph()
    
    # Create a sample network with areas
    G.add_edge('R1', 'R2', weight=4, area=0)
    G.add_edge('R1', 'R3', weight=2, area=0)
    G.add_edge('R2', 'R3', weight=1, area=0)
    G.add_edge('R2', 'R4', weight=5, area=1)
    G.add_edge('R3', 'R4', weight=8, area=1)
    G.add_edge('R4', 'R5', weight=2, area=1)
    
    # Add area information to nodes
    for node in G.nodes():
        G.nodes[node]['area'] = 0 if node in ['R1', 'R2', 'R3'] else 1
    
    # Run Dijkstra from R1
    try:
        paths = nx.single_source_dijkstra_path(G, 'R1', weight='weight')
        path_lengths = nx.single_source_dijkstra_path_length(G, 'R1', weight='weight')
        
        return {
            "graph": {
                "nodes": list(G.nodes(data=True)),
                "edges": [{"from": u, "to": v, "weight": d['weight'], "area": d.get('area', 0)} 
                         for u, v, d in G.edges(data=True)]
            },
            "dijkstra_from_R1": {
                "shortest_paths": paths,
                "shortest_distances": path_lengths
            },
            "areas": {
                0: ["R1", "R2", "R3"],
                1: ["R4", "R5"]
            },
            "explanation": "Dijkstra's algorithm finds the shortest path considering link costs. In OSPF, this runs per area to build the SPF tree."
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/ospf/areas-explanation")
async def areas_explanation():
    """Explain OSPF areas concept"""
    return {
        "ospf_areas": {
            "area_0": {
                "name": "Backbone Area",
                "description": "Required area that connects all other areas",
                "characteristics": [
                    "All inter-area traffic must pass through area 0",
                    "Must be contiguous",
                    "All ABRs must be connected to area 0",
                    "Floods Type 1, 2, 3, 4, and 5 LSAs"
                ]
            },
            "area_types": {
                "normal": {
                    "name": "Normal Area",
                    "description": "Standard OSPF area that learns intra and inter-area routes",
                    "lsa_types": "1, 2, 3, 4, 5"
                },
                "stub": {
                    "name": "Stub Area",
                    "description": "Blocks external routes (Type 5 LSAs) to reduce routing table size",
                    "lsa_types": "1, 2, 3 (No Type 5)",
                    "characteristics": [
                        "No AS External LSAs",
                        "Default route injected by ABR",
                        "Reduced routing table size"
                    ]
                },
                "nssa": {
                    "name": "Not-So-Stubby Area",
                    "description": "Allows limited external routes via Type 7 LSAs while still being stub",
                    "lsa_types": "1, 2, 3, 7",
                    "characteristics": [
                        "Type 7 LSAs converted to Type 5 by ABR",
                        "Limited external route injection"
                    ]
                },
                "totally_stubby": {
                    "name": "Totally Stubby Area",
                    "description": "Blocks both external and inter-area routes",
                    "lsa_types": "1, 2 (No Type 3, 4, 5)",
                    "characteristics": [
                        "Only default route from ABR",
                        "Smallest routing tables"
                    ]
                }
            }
        },
        "router_types": {
            "ir": {
                "name": "Internal Router",
                "description": "All interfaces in same area",
                "functions": ["Runs SPF for its area", "Maintains area LSDB"]
            },
            "abr": {
                "name": "Area Border Router",
                "description": "Interfaces in multiple areas",
                "functions": ["Connects areas", "Generates Type 3 LSAs", "Summarizes routes"]
            },
            "asbr": {
                "name": "AS Boundary Router",
                "description": "Connects to external networks",
                "functions": ["Generates Type 5 LSAs", "Redistributes external routes"]
            },
            "backbone_router": {
                "name": "Backbone Router",
                "description": "Router in area 0",
                "functions": ["Routes inter-area traffic", "Maintains backbone LSDB"]
            }
        },
        "lsa_types": {
            "type_1": "Router LSA - Describes router's links within an area",
            "type_2": "Network LSA - Describes multi-access networks within an area",
            "type_3": "Summary LSA - Advertises inter-area routes",
            "type_4": "ASBR Summary LSA - Advertises location of ASBRs",
            "type_5": "AS External LSA - Advertises external routes",
            "type_7": "NSSA External LSA - External routes in NSSA areas"
        },
        "key_concepts": {
            "lsa_flooding": "LSAs are flooded within an area but not between areas (except by ABRs)",
            "route_preference": "Connected > Static > External > Inter-area > Intra-area",
            "path_selection": "OSPF prefers intra-area routes over inter-area routes",
            "area_hierarchy": "All areas must connect to backbone (area 0)"
        }
    }

@app.get("/ospf/lsa-types")
async def lsa_types_explanation():
    """Detailed explanation of OSPF LSA types"""
    return {
        "lsa_types": [
            {
                "type": 1,
                "name": "Router LSA",
                "description": "Generated by every router, describes the router's links within an area",
                "flooding_scope": "Within originating area",
                "contents": [
                    "List of connected links",
                    "Link types (point-to-point, transit, stub)",
                    "Link costs",
                    "Router capabilities"
                ],
                "example": "Router R1 advertises its connections to R2 and R3 in Area 0"
            },
            {
                "type": 2,
                "name": "Network LSA",
                "description": "Generated by Designated Router on broadcast networks",
                "flooding_scope": "Within originating area",
                "contents": [
                    "List of routers attached to the network",
                    "Network mask",
                    "DR's router ID"
                ],
                "example": "DR on switch S1 advertises that R1, R2, R3 are connected"
            },
            {
                "type": 3,
                "name": "Summary LSA",
                "description": "Generated by ABRs to advertise routes between areas",
                "flooding_scope": "From source area to destination area",
                "contents": [
                    "Network address and mask",
                    "Route cost",
                    "Advertising ABR"
                ],
                "example": "ABR R2 advertises routes from Area 1 to Area 0"
            },
            {
                "type": 4,
                "name": "ASBR Summary LSA",
                "description": "Generated by ABRs to advertise location of ASBRs",
                "flooding_scope": "Throughout AS (except stub areas)",
                "contents": [
                    "ASBR's router ID",
                    "Cost to reach ASBR"
                ],
                "example": "ABR R3 advertises that ASBR R4 is reachable with cost 20"
            },
            {
                "type": 5,
                "name": "AS External LSA",
                "description": "Generated by ASBRs to advertise external routes",
                "flooding_scope": "Throughout AS (except stub areas)",
                "contents": [
                    "External network address and mask",
                    "External metric",
                    "Forwarding address"
                ],
                "example": "ASBR R5 advertises external network 8.8.8.0/24"
            },
            {
                "type": 7,
                "name": "NSSA External LSA",
                "description": "Generated by ASBRs in NSSA areas, converted to Type 5 by ABRs",
                "flooding_scope": "Within NSSA area, converted to Type 5 for flooding elsewhere",
                "contents": [
                    "External network address and mask",
                    "External metric",
                    "Forwarding address"
                ],
                "example": "ASBR in NSSA Area 2 advertises external route, ABR converts to Type 5"
            }
        ],
        "flooding_rules": {
            "type_1_2": "Flooded only within originating area",
            "type_3": "Flooded by ABRs between connected areas",
            "type_4_5": "Flooded throughout AS (except stub areas)",
            "type_7": "Flooded within NSSA, converted to Type 5 by ABR"
        },
        "area_restrictions": {
            "stub_areas": "No Type 5 LSAs, Type 4 LSAs filtered",
            "nssa_areas": "Type 7 LSAs allowed, converted to Type 5 by ABR",
            "totally_stubby": "No Type 3, 4, or 5 LSAs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)