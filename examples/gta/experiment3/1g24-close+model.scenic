from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../map.npz')

from scenic.simulators.gta.model import *

param time = 12 * 60
param weather = 'EXTRASUNNY'

ego = EgoCar

c = Car offset by (-5, 5) @ (7, 12),
	with color CarColor.withBytes([187, 162, 157])