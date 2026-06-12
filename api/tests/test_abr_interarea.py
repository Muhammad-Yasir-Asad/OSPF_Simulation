from api.main import OSPFSimulator, Device, Link, Topology, OSPFConfig


def make_router(id, area):
    # Try to derive a deterministic IP from numeric router IDs; fall back when needed
    try:
        num = int(id.replace("R", ""))
        ip = f'10.0.0.{num+1}'
    except Exception:
        # Non-numeric IDs (e.g., 'A', 'C') use a simple hash-derived last octet
        ip = f'10.255.0.{(sum(ord(c) for c in id) % 250) + 1}'

    return Device(
        id=id,
        type='router',
        label=id,
        position={'x': 0, 'y': 0},
        ip=ip,
        interfaces=[],
        ospf=OSPFConfig(enabled=True, area=area),
        mac='00:00:00:00:00:00'
    )


def test_abrs_have_inter_area_routes():
    # Build a simple topology with backbone (R0) and two areas connected via ABRs R1 and R2
    R0 = make_router('R0', 0)
    R1 = make_router('R1', 0)  # ABR for area 1
    R2 = make_router('R2', 0)  # ABR for area 2
    A = make_router('A', 1)
    C = make_router('C', 2)

    # Define links (OSPF type) - R1 connects R0 (area0) and A (area1)
    links = [
        Link(id='L0', source='R0', target='R1', type='ospf', cost=10, area=0, label='R0-R1'),
        Link(id='L1', source='R1', target='A', type='ospf', cost=10, area=1, label='R1-A'),
        Link(id='L2', source='R0', target='R2', type='ospf', cost=10, area=0, label='R0-R2'),
        Link(id='L3', source='R2', target='C', type='ospf', cost=10, area=2, label='R2-C'),
    ]

    topology = Topology(devices=[R0, R1, R2, A, C], links=links, timestamp='t')

    sim = OSPFSimulator()
    result = sim.simulate_ospf(topology, step_by_step=False)
    routing_tables = result.get('routing_tables', [])

    # Find R1 routing table
    r1_rt = next((rt for rt in routing_tables if rt['router'] == 'R1'), None)
    assert r1_rt is not None, "R1 routing table not found"

    # Check that R1 has inter-area route to Area 2 (via R2)
    has_inter_area_to_area2 = any(
        r.get('type') == 'inter-area' and r.get('to_area') == 2 for r in r1_rt.get('routes', [])
    )

    assert has_inter_area_to_area2, f"R1 should have inter-area routes to Area 2 but routes were: {r1_rt.get('routes', [])}"
