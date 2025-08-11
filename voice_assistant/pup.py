import torch
print(torch.version.cuda)        # должно быть '12.1'
print(torch.cuda.is_available()) # должно быть True
print(torch.cuda.get_device_name(0))  # должно показать 'NVIDIA GeForce RTX 4060'
