from __future__ import division
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np
import cv2

def predict_transforms(prediction, input_dim, anchors, num_classes, CUDA=True):
    """
    Takes a detection featuremap and turns it into a 2-D tensor, where each row of a tensor corresponds to attributes of a bounding box

    :param prediction: output of yolo layer
    :param input_dim: input image dimension
    :param anchors:
    :param num_classes:
    :param CUDA:
    :return:
    """
    batch_size = prediction.size(0)
    stride = input_dim// prediction.size(2)
    grid_size = input_dim// stride
    bbox_attrs = 5+num_classes
    num_anchors = len(anchors)

    # prediction = prediction.view(batch_size, bbox_attrs*num_anchors, grid_size*grid_size)
    prediction = prediction.view(batch_size, bbox_attrs * num_anchors, grid_size * grid_size)
    prediction = prediction.transpose(1, 2).contiguous()
    prediction = prediction.view(batch_size, grid_size*grid_size*num_anchors, bbox_attrs)

    # dimensions of anchors are in accordance with the `height` and `width` attributes of the `net` block
    # These attributes describe the dimensions of input image, which is larger (by a factor of stride) than the detection map
    # Hence divide the anchors by stride of detection feature
    anchors = [(a[0]/stride, a[1]/stride) for a in anchors]

    # sigmoid the x, y coordinates and objectness score
    # sigmoid the center_x, center_y and object confidence
    prediction[:,:,0] = torch.sigmoid(prediction[:,:,0])
    prediction[:,:,1] = torch.sigmoid(prediction[:,:,1])
    prediction[:,:,2] = torch.sigmoid(prediction[:,:,2])

    # add grid offsets to the centre coordinate predictions
    grid = np.arange(grid_size)
    a, b = np.meshgrid(grid, grid)

    x_offset = torch.FloatTensor(a).view(-1, 1)
    y_offset = torch.FloatTensor(b).view(-1, 1)

    if CUDA:
        x_offset = x_offset.cuda()
        y_offset = y_offset.cuda()

    x_y_offset = torch.cat((x_offset, y_offset), 1).repeat(1, num_anchors).view(-1, 2).unsqueeze(0)

    prediction[:, :, :2] += x_y_offset

    # apply anchors to dimensions of boundingbox
    # logspace transform of height and width
    anchors = torch.FloatTensor(anchors)

    if CUDA:
        anchors = anchors.cuda()

    anchors = anchors.repeat(grid_size*grid_size, 1).unsqueeze(0)
    prediction[:,:,2:4] = torch.exp(prediction[:,:,2:4])*anchors

    # apply sigmoid activations to class scores
    prediction[:,:,5:5+num_classes] = torch.sigmoid((prediction[:,:,5:5+num_classes]))

    # resize the detection map to the size of the input image
    # bounding box attributes are sized according to the featuremap eg: (13x13)
    # if input image was 416x416, we multiply the attributes by 32 or the stride variable
    prediction[:,:,:4] *= stride

    return prediction
