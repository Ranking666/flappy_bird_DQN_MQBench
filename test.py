import pdb
import cv2
import sys
import os

os.chdir(sys.path[0])
import numpy

sys.path.append("./game/")
import game.wrapped_flappy_bird as game
import random
import numpy as np
from collections import deque  # 数据结构常用的模块
import torch
from torch.autograd import Variable
import torch.nn as nn


GAME = 'bird' 
ACTIONS = 2  

from mqbench.convert_deploy import convert_deploy
from mqbench.prepare_by_platform import prepare_qat_fx_by_platform, BackendType
from mqbench.utils.state import enable_calibration, enable_quantization


class DeepNetWork(nn.Module):
    def __init__(self, ):
        super(DeepNetWork, self).__init__()
        self.fc1 = nn.Sequential(
            nn.Linear(28, 64),  
            nn.ReLU()
        )
        self.fc2 = nn.Sequential(
             nn.Linear(64, 128, bias=False),
             nn.ReLU()
         )
        self.fc3 = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU()
        )
        self.fc4 = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU()
        )
        self.fc5 = nn.Sequential(
            nn.Linear(256, 256),
            nn.ReLU()
        )
        self.fc6 = nn.Sequential(
            nn.Linear(256, 256),
            nn.ReLU()
        )

        self.out = nn.Linear(256, 2)

    def forward(self, x):
        x = self.fc1(x)
        x = self.fc2(x)
        x = self.fc3(x)
        x = self.fc4(x)
        x = self.fc5(x)
        x = self.fc6(x)
        return self.out(x)


class BrainDQNMainTest(object):
    def load(self):
        if os.path.exists("params3.pth"):
            print("====================load model =======================")
            ckpt = torch.load('params3.pth')
            for k, v in ckpt.items():
              print(k, v)
            self.Q_net.load_state_dict(torch.load('params3.pth'))


    def __init__(self, actions=2):
        self.actions = actions
        self.Q_net = DeepNetWork()
        self.Q_net.train()
        self.Q_net = prepare_qat_fx_by_platform(self.Q_net, BackendType.Tensorrt)
        self.Q_net.eval()
        enable_calibration(self.Q_net)
        self.calibration_flag = True
        self.load()

    def setPerception(self, nextObservation): 
        newState = nextObservation

        self.currentState = newState
    def quantize_set(self):
        self.Q_net.train()
        self.Q_net = prepare_qat_fx_by_platform(self.Q_net, BackendType.Tensorrt)
        self.Q_net.eval()
        enable_calibration(self.Q_net)
        self.calibration_flag = True

    def getAction(self):
        currentState = torch.Tensor(numpy.array([self.currentState]))
        QValue = self.Q_net(currentState)[0]
        action = np.zeros(self.actions)

        action_index = np.argmax(QValue.detach().numpy())
        action[action_index] = 1

        return action

    def setInitState(self, observation): 
        self.currentState = observation


if __name__ == '__main__':

    total_scores = 0
    episode = 1

    actions = 2
    brain = BrainDQNMainTest(actions)
    flappyBird = game.GameState()
    action0 = np.array([1, 0])
    observation0, reward0, terminal = flappyBird.frame_step(action0)
    if reward0 == 1:
        total_scores += 1
    brain.setInitState(observation0)
    while 1 != 0:
        action = brain.getAction()
        nextObservation, reward, terminal = flappyBird.frame_step(action)
        brain.setPerception(nextObservation)
        if reward == 1:
            total_scores += 1
            #print("第{}回合".format(episode), "通过{}个管道".format(total_scores))
        if terminal or (total_scores > 2000):
            print("游戏结束", "第{}回合".format(episode), "共通过{}个管道".format(total_scores))
            total_scores = 0
            episode += 1


