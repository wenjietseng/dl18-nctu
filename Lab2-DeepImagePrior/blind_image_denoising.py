# --- Import libs ---
from __future__ import print_function
import matplotlib.pyplot as plt
import os

import numpy as np
from models import *

import torch
import torch.optim

from torch.autograd import Variable
from utils.denoising_utils import *
from skimage.measure import compare_psnr

torch.backends.cudnn.enabled = True
torch.backends.cudnn.benchmark = True
dtype = torch.cuda.FloatTensor

imsize = -1
PLOT = True
sigma = 25
sigma_ = sigma / 255

# --- Load Image ---
fname = './images/noise_image.png'

if fname == './images/noise_image.png':
    img_noisy_pil = crop_image(get_image(fname, imsize)[0], d=32)
    img_noisy_np = pil_to_np(img_noisy_pil)
    
    # As we don't have ground truth
    img_pil = img_noisy_pil
    img_np = img_noisy_np
    
    if PLOT:
        plot_image_grid([img_np], 4, 5) # perhaps need to change 4, 5
        
# elif fname == 'data/denoising/F16_GT.png':
#     # Add synthetic noise 
#     img_pil = crop_image(get_image(fname, imsize)[0], d=32)
#     img_np = pil_to_np(img_pil)
    
#     img_noisy_pil, img_noisy_np = get_noisy_image(img_np, sigma_)
    
#     if PLOT:
#         plot_image_grid([img_np, img_noisy_np], 4, 6)
else:
    assert False

# --- Setup ---
INPUT = 'noise' # 'meshgrid'
pad = 'reflection'
OPT_OVER = 'net' # 'net,input'

reg_noise_std = 1./30. # set to 1./20. for sigma=50
LR = 0.01

OPTIMIZER = 'adam'
show_every = 500

if fname == './images/noise_image.png':
    num_iter = 1800
    input_depth = 3
    figsize = 5 
    
    net = skip(
                input_depth, 3, 
                num_channels_down = [128, 128, 128, 128, 128], 
                num_channels_up   = [128, 128, 128, 128, 128],
                num_channels_skip = [4, 4, 4, 4, 4], 
                upsample_mode='bilinear',
                need_sigmoid=True, need_bias=True, pad=pad, act_fun='LeakyReLU')

    net = net.type(dtype)

# elif fname == 'data/denoising/F16_GT.png':
#     num_iter = 3000
#     input_depth = 32 
#     figsize = 4 
    
#     net = get_net(input_depth, 'skip', pad,
#                   skip_n33d=128, 
#                   skip_n33u=128, 
#                   skip_n11=4, 
#                   num_scales=5,
#                   upsample_mode='bilinear').type(dtype)

else:
    assert False

net_input = get_noise(input_depth, INPUT, (img_pil.size[1], img_pil.size[0])).type(dtype).detach()

# Compute number of parameters
s  = sum([np.prod(list(p.size())) for p in net.parameters()]); 
print ('Number of params: %d' % s)

# Loss
mse = torch.nn.MSELoss().type(dtype)

img_noisy_var = np_to_var(img_noisy_np).type(dtype)

# --- Optimize ---
net_input_saved = net_input.data.clone()
noise = net_input.data.clone()

i = 0
def closure():
    
    global i
    
    if reg_noise_std > 0:
        net_input.data = net_input_saved + (noise.normal_() * reg_noise_std)
    
    out = net(net_input)
   
    total_loss = mse(out, img_noisy_var)
    total_loss.backward()
        
    print ('Iteration %05d    Loss %f' % (i, total_loss.data[0]), '\r', end='')
    if  PLOT and i % show_every == 0:
        out_np = var_to_np(out)
        plot_image_grid([np.clip(out_np, 0, 1)], factor=figsize, nrow=1)
        
    i += 1

    return total_loss

p = get_params(OPT_OVER, net, net_input)
optimize(OPTIMIZER, p, closure, LR, num_iter)
out_np = var_to_np(net(net_input))
q = plot_image_grid([np.clip(out_np, 0, 1), img_np], factor=13)