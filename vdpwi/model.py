from torch.autograd import Variable
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class SerializableModule(nn.Module):
    def __init__(self):
        super().__init__()

    def save(self, filename):
        torch.save(self.state_dict(), filename)

    def load(self, filename):
        self.load_state_dict(torch.load(filename, map_location=lambda storage, loc: storage))

class VDPWIConvNet(SerializableModule):
    def __init__(self, n_labels):
        super().__init__()
        self.conv1 = nn.Conv2d(13, 128, 3, padding=1)
        self.conv2 = nn.Conv2d(128, 164, 3, padding=1)
        self.conv3 = nn.Conv2d(164, 192, 3, padding=1)
        self.conv4 = nn.Conv2d(192, 192, 3, padding=1)
        self.conv5 = nn.Conv2d(192, 128, 3, padding=1)
        self.maxpool2 = nn.MaxPool2d(2, ceil_mode=True)
        self.dnn = nn.Linear(128, 128)
        self.output = nn.Linear(128, n_labels)

    def forward(self, x):
        def pad_side(idx, max_size):
            if max_size <= 32:
                pad_len = 32 - x.size(idx)
            elif max_size <= 48:
                pad_len = 48 - x.size(idx)
            else:
                pad_len = 0
            return [0, pad_len]
        padding = pad_side(3, max(x.size()[2:]))
        padding.extend(pad_side(2, max(x.size()[2:])))
        x = F.pad(x, padding)
        x = x[:, :, :48, :48]

        pool_final = nn.MaxPool2d(2, ceil_mode=True) if x.size(2) == 32 else nn.MaxPool2d(3, 1, ceil_mode=True)
        x = self.maxpool2(F.relu(self.conv1(x)))
        x = self.maxpool2(F.relu(self.conv2(x)))
        x = self.maxpool2(F.relu(self.conv3(x)))
        x = self.maxpool2(F.relu(self.conv4(x)))
        x = pool_final(F.relu(self.conv5(x)))
        x = F.relu(self.dnn(x.view(x.size(0), -1)))
        return self.output(x)

class VDPWIModel(SerializableModule):
    def __init__(self, embedding, config, classifier_net=None):
        super().__init__()
        self.rnn = nn.LSTM(300, config.rnn_hidden_dim, 1, bidirectional=True, batch_first=True)
        self.embedding = embedding
        self.use_cuda = not config.cpu
        self.classifier_net = VDPWIConvNet(config.n_labels) if classifier_net is None else classifier_net

    def compute_sim_cube(self, seq1, seq2):
        def compute_sim(h1, h2):
            h1_len = torch.sqrt(torch.sum(h1**2))
            h2_len = torch.sqrt(torch.sum(h2**2))

            dot_prod = torch.dot(h1, h2)
            cos_dist = dot_prod / (h1_len * h2_len + 1E-8)
            l2_dist = torch.sqrt(torch.sum((h1 - h2)**2))
            return torch.cat([dot_prod, cos_dist, l2_dist])

        sim_cube = Variable(torch.Tensor(13, seq1.size(0), seq2.size(0)))
        if self.use_cuda:
            sim_cube = sim_cube.cuda()
        seq1_f = seq1[:, 0]
        seq1_b = seq1[:, 1]
        seq2_f = seq2[:, 0]
        seq2_b = seq2[:, 1]
        for t, (h1f, h1b) in enumerate(zip(seq1_f, seq1_b)):
            for s, (h2f, h2b) in enumerate(zip(seq2_f, seq2_b)):
                sim_cube[0:3, t, s] = compute_sim(torch.cat([h1f, h1b]), torch.cat([h2f, h2b]))
                sim_cube[3:6, t, s] = compute_sim(h1f, h2f)
                sim_cube[6:9, t, s] = compute_sim(h1b, h2b)
                sim_cube[9:12, t, s] = compute_sim(h1f + h1b, h2f + h2b)
        return sim_cube

    def compute_focus_cube(self, sim_cube):
        mask = Variable(torch.Tensor(*sim_cube.size()))
        if self.use_cuda:
            mask = mask.cuda()
        mask[:, :, :] = 0.1
        def build_mask(index):
            s1tag = np.zeros(sim_cube.size(1))
            s2tag = np.zeros(sim_cube.size(2))
            _, indices = torch.sort(sim_cube[index].view(-1), descending=True)
            for i, index in enumerate(indices.cpu().data.numpy()):
                if i >= len(s1tag) + len(s2tag):
                    break
                pos1, pos2 = index // len(s2tag), index % len(s2tag)
                if s1tag[pos1] + s2tag[pos2] == 0:
                    s1tag[pos1] = s2tag[pos2] = 1
                    mask[:, int(pos1), int(pos2)] = 1
        build_mask(10)
        build_mask(11)
        mask[12, :, :] = 1
        return mask * sim_cube

    def forward(self, x1, x2):
        x1 = self.embedding(x1)
        x2 = self.embedding(x2)
        seq1, _ = self.rnn(x1)
        seq2, _ = self.rnn(x2)
        seq1 = seq1.squeeze(0) # batch size assumed to be 1
        seq2 = seq2.squeeze(0)
        sim_cube = self.compute_sim_cube(seq1, seq2)
        focus_cube = self.compute_focus_cube(sim_cube)
        logits = self.classifier_net(focus_cube.unsqueeze(0))
        return F.log_softmax(logits)
