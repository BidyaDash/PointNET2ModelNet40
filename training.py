from ModelNet40.data_loader import ModelNetDataLoader
# import argparse
import numpy as np
import os
import torch
import datetime
import logging
from pathlib import Path
from tqdm import tqdm
import sys
from ModelNet40 import provider
from ModelNet40 import model
import importlib
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR
sys.path.append(os.path.join(ROOT_DIR, 'models'))


# def parse_args():
#     '''PARAMETERS'''
#     parser = argparse.ArgumentParser('PointNet')
#     parser.add_argument('--batch_size', type=int, default=24, help='batch size in training [default: 24]')
#     parser.add_argument('--model', default='pointnet_cls', help='model name [default: pointnet_cls]')
#     parser.add_argument('--epoch',  default=200, type=int, help='number of epoch in training [default: 200]')
#     parser.add_argument('--learning_rate', default=0.001, type=float, help='learning rate in training [default: 0.001]')
#     parser.add_argument('--gpu', type=str, default='0', help='specify gpu device [default: 0]')
#     parser.add_argument('--num_point', type=int, default=1024, help='Point Number [default: 1024]')
#     parser.add_argument('--optimizer', type=str, default='Adam', help='optimizer for training [default: Adam]')
#     parser.add_argument('--log_dir', type=str, default=None, help='experiment root')
#     parser.add_argument('--decay_rate', type=float, default=1e-4, help='decay rate [default: 1e-4]')
#     parser.add_argument('--normal', action='store_true', default=False, help='Whether to use normal information [default: False]')
#     return parser.parse_args()

def test(model, loader, num_class=40):
    mean_correct = []
    class_acc = np.zeros((num_class,3))
    # for j, data in tqdm(enumerate(loader), total=len(loader)):
    for j, data in enumerate(loader):
        points, target = data
        target = target[:, 0]
        points = points.transpose(2, 1)
        points, target = points.cuda(), target.cuda()
        classifier = model.eval()
        pred, _ = classifier(points)
        pred_choice = pred.data.max(1)[1]
        for cat in np.unique(target.cpu()):
            classacc = pred_choice[target==cat].eq(target[target==cat].long().data).cpu().sum()
            class_acc[cat,0]+= classacc.item()/float(points[target==cat].size()[0])
            class_acc[cat,1]+=1
        correct = pred_choice.eq(target.long().data).cpu().sum()
        mean_correct.append(correct.item()/float(points.size()[0]))
    class_acc[:,2] =  class_acc[:,0]/ class_acc[:,1]
    class_acc = np.mean(class_acc[:,2])
    instance_acc = np.mean(mean_correct)
    return instance_acc, class_acc


def main():
    # def log_string(str):
    #     logger.info(str)
    #     print(str)
    #
    # '''HYPER PARAMETER'''
    # os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    #
    # '''CREATE DIR'''
    # timestr = str(datetime.datetime.now().strftime('%Y-%m-%d_%H-%M'))
    # experiment_dir = Path('./log/')
    # experiment_dir.mkdir(exist_ok=True)
    # experiment_dir = experiment_dir.joinpath('classification')
    # experiment_dir.mkdir(exist_ok=True)
    # if args.log_dir is None:
    #     experiment_dir = experiment_dir.joinpath(timestr)
    # else:
    #     experiment_dir = experiment_dir.joinpath(args.log_dir)
    # experiment_dir.mkdir(exist_ok=True)
    # checkpoints_dir = experiment_dir.joinpath('checkpoints/')
    # checkpoints_dir.mkdir(exist_ok=True)
    # log_dir = experiment_dir.joinpath('logs/')
    # log_dir.mkdir(exist_ok=True)
    #
    # '''LOG'''
    # args = parse_args()
    # logger = logging.getLogger("Model")
    # logger.setLevel(logging.INFO)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # file_handler = logging.FileHandler('%s/%s.txt' % (log_dir, args.model))
    # file_handler.setLevel(logging.INFO)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)
    # log_string('PARAMETER ...')
    # log_string(args)


    print('Load dataset ...')
    DATA_PATH = 'D:/AI/Dataset/ModelNet40/modelnet40_normal_resampled'

    TRAIN_DATASET = ModelNetDataLoader(root=DATA_PATH, npoint=1024, split='train',
                                                     normal_channel=True)
    TEST_DATASET = ModelNetDataLoader(root=DATA_PATH, npoint=1024, split='test',
                                                    normal_channel=True)
    trainDataLoader = torch.utils.data.DataLoader(TRAIN_DATASET, batch_size=32, shuffle=True, num_workers=4)
    testDataLoader = torch.utils.data.DataLoader(TEST_DATASET, batch_size=64, shuffle=False, num_workers=4)

    print("Dataset Loaded......")

    print("Loading Model........")
    num_class = 40
    MODEL = model
    classifier = MODEL.get_model(num_class,normal_channel=True).cuda()
    criterion = MODEL.get_loss().cuda()
    print("Model Loaded.........")

    # try:
    #     checkpoint = torch.load(str(experiment_dir) + '/checkpoints/best_model.pth')
    #     start_epoch = checkpoint['epoch']
    #     classifier.load_state_dict(checkpoint['model_state_dict'])
    #     log_string('Use pretrain model')
    # except:
    #     log_string('No existing model, starting training from scratch...')
    #     start_epoch = 0


    # if args.optimizer == 'Adam':
    #     optimizer = torch.optim.Adam(
    #         classifier.parameters(),
    #         lr=args.learning_rate,
    #         betas=(0.9, 0.999),
    #         eps=1e-08,
    #         weight_decay=args.decay_rate
    #     )
    # else:
    #     optimizer = torch.optim.SGD(classifier.parameters(), lr=0.01, momentum=0.9)

    optimizer = torch.optim.Adam(
        classifier.parameters(),
        lr=1e-3,
        betas=(0.9, 0.999),
        eps=1e-08,
        weight_decay=1e-4
    )

    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.7)
    global_epoch = 0
    global_step = 0
    best_instance_acc = 0.0
    best_class_acc = 0.0
    mean_correct = []
    epochs = 300

    print("Training started...")
    for epoch in range(epochs):
        print('Epoch {}/{}:'.format(epoch + 1, epochs))

        scheduler.step()
        # for batch_id, data in tqdm(enumerate(trainDataLoader, 0), total=len(trainDataLoader), smoothing=0.9):
        for batch_id, data in enumerate(trainDataLoader, 0):
            points, target = data
            points = points.data.numpy()
            points = provider.random_point_dropout(points)
            points[:,:, 0:3] = provider.random_scale_point_cloud(points[:,:, 0:3])
            points[:,:, 0:3] = provider.shift_point_cloud(points[:,:, 0:3])
            points = torch.Tensor(points)
            target = target[:, 0]

            points = points.transpose(2, 1)
            points, target = points.cuda(), target.cuda()
            optimizer.zero_grad()

            classifier = classifier.train()
            pred, trans_feat = classifier(points)
            loss = criterion(pred, target.long(), trans_feat)
            pred_choice = pred.data.max(1)[1]
            correct = pred_choice.eq(target.long().data).cpu().sum()
            mean_correct.append(correct.item() / float(points.size()[0]))
            loss.backward()
            optimizer.step()
            global_step += 1

        train_instance_acc = np.mean(mean_correct)
        print('Train Instance Accuracy: {}'.format(train_instance_acc))


        with torch.no_grad():
            instance_acc, class_acc = test(classifier.eval(), testDataLoader)

            if (instance_acc >= best_instance_acc):
                best_instance_acc = instance_acc
                best_epoch = epoch + 1

            if (class_acc >= best_class_acc):
                best_class_acc = class_acc
            print('Test Instance Accuracy: {}, Class Accuracy: {}'.format(instance_acc, class_acc))
            print('Best Instance Accuracy: {}, Class Accuracy: {}'.format(best_instance_acc, best_class_acc))

            if (instance_acc >= best_instance_acc):
                print('Save model...')
                savepath = 'best_model.pth'
                print('Saving as {}'.format(savepath))
                state = {
                    'epoch': best_epoch,
                    'instance_acc': instance_acc,
                    'class_acc': class_acc,
                    'model_state_dict': classifier.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                }
                torch.save(state, savepath)
            global_epoch += 1

    print('End of training...')

if __name__ == '__main__':
    # args = parse_args()
    # main(args)
    main()