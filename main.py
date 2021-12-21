# this file uses images without crop to train the model
# purpose: is crop really useful?
import json
import time
import argparse
import torch
from tqdm import tqdm
import matplotlib.pyplot as plt
import os
from torchvision import transforms
import network
import dataset
from torch.utils.data import DataLoader
from utils.metric import get_overall_valid_score
from utils.generate_CAM import generate_cam
from utils.util import get_average_image_size, report


class PolyOptimizer(torch.optim.SGD):
    def __init__(self, params, lr, weight_decay, max_step, momentum=0.9):
        super().__init__(params, lr, weight_decay)

        self.global_step = 0
        self.max_step = max_step
        self.momentum = momentum

        self.__initial_lr = [group['lr'] for group in self.param_groups]


    def step(self, closure=None):

        if self.global_step < self.max_step:
            lr_mult = (1 - self.global_step / self.max_step) ** self.momentum

            for i in range(len(self.param_groups)):
                self.param_groups[i]['lr'] = self.__initial_lr[i] * lr_mult

        super().step(closure)

        self.global_step += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-batch", default=20, type=int)
    parser.add_argument("-epoch", default=20, type=int)
    parser.add_argument("-lr", default=0.01, type=float)
    parser.add_argument("-resize", default=224, type=int)
    parser.add_argument("-save_every", default=10, type=int, help="how often to save a model while training")
    parser.add_argument('-d','--device', nargs='+', help='GPU id to use parallel', required=True, type=int)
    parser.add_argument('-m', type=str, help='the save model name', required=True)
    parser.add_argument('-resnet', action='store_true', default=False)
    parser.add_argument('-note', type=str, help='special experiments with this training', required=False)
    args = parser.parse_args()

    batch_size = args.batch
    epochs = args.epoch
    base_lr = args.lr
    resize = args.resize
    save_every = args.save_every
    devices = args.device
    model_name = args.m
    useresnet = args.resnet
    remark = args.note

    if not os.path.exists('modelstates'):
        os.mkdir('modelstates')
    if not os.path.exists('valid_out_cam'):
        os.mkdir('valid_out_cam')
    average_image_size = get_average_image_size('Dataset/1.training')

    # load model
    prefix = ""
    if useresnet:
        prefix = "resnet"
        resnet38_path = "weights/res38d.pth"
        reporter = report(batch_size, epochs, base_lr, resize, model_name, back_bone=prefix, remark=remark)
        net = network.wideResNet()
        net.load_state_dict(torch.load(resnet38_path), strict=False)
    else:
        prefix = "scalenet"
        net = network.scalenet101(structure_path='network/structures/scalenet101.json', ckpt='weights/scalenet101.pth')
        reporter = report(batch_size, epochs, base_lr, resize, model_name, back_bone=prefix, remark=remark)
    net = torch.nn.DataParallel(net, device_ids=devices).cuda()
    
    # data augmentation
    scale = (0.25,1)
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(size=resize, scale=scale),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    reporter['data_augmentation'] = {'random_resized_crop': f"scale={scale}"}

    # load training dataset
    TrainDataset = dataset.OriginPatchesDataset(transform=train_transform)
    print("train Dataset", len(TrainDataset))
    TrainDatasampler = torch.utils.data.RandomSampler(TrainDataset)
    TrainDataloader = DataLoader(TrainDataset, batch_size=batch_size, num_workers=2, sampler=TrainDatasampler, drop_last=True)

    # optimizer and loss
    optimizer = PolyOptimizer(net.parameters(), base_lr, weight_decay=1e-4, max_step=epochs, momentum=0.9)
    criteria = torch.nn.BCEWithLogitsLoss(reduction='mean')
    criteria.cuda()

    # train loop
    loss_t = []
    accuracy_t = []
    iou_v = []
    best_val = 0
    
    for i in range(epochs):
        count = 0
        running_loss = 0.
        correct = 0
        net.train()

        for img, label in tqdm(TrainDataloader):
            count += 1
            img = img.cuda()
            label = label.cuda()
            scores = net(img)
            loss = criteria(scores, label.float())
            
            scores = torch.sigmoid(scores)
            predict = torch.zeros_like(scores)
            predict[scores > 0.5] = 1
            predict[scores < 0.5] = 0
            for k in range(len(predict)):
                if torch.equal(predict[k], label[k]):
                    correct += 1
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        
        train_loss = running_loss / count
        train_acc = correct / (count * batch_size)
        accuracy_t.append(train_loss)
        loss_t.append(train_acc)

        if useresnet:
            net_cam = network.wideResNet_cam()
        else:
            net_cam = network.scalenet101_cam(structure_path='network/structures/scalenet101.json')

        pretrained = net.state_dict()
        pretrained = {k[7:]: v for k, v in pretrained.items()}
        pretrained['fc1.weight'] = pretrained['fc1.weight'].unsqueeze(-1).unsqueeze(-1).to(torch.float64)
        # pretrained['fc2.weight'] = pretrained['fc2.weight'].unsqueeze(-1).unsqueeze(-1).to(torch.float64)
        net_cam.load_state_dict(pretrained)
        
        # calculate MIOU
        generate_cam(net_cam, prefix + model_name, (average_image_size, average_image_size//3), batch_size, 'valid', resize)
        start_time = time.time()
        valid_image_path = f'valid_out_cam/{prefix + model_name}'
        valid_iou = get_overall_valid_score(valid_image_path, num_workers=8)
        iou_v.append(valid_iou)
        print("--- %s seconds ---" % (time.time() - start_time))
        
        if valid_iou > best_val:
            print("Updating the best model..........................................")
            best_val = valid_iou
            torch.save({"model": net.state_dict(), 'optimizer': optimizer.state_dict()}, "./modelstates/" + prefix + model_name + "_best.pth")
    
        print(f'Epoch [{i+1}/{epochs}], Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, Valid mIOU: {valid_iou:.4f}')

        if (i + 1) % save_every == 0 and (i + 1) != epochs:
            torch.save({"model": net.state_dict(), 'optimizer': optimizer.state_dict()}, "./modelstates/" + prefix + model_name + "_ep"+str(i+1)+".pth")

    torch.save({"model": net.state_dict(), 'optimizer': optimizer.state_dict()}, "./modelstates/" + prefix + model_name + "_last.pth")

    plt.figure(1)
    plt.plot(loss_t)
    plt.ylabel('loss')
    plt.xlabel('epochs')
    plt.title('train loss')
    plt.savefig('./image/train_loss.png')
    plt.close()

    plt.figure(2)
    plt.plot(accuracy_t)
    plt.ylabel('accuracy')
    plt.xlabel('epochs')
    plt.title('train accuracy')
    plt.savefig('./image/train_accuracy.png')

    plt.figure(3)
    plt.plot(iou_v)
    plt.ylabel('accuracy')
    plt.xlabel('epochs')
    plt.title('valid accuracy')
    plt.savefig('./image/valid_iou.png')

    reporter['training_accuracy'] = accuracy_t
    reporter['best_validation_mIOU'] = best_val

    with open('result/experiment.json', 'a') as fp:
        json.dump(reporter, fp)