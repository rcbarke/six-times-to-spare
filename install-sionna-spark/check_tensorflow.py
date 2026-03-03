import tensorflow as tf
print("TF version:", tf.__version__)
print("CUDA build:", tf.sysconfig.get_build_info().get("is_cuda_build"))
print("GPUs:", tf.config.list_physical_devices("GPU"))
