# -*- coding: utf-8 -*-

import datetime

import torch
import torch.nn as nn
import torch.optim as optim


class Trainer(object):
    def __init__(self, network, config):
        self.network = network
        self.config = config
        # choose optimizer
        if config.optimizer == 'sgd':
            print('Using SGD optimizer...')
            self.optimizer = optim.SGD(network.parameters(), lr=config.lr)
        elif config.optimizer == 'adam':
            print('Using Adam optimizer...')
            self.optimizer = optim.Adam(network.parameters(), lr=config.lr)

    def lr_decay(self, optimizer, epoch, decay_rate, init_lr):
        lr = init_lr/(1+decay_rate*epoch)
        print("Learning rate is set as:", lr)
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr

    def train(self, data_loaders, evaluator):
        # record some parameters
        max_precision = 0
        test_precision = 0
        max_epoch = 0
        patience = 0

        max_precision2 = 0
        test_precision2 = 0
        max_epoch2 = 0
        patience2 = 0

        train_loader, dev_loader, test_loader = data_loaders

        # begin to train
        print('start to train the model ')
        for epoch in range(1, self.config.epochs + 1):
            print(f"Epoch {epoch} / {self.config.epochs}:")
            self.network.train()
            time_start = datetime.datetime.now()

            if self.config.optimizer == 'sgd':
                self.lr_decay(self.optimizer, epoch,
                              self.config.decay, self.config.lr)

            for batch in train_loader:
                self.optimizer.zero_grad()
                # mask = torch.arange(label_idxs.size(1)) < lens.unsqueeze(-1)
                # mask = word_idxs.gt(0)
                mask, out, targets = self.network.forward_batch(batch)
                loss = self.network.get_loss(out, targets)

                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), 5.0)
                self.optimizer.step()

            train_loss, train_p, train_r, train_f = evaluator.evaluate(
                self.network, train_loader)
            print('train: loss = %.4f precision = %.4f recall = %.4f fmeasure = %.4f' % (
                train_loss, train_p, train_r, train_f))

            dev_loss, dev_p, dev_r, dev_f = evaluator.evaluate(
                self.network, dev_loader)
            print('dev:   loss = %.4f precision = %.4f recall = %.4f fmeasure = %.4f' % (
                dev_loss, dev_p, dev_r, dev_f))

            test_loss, test_p, test_r, test_f = evaluator.evaluate(
                self.network, test_loader)
            print('test:  loss = %.4f precision = %.4f recall = %.4f fmeasure = %.4f' % (
                test_loss, test_p, test_r, test_f))

            # save the model when dev precision get better
            if dev_f > max_precision:
                max_precision = dev_f
                test_precision = test_f
                max_epoch = epoch
                patience = 0
                print('save the model...')
                torch.save(self.network, self.config.net_file)
            else:
                patience += 1

            time_end = datetime.datetime.now()
            print('iter executing time is ' +
                  str(time_end - time_start) + '\n')
            if patience >= self.config.patience:
                break

        print('train finished with epoch: %d / %d' %
              (epoch, self.config.epochs))
        print('best epoch is epoch = %d ,the dev precision = %.4f the test precision = %.4f' %
              (max_epoch, max_precision, test_precision))
        print(str(datetime.datetime.now()))
