import numpy as np
import os
from matplotlib import pyplot as plt
from tqdm import tqdm
import png
from PIL import Image


def calculate_IOU(pred, real):
    """
    this test is on a single image, and the number of clusters are the number in groundtruth
    thus, if prediction has three classes but gt has 2, mean will only divide by 2

    Returns:
        float: mIOU score
    """
    score = 0
    # num_cluster = 0
    for i in [0, 1, 2]:
        if i in pred:
            # num_cluster += 1
            intersection = sum(np.logical_and(pred == i, real == i))
            union = sum(np.logical_or(pred == i, real == i))
            score += intersection/union
    num_cluster = len(np.unique(real))
    return score/num_cluster


def get_mIOU(mask, groundtruth, prediction):
    """
    in this mIOU calculation, the mask will be excluded
    """
    prediction = np.reshape(prediction, (-1))
    groundtruth = groundtruth.reshape(-1)
    mask = mask.reshape(-1)
    length = len(prediction)

    after_mask_pred = []
    after_mask_true = []
    for i in range(length):
        if mask[i] == 0:
            after_mask_true.append(groundtruth[i])
            after_mask_pred.append(prediction[i])

    after_mask_pred = np.array(after_mask_pred)
    after_mask_true = np.array(after_mask_true)
    score = calculate_IOU(after_mask_pred, after_mask_true)
    return score


# model_names = ['secondphase_ep10', 'model_last', '9632_ep10', '01_best']
# model_names = ['ensemble'] #'secondphase_scalenet101_448_2_last'

def visualize_result(model_names):
    """
    get the 0,1,2,3 predictions from directory out_cam/{model_name} and compare with groundtruth
    will generate some temporary files

    Args:
        model_names (list): list of results you want to test on validation set
    """
    img_path = 'Dataset/2.validation/img'
    gt_path = 'Dataset/2.validation/mask'
    mask_path = 'Dataset/2.validation/background-mask'

    if not os.path.exists(f'temp'):
        os.mkdir(f'temp')

    visualize_pick = np.arange(40) # define the id of images that require visualization
    
    for model_name in model_names:
        for i in tqdm(visualize_pick):
            
            mask = np.asarray(Image.open(mask_path + f'/{i:02d}.png'))
            
            cam_path = f'out_cam/{model_name}'
            cam = np.load(os.path.join(cam_path, f'{i:02d}.npy'), allow_pickle=True).astype(np.uint8)
            
            groundtruth = np.asarray(Image.open(gt_path + f'/{i:02d}.png'))
            
            score = get_mIOU(mask, groundtruth, cam)

            palette = [(0, 64, 128), (64, 128, 0), (243, 152, 0), (255, 255, 255)]
            with open(f'temp/{i:02d}.png', 'wb') as f:
                w = png.Writer(cam.shape[1], cam.shape[0], palette=palette, bitdepth=8)
                w.write(f, cam)

            cam[mask == 1] = 3
            with open(f'temp/{i:02d}_1.png', 'wb') as f:
                w = png.Writer(cam.shape[1], cam.shape[0],palette=palette, bitdepth=8)
                w.write(f, cam)

            plt.figure(i)
            im = plt.imread(f'{i:02d}.png')
            im_mask = plt.imread(f'{i:02d}_1.png')
            gt = plt.imread(gt_path + f'/{i:02d}.png')
            origin = plt.imread(img_path + f'/{i:02d}.png')

            plt.figure(i, figsize=(40, 40))
            plt.subplot(2, 2, 1)
            plt.imshow(im)
            plt.title(f'cam, mIOU = {score:.2f}')
            plt.subplot(2, 2, 2)
            plt.imshow(gt)
            plt.title('groundtruth')
            plt.subplot(2, 2, 3)
            plt.imshow(origin)
            plt.title('origin image')
            plt.subplot(2, 2, 4)
            plt.imshow(im_mask)
            plt.title('cam with background mask')

            if not os.path.exists(f'{model_name}_heatmap'):
                os.mkdir(f'{model_name}_heatmap')

            plt.savefig(f'{model_name}_heatmap/{i:02d}.png')
            plt.close()