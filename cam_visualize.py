import numpy as np
import cv2
import os
from matplotlib import pyplot as plt
from tqdm import tqdm
import png
from PIL import Image

img_path = 'Dataset/2.validation/img'
# img_path = 'Dataset/3.testing/img'
image_names = os.listdir(img_path)
cam_path = 'valid_out_cam/img'
npy_names = os.listdir(cam_path)
mask_path = 'Dataset/2.validation/background-mask'

if not os.path.exists("./heatmap1"):
    os.mkdir("./heatmap1")



for i in range(30):
    mask = np.asarray(Image.open(mask_path+f'/{i:02d}.png'))
    cam = np.load(os.path.join(cam_path, npy_names[i]), allow_pickle=True).astype(np.uint8)
    palette=[(0, 64, 128), (64, 128, 0), (243, 152, 0), (255,255,255)]
    with open(f'{i:02d}.png', 'wb') as f:
        w = png.Writer(cam.shape[1], cam.shape[0], palette=palette, bitdepth=8)
        w.write(f, cam)
    
    cam[mask==1] = 3
    with open(f'{i:02d}_1.png', 'wb') as f:
        w = png.Writer(cam.shape[1], cam.shape[0], palette=palette, bitdepth=8)
        w.write(f, cam)
    
    plt.figure(i)
    im = plt.imread(f'{i:02d}.png')
    im_mask = plt.imread(f'{i:02d}_1.png')
    gt = plt.imread(f'Dataset/2.validation/mask/{i:02d}.png')
    origin = plt.imread(f'Dataset/2.validation/img/{i:02d}.png')
    
    plt.figure(i, figsize=(40,40))
    plt.subplot(2,2,1)
    plt.imshow(im)
    plt.title('cam')
    plt.subplot(2,2,2)
    plt.imshow(gt)
    plt.title('groundtruth')
    plt.subplot(2,2,3)
    plt.imshow(origin)
    plt.title('origin image')
    plt.subplot(2,2,4)
    plt.imshow(im_mask)
    plt.title('cam with background mask')

    plt.savefig(f'heatmap1/{i:02d}.png')
    # plt.show()
    plt.close()

# heatmap = ((cam/3)*255).astype(np.uint8)
# heatmap_img = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
# img = cv2.addWeighted(heatmap_img, 0.7, im, 0.3, 0)
# cv2.imshow('result',heatmap_img)
# cv2.waitKey(0)
# for i in tqdm(range(len(image_names))):
#     cam = np.load(os.path.join(cam_path, npy_names[i]), allow_pickle=True)
#     im = cv2.imread(os.path.join(img_path, image_names[i]))
#     mask = cv2.imread(os.path.join(mask_path, image_names[i]))

#     heatmap = (cam[0] * 255).astype(np.uint8)
#     heatmap = np.expand_dims(heatmap,axis=2)
#     heatmap_img = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
#     tumor = cv2.addWeighted(heatmap_img, 0.7, im, 0.3, 0)

#     heatmap = (cam[1] * 255).astype(np.uint8)
#     heatmap = np.expand_dims(heatmap,axis=2)
#     heatmap_img = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
#     stroma = cv2.addWeighted(heatmap_img, 0.7, im, 0.3, 0)

#     heatmap = (cam[2] * 255).astype(np.uint8)
#     heatmap = np.expand_dims(heatmap,axis=2)
#     heatmap_img = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
#     normal = cv2.addWeighted(heatmap_img, 0.7, im, 0.3, 0)

#     plt.figure(i)
#     plt.subplot(2,2,1)
#     plt.imshow(cv2.cvtColor(tumor, cv2.COLOR_BGR2RGB))
#     plt.title('tumor')
#     plt.subplot(2,2,2)
#     plt.imshow(cv2.cvtColor(stroma, cv2.COLOR_BGR2RGB))
#     plt.title('stroma')
#     plt.subplot(2,2,3)
#     plt.imshow(cv2.cvtColor(normal, cv2.COLOR_BGR2RGB))
#     plt.title('normal')
#     plt.subplot(2,2,4)
#     plt.imshow(cv2.cvtColor(mask, cv2.COLOR_BGR2RGB))
#     plt.title('original image')
#     plt.savefig(f'heatmap1/{i:02d}.png')
#     plt.show()
#     plt.close()
#     break