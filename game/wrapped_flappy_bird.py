import numpy as np
import sys
import os
#os.environ["SDL_VIDEODRIVER"] = "dummy"
import random
import pygame
import flappy_bird_utils
import pygame.surfarray as surfarray
from pygame.locals import *
from itertools import cycle

FPS = 30
SCREENWIDTH  = 288   #屏幕宽度
SCREENHEIGHT = 512   #屏幕高度

pygame.init()
FPSCLOCK = pygame.time.Clock()
SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
pygame.display.set_caption('Flappy Bird')

IMAGES, SOUNDS, HITMASKS = flappy_bird_utils.load()
PIPEGAPSIZE = 100 # gap between upper and lower part of pipe 管道上部和下部的间隙
BASEY = SCREENHEIGHT * 0.79

PLAYER_WIDTH = IMAGES['player'][0].get_width()
PLAYER_HEIGHT = IMAGES['player'][0].get_height()
PIPE_WIDTH = IMAGES['pipe'][0].get_width()
PIPE_HEIGHT = IMAGES['pipe'][0].get_height()
BACKGROUND_WIDTH = IMAGES['background'].get_width()

PLAYER_INDEX_GEN = cycle([0, 1, 2, 1])


class GameState:
    def __init__(self):
        self.score = self.playerIndex = self.loopIter = 0
        self.playerx = int(SCREENWIDTH * 0.2)    # 小鸟的x轴位置固定=57
        self.playery = int((SCREENHEIGHT - PLAYER_HEIGHT) / 2)    # 小鸟的y轴位置固定=244 也就是上下距离相同，使得鸟在中间
        self.basex = 0
        self.baseShift = IMAGES['base'].get_width() - BACKGROUND_WIDTH    # 48=336-288 底座的宽度减去背景的宽度

        newPipe1 = getRandomPipe()    # 生成随机新管道
        newPipe2 = getRandomPipe()
        self.upperPipes = [
            {'x': SCREENWIDTH, 'y': newPipe1[0]['y']},
            {'x': SCREENWIDTH + (SCREENWIDTH / 2), 'y': newPipe2[0]['y']},
        ]
        self.lowerPipes = [
            {'x': SCREENWIDTH, 'y': newPipe1[1]['y']},
            {'x': SCREENWIDTH + (SCREENWIDTH / 2), 'y': newPipe2[1]['y']},
        ]

        # player velocity, max velocity, downward accleration, accleration on flap
        self.pipeVelX = -4            # x轴的初始速度
        self.playerVelY    =  0    # player's velocity along Y, default same as playerFlapped 初始速度Y
        self.playerMaxVelY =  10   # max vel along Y, max 最大速度Y
        self.playerMinVelY =  -8   # min vel along Y, max 最小速度Y
        self.playerAccY    =   1   # players downward 下降加速度Y
        self.playerFlapAcc =  -9   # players speed on flapping 上升加速度Y
        self.playerFlapped = False  # True when player flaps

    def frame_step(self, input_actions):
        pygame.event.pump()    # 内部进程pygame事件处理程序，每次循环调用，保持系统更新

        reward = 0.1
        terminal = False    # 不要终点

        if sum(input_actions) != 1:
            raise ValueError('Multiple input actions!')

        # input_actions[0] == 1: do nothing,即action=[1 0]
        # input_actions[1] == 1: flap the bird,即action=[0 1]
        if input_actions[1] == 1:
            if self.playery > -2 * PLAYER_HEIGHT:
                self.playerVelY = self.playerFlapAcc
                self.playerFlapped = True
                # SOUNDS['wing'].play()

        # check for score
        playerMidPos = self.playerx + PLAYER_WIDTH / 2
        for pipe in self.upperPipes:
            pipeMidPos = pipe['x'] + PIPE_WIDTH / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:    # 小鸟过管道中间，得一分
                self.score += 1
                # SOUNDS['point'].play()
                reward = 1
        # if in the middle reward + 0.1
        # if self.playery > (self.upperPipes[0]['y'] + 320) and self.playery < (self.lowerPipes[0]['y'] - PLAYER_HEIGHT) :
        #   reward += 0.1

        # playerIndex basex change
        if (self.loopIter + 1) % 3 == 0:
            self.playerIndex = next(PLAYER_INDEX_GEN)
        self.loopIter = (self.loopIter + 1) % 30
        self.basex = -((-self.basex + 100) % self.baseShift)

        # player's movement
        if self.playerVelY < self.playerMaxVelY and not self.playerFlapped:
            self.playerVelY += self.playerAccY
        if self.playerFlapped:
            self.playerFlapped = False
        self.playery += min(self.playerVelY, BASEY - self.playery - PLAYER_HEIGHT)
        if self.playery < 0:
            self.playery = 0

        # move pipes to left
        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            uPipe['x'] += self.pipeVelX
            lPipe['x'] += self.pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < self.upperPipes[0]['x'] < 5:
            newPipe = getRandomPipe()
            self.upperPipes.append(newPipe[0])
            self.lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if self.upperPipes[0]['x'] < -PIPE_WIDTH:
            self.upperPipes.pop(0)
            self.lowerPipes.pop(0)

        # check if crash here
        isCrash= checkCrash({'x': self.playerx, 'y': self.playery,
                             'index': self.playerIndex},
                            self.upperPipes, self.lowerPipes)
        if isCrash:
            # SOUNDS['hit'].play()
            # SOUNDS['die'].play()
            terminal = True
            self.__init__()
            reward = -1

        # draw sprites
        SCREEN.blit(IMAGES['background'], (0, 0))

        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (self.basex, BASEY))
        # print score so player overlaps the score
        # showScore(self.score)
        SCREEN.blit(IMAGES['player'][self.playerIndex],
                    (self.playerx, self.playery))

        # 小鸟的垂直速度速度
        scale = (self.playerMaxVelY - self.playerMinVelY + 1 ) / (2**6 - 1)
        #print(self.playerMaxVelY - self.playerMinVelY)
        zero = 0
        x = round((self.playerVelY + 9)/ scale + zero)
        #print(self.playerVelY)
        x_bin = bin(x)
        #print(x_bin)
        x_out = [int(d) for d in str(x_bin)[2:]]
        num =  6 - len(x_out)
        for i in range(num):
            x_out.insert(0, 0) 


        # 小鸟与它前面一对水管中下面那根水管的水平距离
        scale2 = (SCREENWIDTH + PIPE_WIDTH / 2 -  self.playerx) / (2**8 - 1)         
        zero2 = 0
        if self.lowerPipes[0]['x'] - 57 + PIPE_WIDTH / 2  - PLAYER_WIDTH / 2 >= 0:
          pip_x = round((self.lowerPipes[0]['x'] - 57 + PIPE_WIDTH / 2  - PLAYER_WIDTH / 2) / scale2 + zero2)
        else:
          pip_x = round((self.lowerPipes[1]['x'] - 57 + PIPE_WIDTH / 2  - PLAYER_WIDTH / 2) / scale2 + zero2)
        #print(self.lowerPipes[0]['x'] - 57 + PIPE_WIDTH / 2  - PLAYER_WIDTH / 2)
        pip_bin = bin(pip_x)
        #print(pip_bin)
        pip_out = [int(d) for d in str(pip_bin)[2:]]
        num2 =  8 - len(pip_out)
        for i in range(num2):
            pip_out.insert(0, 0) 

        # 小鸟与它前面一对水管中下面那根水管的顶端的垂直距离

        scale3 =  2 * BASEY / (2**8 - 1)         
        zero3 = 0
        if self.lowerPipes[0]['x'] - 57 +  PIPE_WIDTH / 2  - PLAYER_WIDTH / 2 >= 0:
            y = self.lowerPipes[0]['y'] - self.playery + 404
        else:
            y = self.lowerPipes[1]['y'] - self.playery + 404
        pip_y = round(y / scale3 + zero3)
        pip_bin_y = bin(pip_y)
        #print(pip_bin_y)
        pip_out_y = [int(d) for d in str(pip_bin_y)[2:]]
        num2 =  8 - len(pip_out_y)
        for i in range(num2):
            pip_out_y.insert(0, 0) 
        
        # 小鸟与它前面一对水管中上面那根水管的顶端的垂直距离
        
        scale3 =  2 * BASEY / (2**6 - 1)
        zero3 = 0
        if self.lowerPipes[0]['x'] - 57 +  PIPE_WIDTH / 2  - PLAYER_WIDTH / 2 >= 0:
            y_up = self.upperPipes[0]['y'] - self.playery + 320 + 404
        else:
            y_up = self.upperPipes[1]['y'] - self.playery + 320 + 404
        #print(y_up)
        #print(self.upperPipes[0]['y'])
        #print(self.playery)
        pip_y_up = round(y_up / scale3 + zero3)
        pip_bin_y_up = bin(pip_y_up)
        #print(pip_bin_y_up)
        pip_out_y_up = [int(d) for d in str(pip_bin_y_up)[2:]]
        num2 =  6 - len(pip_out_y_up)
        for i in range(num2):
            pip_out_y_up.insert(0, 0) 

        
        #print(x_out)
        #print(pip_out)
        #print(pip_out_y)

        # out = np.array([x_out, pip_out, pip_out_y, pip_out_y_up])
        out = x_out + pip_out + pip_out_y + pip_out_y_up
        #print(out)
        out = np.array(out)
        #out = np.expand_dims(out, axis=0)
        #print(out)
        # print(out.shape)
        pygame.display.update()
        FPSCLOCK.tick(FPS)
        #print self.upperPipes[0]['y'] + PIPE_HEIGHT - int(BASEY * 0.2)
        return out, reward, terminal

def getRandomPipe():
    """returns a randomly generated pipe"""
    # y of gap between upper and lower pipe 上下两管间距
    gapYs = [20, 30, 40, 50, 60, 70, 80, 90]
    index = random.randint(0, len(gapYs)-1)    # 返回[0, 7)区间的值
    gapY = gapYs[index]    # 例如index=2，gapY=40

    gapY += int(BASEY * 0.2)    # 120=40+80
    pipeX = SCREENWIDTH + 10    # 298=288+10

    return [
        {'x': pipeX, 'y': gapY - PIPE_HEIGHT},  # upper pipe 70-320
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE},  # lower pipe 70+100
    ]


def showScore(score):
    """displays score in center of screen"""
    scoreDigits = [int(x) for x in list(str(score))]
    totalWidth = 0 # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += IMAGES['numbers'][digit].get_width()

    Xoffset = (SCREENWIDTH - totalWidth) / 2

    for digit in scoreDigits:
        SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.1))
        Xoffset += IMAGES['numbers'][digit].get_width()


def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collders with base or pipes."""
    pi = player['index']
    player['w'] = IMAGES['player'][0].get_width()
    player['h'] = IMAGES['player'][0].get_height()

    # if player crashes into ground
    if player['y'] + player['h'] >= BASEY - 1:
        return True
    elif player['y'] ==  0:
        return True
    else:

        playerRect = pygame.Rect(player['x'], player['y'],
                      player['w'], player['h'])

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], PIPE_WIDTH, PIPE_HEIGHT)
            lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], PIPE_WIDTH, PIPE_HEIGHT)

            # player and upper/lower pipe hitmasks
            pHitMask = HITMASKS['player'][pi]
            uHitmask = HITMASKS['pipe'][0]
            lHitmask = HITMASKS['pipe'][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return True

    return False

def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    for x in range(rect.width):
        for y in range(rect.height):
            if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                return True
    return False

if __name__ == '__main__':
    a = GameState()
    action0 = np.array([1, 0])
    a.frame_step(action0)