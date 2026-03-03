import tensorflow as tf
from tensorflow.python.client import device_lib

print("Build:", tf.sysconfig.get_build_info())
print("Local devices:")
for d in device_lib.list_local_devices():
    print("  ", d.name, d.device_type)