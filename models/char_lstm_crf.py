# -*- coding: utf-8 -*-

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import *

from module import *


class CHAR_LSTM_CRF(nn.Module):

    def __init__(self, n_char, char_dim, char_hidden, n_bichar, word_dim,
                 n_layers, word_hidden, n_target, drop=0.5):
        super(CHAR_LSTM_CRF, self).__init__()

        self.embedding_dim = char_dim
        self.drop1 = nn.Dropout(drop)
        self.embedding_char = nn.Embedding(n_char, char_dim)
        self.embedding_bichar = nn.Embedding(n_bichar, char_dim)

        # self.char_lstm = CHAR_LSTM(n_char, char_dim, char_hidden)

        if n_layers > 1:
            self.lstm_layer = nn.LSTM(
                input_size=self.embedding_dim * 2,
                hidden_size=word_hidden//2,
                batch_first=True,
                bidirectional=True,
                num_layers=n_layers,
                dropout=0.2  # ?? zhenghua
            )
        else:
            self.lstm_layer = nn.LSTM(
                input_size=self.embedding_dim+char_hidden,
                hidden_size=word_hidden//2,
                batch_first=True,
                bidirectional=True,
                num_layers=1,
            )
        # self.hidden = nn.Linear(word_hidden, word_hidden//2, bias=True)
        self.out = nn.Linear(word_hidden, n_target, bias=True)
        #self.crf = CRFlayer(n_target)
        self.loss_func = nn.CrossEntropyLoss(
            size_average=False, ignore_index=-1)
        self.reset_parameters()

    def load_pretrained_embedding(self, pre_embeddings):
        assert (pre_embeddings.size()[1] == self.embedding_dim)
        self.embedding_char.weight = nn.Parameter(pre_embeddings)

    def reset_parameters(self):
        nn.init.xavier_uniform_(self.out.weight)
        # nn.init.xavier_uniform_(self.hidden.weight)
        # bias = (3.0 / self.embedding.weight.size(1)) ** 0.5
        # nn.init.uniform_(self.embedding.weight, -bias, bias)
        nn.init.normal_(self.embedding_char.weight, 0,
                        1 / self.embedding_dim ** 0.5)
        nn.init.normal_(self.embedding_bichar.weight, 0,
                        1 / self.embedding_dim ** 0.5)

    def forward(self, char_idxs, bichar_idxs):
        # mask = torch.arange(x.size()[1]) < lens.unsqueeze(-1)
        mask = char_idxs.gt(0)
        sen_lens = mask.sum(1)

        # char_vec = self.char_lstm.forward(char_idxs[mask])
        # char_vec = pad_sequence(torch.split(char_vec, sen_lens.tolist()), True, padding_value=0)

        char_vec = self.embedding_char(char_idxs)
        bichar_vec = self.embedding_bichar(bichar_idxs)
        feature = self.drop1(torch.cat((char_vec, bichar_vec), -1))

        sorted_lens, sorted_idx = torch.sort(sen_lens, dim=0, descending=True)
        reverse_idx = torch.sort(sorted_idx, dim=0)[1]
        feature = feature[sorted_idx]
        feature = pack_padded_sequence(feature, sorted_lens, batch_first=True)

        r_out, state = self.lstm_layer(feature, None)
        out, _ = pad_packed_sequence(r_out, batch_first=True, padding_value=0)
        out = out[reverse_idx]
        # out = torch.tanh(self.hidden(out))
        out = self.out(out)
        return out

    def forward_batch(self, batch):
        word_idxs, char_idxs, label_idxs = batch
        mask = word_idxs.gt(0)
        out = self.forward(word_idxs, char_idxs)
        return mask, out, label_idxs

    def get_loss(self, emit, labels):
        length, batch_size, _ = emit.size()
        loss = self.loss_func(
            emit.view(length*batch_size, -1), labels.contiguous().view(-1))
        return loss
        #emit = emit.transpose(0, 1)
        #labels = labels.t()
        #mask = mask.t()
        #logZ = self.crf.get_logZ(emit, mask)
        #scores = self.crf.score(emit, labels, mask)
        # return (logZ - scores) / emit.size()[1]