import numpy as np
import os
from matplotlib import pyplot as plt
from tqdm import tqdm
import png
from PIL import Image

model_names = ['secondphase_scalenet101_last', 'secondphase_scalenet152_last']
out_path = "train_ensemble_result"
if not os.path.exists(out_path):
    os.mkdir(out_path)
train_path = "Dataset/1.training"
# val_path = "Dataset/2.validation/img"
for file in tqdm(os.listdir(train_path)):
    fileindex = file[:-4]
    cam_total = None
    for model_name in model_names:
        cam_path = f'ensemble_candidates/{model_name}_cam_nonorm'
        # cam_path = f'out_cam/{model_name}_cam_nonorm'
        cam_score = np.load(os.path.join(cam_path, f'{fileindex}.npy'), allow_pickle=True).astype(np.float32)
        if cam_total is None:
            cam_total = cam_score
        else:
            assert cam_total.size == cam_score.size
            cam_total += cam_score

    result_label = np.argmax(cam_total, axis=0).astype(np.uint8)
    np.save(f'{out_path}/{fileindex}.npy', result_label)
