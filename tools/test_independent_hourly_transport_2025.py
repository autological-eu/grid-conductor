import unittest
import numpy as np
from independent_hourly_transport_2025 import economic_nodes,raw_from_nodes,project


class HourlyTransportTests(unittest.TestCase):
    def test_raw_roundtrip_and_economic_function_average(self):
        rng=np.random.default_rng(194);theta=rng.normal(size=(4,2,6));nodes=economic_nodes(theta)
        np.testing.assert_allclose(economic_nodes(raw_from_nodes(nodes)),nodes,atol=1e-12,rtol=0)
        slots=np.zeros((4,2),dtype=int);availability=np.ones((4,2))
        profile,support=project(theta,availability,slots,theta[0])
        np.testing.assert_allclose(economic_nodes(profile[0]),nodes.mean(axis=0),atol=1e-12,rtol=0)
        self.assertTrue((support[0]==4).all())
        self.assertGreater(abs(economic_nodes(theta.mean(axis=0))-nodes.mean(axis=0)).max(),.01)

    def test_unavailable_isolation_and_fallbacks(self):
        theta=np.zeros((3,2,6));theta[:,0,0]=[0,1,2]
        slots=np.array([[0,0],[0,0],[1,1]])
        availability=np.array([[1,0],[0,0],[1,0]])
        profile,support=project(theta,availability,slots,theta[0])
        changed=theta.copy();changed[1,0]=100
        other,_=project(changed,availability,slots,theta[0])
        np.testing.assert_allclose(profile,other,atol=0,rtol=0)
        nodes=economic_nodes(profile)
        np.testing.assert_allclose(nodes[0,0],economic_nodes(theta[0,0]),atol=1e-12)
        np.testing.assert_allclose(nodes[2,0],economic_nodes(theta[[0,2],0]).mean(axis=0),atol=1e-12)
        np.testing.assert_allclose(nodes[:,1],np.broadcast_to(economic_nodes(theta[0,1]),(168,6)),atol=1e-12)
        self.assertEqual(support[:,1].sum(),0)


if __name__=='__main__':unittest.main()
