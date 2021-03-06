import torch.nn as nn
import torch.backends.cudnn as cudnn

from opts import args
from models.SSF_Resnet import ssf_resnet34,ssf_resnet50,ssf_resnet101,ssf_resnet152
from models.resnet import resnet34,resnet50,resnet101,resnet152
from models.SSF_VGG import ssf_vgg19,ssf_vgg16,ssf_vgg13
from models.preact_resnet import PreActResNet34,PreActResNet50,PreActResNet101,PreActResNet152
from datasets import get_train_loader
from datasets import get_test_loader
from log import Logger
from train import Trainer

import os
import torch


def get_catalogue():
    model_creators = dict()
    model_creators['ssf_resnet101'] = ssf_resnet101
    model_creators['ssf_resnet152'] = ssf_resnet152
    model_creators['ssf_resnet50'] = ssf_resnet50
    model_creators['ssf_resnet34'] = ssf_resnet34
    model_creators['resnet101'] = resnet101
    model_creators['resnet152'] = resnet152
    model_creators['resnet50'] = resnet50
    model_creators['resnet34'] = resnet34
    model_creators['PreActResNet34'] = PreActResNet34
    model_creators['PreActResNet50'] = PreActResNet50
    model_creators['ssf_vgg19'] = ssf_vgg19
    model_creators['ssf_vgg16'] = ssf_vgg16
    model_creators['ssf_vgg13'] = ssf_vgg13
    return model_creators


def create_model(args):
    state = None

    model_creators = get_catalogue()

    assert args.model in model_creators

    model = model_creators[args.model](args)

    if args.resume:
        save_path = os.path.join(args.save_path, args.model)

        if args.small_set:
            save_path += '-Small'
        else:
            save_path += '-Baseline'

        print("=> Loading checkpoint from " + save_path)
        assert os.path.exists(save_path), "[!] Checkpoint " + save_path + " doesn't exist"

        latest = torch.load(os.path.join(save_path, 'latest.pth'))
        latest = latest['latest']

        if args.ckpt > 0:
            latest = args.ckpt

        checkpoint = os.path.join(save_path, 'model_%d.pth' % latest)
        checkpoint = torch.load(checkpoint)

        model.load_state_dict(checkpoint['model'])
        state = checkpoint['state']

    # torch.set_num_threads(args.nGPU)

    if args.nGPU > 0:
        cudnn.benchmark = True
        if args.nGPU > 1:
            model = nn.DataParallel(model, device_ids=[i for i in range(args.nGPU)]).cuda()
        else:
            model = model.cuda()
    criterion = nn.__dict__[args.criterion + 'Loss']()

    if args.nGPU > 0:
        criterion = criterion.cuda()

    open('model.txt', 'w').write(str(model))

    return model, criterion, state


def main():
    # Create Model, Criterion and State
    model, criterion, state = create_model(args)
    print("=> Model and criterion are ready")

    # Create Dataloader
    if not args.test_only:
        train_loader = get_train_loader(args)
    val_loader = get_test_loader(args)
    print("=> Dataloaders are ready")

    # Create Logger
    logger = Logger(args, state)
    print("=> Logger is ready")  # Create Trainer
    trainer = Trainer(args, model, criterion, logger)
    print("=> Trainer is ready")

    if args.test_only:
        test_summary = trainer.test(0, val_loader)
        print("- Test:  Acc %6.3f " % (
            test_summary['acc']))
    else:
        start_epoch = logger.state['epoch'] + 1
        print("=> Start training")
        # test_summary = trainer.test(0, val_loader)

        for epoch in range(start_epoch, args.n_epochs + 1):
            train_summary = trainer.train(epoch, train_loader)
            test_summary = trainer.test(epoch, val_loader)

            logger.record(epoch, train_summary, test_summary, model)

        logger.final_print()


if __name__ == '__main__':
    main()
