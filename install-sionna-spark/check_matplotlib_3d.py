import matplotlib, sys
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np

print("Matplotlib version:", matplotlib.__version__)
print("Loaded from:", matplotlib.__file__)

import mpl_toolkits
print("mpl_toolkits from:", mpl_toolkits.__file__)

from mpl_toolkits.mplot3d import Axes3D  # just to force the import
print("Axes3D import OK")

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

t = np.linspace(0, 4*np.pi, 200)
x = np.cos(t)
y = np.sin(t)
z = t

ax.plot(x, y, z)
ax.set_title("3D test plot")
plt.show()
