from api.main import OSPFSimulator, Device, Link, Topology, OSPFConfig, Interface


def make_device(router_id, area, ip=None, is_router=True, is_asbr=False, stub_area=False, nssa=False):
    if is_router:
        return Device(
            id=router_id,
            type='router',
            label=router_id,
            position={'x': 0, 'y': 0},
            ip=ip or '0.0.0.0',
            interfaces=[],
            ospf=OSPFConfig(enabled=True, area=area, is_asbr=is_asbr, stub_area=stub_area, nssa=nssa),
            mac='00:00:00:00:00:00'
        )
    else:
        return Device(
            id=router_id,
            type='server',
            label=router_id,
            position={'x': 0, 'y': 0},
            ip=ip or '0.0.0.0',
            interfaces=[],
            ospf=None,
            mac='00:00:00:00:00:00'
        )


def test_backbone_installs_summary_routes():
    # Build topology similar to user's scenario
    R1 = make_device('R1', 0, ip='10.0.0.1')
    R2 = make_device('R2', 0, ip='10.0.0.2')
    R3 = make_device('R3', 0, ip='10.0.0.3')
    R4 = make_device('R4', 1, ip='10.1.1.2')

    # Add interface information so connected networks show up as connected routes
    R2.interfaces = [Interface(id='eth2', connectedTo='R4', linkId='L5', type='ospf', ip='10.1.1.1', state='up')]
    R4.interfaces = [Interface(id='eth0', connectedTo='R2', linkId='L5', type='ospf', ip='10.1.1.2', state='up')]

    links = [
        Link(id='L1', source='R1', target='R2', type='ospf', cost=10, area=0),
        Link(id='L2', source='R1', target='R3', type='ospf', cost=20, area=0),
        Link(id='L4', source='R2', target='R3', type='ospf', cost=15, area=0),
        Link(id='L5', source='R2', target='R4', type='ospf', cost=10, area=1),
    ]

    topo = Topology(devices=[R1, R2, R3, R4], links=links, timestamp='t')
    sim = OSPFSimulator()
    result = sim.simulate_ospf(topo, step_by_step=False)

    # Find R3 routing table
    r3_rt = next((rt for rt in result.get('routing_tables', []) if rt['router'] == 'R3'), None)
    assert r3_rt is not None, "R3 routing table not found"

    # Check that R3 has inter-area route to R4's connected network (10.1.1.2/24)
    has_inter_area_net = any(
        r.get('type') == 'inter-area' and r.get('destination') in ('10.1.1.2/24', '10.1.1.1/24')
        for r in r3_rt.get('routes', [])
    )

    assert has_inter_area_net, f"R3 should learn Area 1 networks via ABR but routes were: {r3_rt.get('routes', [])}"
