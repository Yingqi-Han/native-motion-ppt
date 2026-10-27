import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_motion.acoustics import displacement,pressure_proxy,wavelength,parcels


class AcousticsTests(unittest.TestCase):
    def test_wavelength_and_frequency_relation(self):
        self.assertAlmostEqual(wavelength(343,440),.7795454545454545)
        self.assertAlmostEqual(wavelength(343,220),2*wavelength(343,440))
        for f in [0,-1,math.inf]:
            with self.assertRaises(ValueError):wavelength(343,f)

    def test_parcel_returns_after_a_period_while_pattern_advances(self):
        for x in [340,470,650,1310]:
            self.assertAlmostEqual(displacement(x,.47),displacement(x,3.47))
            self.assertAlmostEqual(displacement(x,.47),displacement(x+80,.97))

    def test_compression_is_negative_displacement_gradient(self):
        for x in [380,560,950]:
            gradient=(displacement(x+.001,.8)-displacement(x-.001,.8))/.002
            self.assertAlmostEqual(-gradient/(24*2*math.pi/480),pressure_proxy(x,.8),places=6)

    def test_neighbours_do_not_cross_in_the_illustration(self):
        model=dict(amplitude_px=24,wavelength_px=480,period_seconds=3,
                   parcel_spacing_px=54,columns=25,rows=6,origin_x=340,origin_y=410,
                   row_spacing_px=60,tagged_column=10,tagged_row=2)
        for i in range(120):
            pts=[p for p in parcels(i/40,model) if p['row']==0]
            self.assertTrue(all(a['x']<b['x'] for a,b in zip(pts,pts[1:])))
        model['amplitude_px']=100
        with self.assertRaises(ValueError):parcels(0,model)
