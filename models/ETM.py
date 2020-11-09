#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   ETM.py
@Time    :   2020/09/30 15:26:45
@Author  :   Leilan Zhang
@Version :   1.0
@Contact :   zhangleilan@gmail.com
@Desc    :   None
'''

import os
import re
import pickle
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset,DataLoader
import numpy as np
from tqdm import tqdm
from .vae import VAE
import matplotlib.pyplot as plt
import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
sys.path.append('..')
from utils import evaluate_topic_quality, smooth_curve

class EVAE(VAE):
    def __init__(self, use_fc1,encode_dims=[2000,1024,512,20],decode_dims=[20,1024,2000],dropout=0.0,emb_dim=300):
        super(EVAE,self).__init__(use_fc1=use_fc1,encode_dims=encode_dims,decode_dims=decode_dims,dropout=dropout)
        self.emb_dim = emb_dim
        self.vocab_size = encode_dims[0]
        self.n_topic = encode_dims[-1]
        self.rho = nn.Linear(emb_dim,self.vocab_size)
        self.alpha = nn.Linear(emb_dim,self.n_topic)
        self.decoder = None

    def decode(self,z):
        wght_dec = self.alpha(self.rho.weight) #[K,V]
        beta = F.softmax(wght_dec,dim=0).transpose(1,0)
        res = torch.mm(z,beta)
        logits = torch.log(res+1e-6)
        return logits


class ETM:
    def __init__(self,bow_dim=10000,n_topic=20,taskname=None,device=None,use_fc1=False,emb_dim=300):
        self.bow_dim = bow_dim
        self.n_topic = n_topic
        #TBD_fc1
        self.vae = EVAE(use_fc1=use_fc1,encode_dims=[bow_dim,1024,512,n_topic],decode_dims=[n_topic,512,bow_dim],dropout=0.0,emb_dim=emb_dim)
        self.device = device
        self.id2token = None
        self.taskname = taskname
        if device!=None:
            self.vae = self.vae.to(device)
        self.use_fc1 = use_fc1

    def train(self,train_data,batch_size=256,learning_rate=1e-3,test_data=None,num_epochs=100,is_evaluate=False,log_every=5,beta=1.0,criterion='cross_entropy'):
        self.vae.train()
        self.id2token = {v:k for k,v in train_data.dictionary.token2id.items()}
        data_loader = DataLoader(train_data,batch_size=batch_size,shuffle=True,num_workers=4,collate_fn=train_data.collate_fn)

        optimizer = torch.optim.Adam(self.vae.parameters(),lr=learning_rate)
        #scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
        trainloss_lst, valloss_lst = [], []
        recloss_lst, klloss_lst = [],[]
        c_v_lst, c_w2v_lst, c_uci_lst, c_npmi_lst, mimno_tc_lst, td_lst = [], [], [], [], [], []
        for epoch in range(num_epochs):
            epochloss_lst = []
            for iter,data in enumerate(data_loader):
                optimizer.zero_grad()

                txts,bows = data
                bows = bows.to(self.device)
                '''
                n_samples = 20
                rec_loss = torch.tensor(0.0).to(self.device)
                for i in range(n_samples):
                    bows_recon,mus,log_vars = self.vae(bows,lambda x:torch.softmax(x,dim=1))
                    
                    logsoftmax = torch.log_softmax(bows_recon,dim=1)
                    _rec_loss = -1.0 * torch.sum(bows*logsoftmax)
                    rec_loss += _rec_loss
                rec_loss = rec_loss / n_samples
                '''
                bows_recon,mus,log_vars = self.vae(bows,lambda x:torch.softmax(x,dim=1))
                if criterion=='cross_entropy':
                    logsoftmax = torch.log_softmax(bows_recon,dim=1)
                    rec_loss = -1.0 * torch.sum(bows*logsoftmax)
                elif criterion=='bce_softmax':
                    rec_loss = F.binary_cross_entropy(torch.softmax(bows_recon,dim=1),bows,reduction='sum')
                elif criterion=='bce_sigmoid':
                    rec_loss = F.binary_cross_entropy(torch.sigmoid(bows_recon),bows,reduction='sum')
                
                kl_div = -0.5 * torch.sum(1+log_vars-mus.pow(2)-log_vars.exp())
                
                loss = rec_loss + kl_div * beta
                
                loss.backward()
                optimizer.step()

                trainloss_lst.append(loss.item()/len(bows))
                epochloss_lst.append(loss.item()/len(bows))
                if (iter+1) % 10==0:
                    print(f'Epoch {(epoch+1):>3d}\tIter {(iter+1):>4d}\tLoss:{loss.item()/len(bows):<.7f}\tRec Loss:{rec_loss.item()/len(bows):<.7f}\tKL Div:{kl_div.item()/len(bows):<.7f}')
            #scheduler.step()
            if (epoch+1) % log_every==0:
                # The code lines between this and the next comment lines are duplicated with WLDA.py, consider to simpify them.
                print(f'Epoch {(epoch+1):>3d}\tLoss:{sum(epochloss_lst)/len(epochloss_lst):<.7f}')
                print('\n'.join([str(lst) for lst in self.show_topic_words()]))
                print('='*30)
                smth_pts = smooth_curve(trainloss_lst)
                plt.plot(np.array(range(len(smth_pts)))*log_every,smth_pts)
                plt.xlabel('epochs')
                plt.title('Train Loss')
                plt.savefig('gsm_trainloss.png')
                if test_data!=None:
                    c_v,c_w2v,c_uci,c_npmi,mimno_tc, td = self.evaluate(test_data,calc4each=False)
                    c_v_lst.append(c_v), c_w2v_lst.append(c_w2v), c_uci_lst.append(c_uci),c_npmi_lst.append(c_npmi), mimno_tc_lst.append(mimno_tc), td_lst.append(td)
        scrs = {'c_v':c_v_lst,'c_w2v':c_w2v_lst,'c_uci':c_uci_lst,'c_npmi':c_npmi_lst,'mimno_tc':mimno_tc_lst,'td':td_lst}
        '''
        for scr_name,scr_lst in scrs.items():
            plt.cla()
            plt.plot(np.array(range(len(scr_lst)))*log_every,scr_lst)
            plt.savefig(f'wlda_{scr_name}.png')
        '''
        plt.cla()
        for scr_name,scr_lst in scrs.items():
            if scr_name in ['c_v','c_w2v','td']:
                plt.plot(np.array(range(len(scr_lst)))*log_every,scr_lst,label=scr_name)
        plt.title('Topic Coherence')
        plt.xlabel('epochs')
        plt.legend()
        plt.savefig(f'gsm_tc_scores.png')
        # The code lines between this and the last comment lines are duplicated with WLDA.py, consider to simpify them.


    def evaluate(self,test_data,calc4each=False):
        topic_words = self.show_topic_words()
        return evaluate_topic_quality(topic_words, test_data, taskname=self.taskname, calc4each=calc4each)


    def inference(self,doc_bow):
        # doc_bow: torch.tensor [vocab_size]; optional: np.array [vocab_size]
        if isinstance(doc_bow,np.array):
            doc_bow = torch.from_numpy(doc_bow)
        doc_bow = doc_bow.reshape(1,self.bow_dim).to(self.device)
        with torch.no_grad():
            mu,log_var = self.vae.encode(doc_bow)
            if self.use_fc1:
                mu = self.vae.fc1(mu) #TBD_fc1
            theta = F.softmax(mu,dim=1)
            return theta.detach().cpu().squeeze(0).numpy()


    def inference(self, doc_tokenized, dictionary,normalize=True):
        doc_bow = torch.zeros(1,self.bow_dim)
        for token in doc_tokenized:
            try:
                idx = dictionary.token2id[token]
                doc_bow[0][idx] = 1.0
            except:
                print(f'{token} not in the vocabulary.')
        doc_bow = doc_bow.to(self.device)
        with torch.no_grad():
            mu,log_var = self.vae.encode(doc_bow)
            if self.use_fc1:#TBD_fc1
                mu = self.vae.fc1(mu)
            if normalize:
                theta = F.softmax(mu,dim=1)
            return theta.detach().cpu().squeeze(0).numpy()

    def get_topic_word_dist(self,normalize=True):
        self.vae.eval()
        with torch.no_grad():
            idxes = torch.eye(self.n_topic).to(self.device)
            word_dist = self.vae.decode(idxes)  # word_dist: [n_topic, vocab.size]
            if normalize:
                word_dist = F.softmax(word_dist,dim=1)
            return word_dist.detach().cpu().numpy()

    def show_topic_words(self,topic_id=None,topK=15):
        topic_words = []
        idxes = torch.eye(self.n_topic).to(self.device)
        word_dist = self.vae.decode(idxes)
        word_dist = torch.softmax(word_dist,dim=1)
        vals,indices = torch.topk(word_dist,topK,dim=1)
        vals = vals.cpu().tolist()
        indices = indices.cpu().tolist()
        if topic_id==None:
            for i in range(self.n_topic):
                topic_words.append([self.id2token[idx] for idx in indices[i]])
        else:
            topic_words.append([self.id2token[idx] for idx in indices[topic_id]])
        return topic_words

if __name__ == '__main__':
    model = EVAE(use_fc1=True,encode_dims=[1024,512,256,20],decode_dims=[20,128,768,1024],emb_dim=300)
    model = model.cuda()
    inpt = torch.randn(234,1024).cuda()
    out,mu,log_var = model(inpt)
    print(out.shape)
    print(mu.shape)
