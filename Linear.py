import torch.nn as nn
import torch.nn.functional as F
from QuantLayer import STEQuant as QuantFunc

class QuantTrainLinear(nn.Linear):
    def __init__(self,in_features, out_features, bias=True, w_bit=4,o_bit=0,bn_args=None):
        super().__init__(in_features, out_features,bias)
        self.QuantFunc= QuantFunc
        self.w_bit= w_bit
        self.o_bit= o_bit
        self.w_interval= None
        self.o_interval= None
        self.QuantEnd= False
        if bn_args is not None:
            raise NotImplementedError

    def forward(self, x):
        if self.QuantEnd:
            out= super().forward(x)
        else:
            out= self.QuantForward(x)
        return out
    
    def QuantForward(self, x):
        w_interval= self.weight.abs().max()/(2**(self.w_bit-1)-1)
        if self.w_interval is not None:
            w_interval= 0.95*self.w_interval +0.05*w_interval
        if self.training:
            self.w_interval=w_interval.detach()
        self.q_weight= self.QuantFunc.apply(self.weight, self.w_interval, -2**(self.w_bit-1), 2**(self.w_bit-1)-1)
        if self.bias is not None:
            self.q_bias= self.QuantFunc.apply(self.bias, self.w_interval, -2**(self.w_bit-1), 2**(self.w_bit-1)-1)
            out= F.linear(x, self.q_weight, self.q_bias)
        else:
            out= F.linear(x, self.q_weight, self.bias)
        return out
    
    def QuantSelf(self):
        if not self.QuantEnd:
            w_interval= self.weight.abs().max()/(2**(self.w_bit-1)-1)
            if self.w_interval is not None:
                w_interval= 0.95*self.w_interval +0.05*w_interval
            else:
                print('Warring: w_interval missing!')
            self.w_interval=w_interval.detach()
            self.q_weight= self.QuantFunc.apply(self.weight, self.w_interval, -2**(self.w_bit-1), 2**(self.w_bit-1)-1)
            self.weight= nn.Parameter(self.q_weight)
            if self.bias is not None:
                self.q_bias= self.QuantFunc.apply(self.bias, self.w_interval, -2**(self.w_bit-1), 2**(self.w_bit-1)-1)
                self.bias= nn.Parameter(self.q_bias)
            self.QuantEnd= True
    def Train(self):
        self.QuantEnd= False
    def Eval(self):
        if not self.QuantEnd:
            self.QuantSelf()
