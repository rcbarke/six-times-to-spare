import sionna, scipy, matplotlib
from sionna.phy.mapping import Constellation

print("Sionna:", sionna.__version__)
print("SciPy:", scipy.__version__)
print("Matplotlib:", matplotlib.__version__)

import tensorflow as tf
print("TF:", tf.__version__, "GPUs:", tf.config.list_physical_devices("GPU"))

c = Constellation("qam", 4)  # 16-QAM: 4 bits/symbol
print("Constellation points (first 4):", c.points.numpy()[:4])
