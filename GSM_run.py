#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   NTM_run.py
@Time    :   2020/09/30 15:52:35
@Author  :   Leilan Zhang
@Version :   1.0
@Contact :   zhangleilan@gmail.com
@Desc    :   None
'''


import os
import re
import torch
import pickle
import argparse
import logging
from models import GSM
from utils import *
from dataset import DocDataset
from multiprocessing import cpu_count
#from torch.utils.data import Dataset,DataLoader

parser = argparse.ArgumentParser('GSM topic model')
parser.add_argument('--taskname',type=str,default='cnews10k',help='Taskname e.g cnews10k')
parser.add_argument('--no_below',type=int,default=5,help='The lower bound of count for words to keep, e.g 10')
parser.add_argument('--no_above',type=float,default=0.005,help='The ratio of upper bound of count for words to keep, e.g 0.3')
parser.add_argument('--num_epochs',type=int,default=100,help='Number of iterations (set to 100 as default, but 1000+ is recommended.)')
parser.add_argument('--n_topic',type=int,default=20,help='Num of topics')
parser.add_argument('--bkpt_continue',type=bool,default=False,help='Whether to load a trained model as initialization and continue training.')
parser.add_argument('--use_tfidf',type=bool,default=False,help='Whether to use the tfidf feature for the BOW input')
parser.add_argument('--rebuild',type=bool,default=True,help='Whether to rebuild the corpus, such as tokenization, build dict etc.(default True)')
parser.add_argument('--batch_size',type=int,default=512,help='Batch size (default=512)')
parser.add_argument('--criterion',type=str,default='cross_entropy',help='The criterion to calculate the loss, e.g cross_entropy, bce_softmax, bce_sigmoid')
parser.add_argument('--use_fc1',action='store_true',help='Whether to use a linear layer after the reparameter trick (default:False)') #TBD_fc1
args = parser.parse_args()

def main():
    global args
    taskname = args.taskname
    no_below = args.no_below
    no_above = args.no_above
    num_epochs = args.num_epochs
    n_topic = args.n_topic
    n_cpu = cpu_count()-2 if cpu_count()>2 else 2
    bkpt_continue = args.bkpt_continue
    use_tfidf = args.use_tfidf
    rebuild = args.rebuild
    batch_size = args.batch_size
    criterion = args.criterion
    n_topic = args.n_topic
    use_fc1 = args.use_fc1 #TBD_fc1

    device = torch.device('cuda')
    docSet = DocDataset(taskname,no_below=no_below,no_above=no_above,rebuild=rebuild,use_tfidf=False)
    voc_size = docSet.vocabsize
    print('voc size:',voc_size)
    model = GSM(bow_dim=voc_size,n_topic=n_topic,taskname=taskname,device=device,use_fc1=use_fc1) #TBD_fc1
    model.train(train_data=docSet,batch_size=batch_size,test_data=docSet,num_epochs=num_epochs,log_every=10,beta=1.0,criterion=criterion)
    model.evaluate(test_data=docSet)

if __name__ == "__main__":
    main()