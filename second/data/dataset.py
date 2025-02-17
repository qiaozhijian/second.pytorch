import pathlib
import pickle
import time
from functools import partial

import numpy as np

from second.core import box_np_ops
from second.core import preprocess as prep
from second.data import kitti_common as kitti
from second.data.preprocess import _read_and_prep_v9


class Dataset(object):
    """An abstract class representing a pytorch-like Dataset.
    All other datasets should subclass it. All subclasses should override
    ``__len__``, that provides the size of the dataset, and ``__getitem__``,
    supporting integer indexing in range from 0 to len(self) exclusive.
    """

    def __getitem__(self, index):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError



class KittiDataset(Dataset):
    def __init__(self, info_path, root_path, num_point_features,
                 target_assigner, feature_map_size, prep_func):
        with open(info_path, 'rb') as f:
            infos = pickle.load(f)
        #self._kitti_infos = kitti.filter_infos_by_used_classes(infos, class_names)
        self._root_path = root_path
        self._kitti_infos = infos
        self._num_point_features = num_point_features
        print("remain number of infos:", len(self._kitti_infos))
        # generate anchors cache
        # [352, 400]
        ret = target_assigner.generate_anchors(feature_map_size)
        anchors = ret["anchors"]
        anchors = anchors.reshape([-1, 7]) #default [1,248,216,2,7]
        matched_thresholds = ret["matched_thresholds"]
        unmatched_thresholds = ret["unmatched_thresholds"]
        anchors_bv = box_np_ops.rbbox2d_to_near_bbox(
            anchors[:, [0, 1, 3, 4, 6]])
        # anchors 7维度内容分别是[x,y,z,w,l,h,yaw]
        # anchors_bv 因为这相当于是在俯视图上划分的anchor，只需要最左上和最右下两个坐标
        # matched_thresholds 对应着每一类被认为是pos的IOU最小值
        # unmatched_thresholds 对应着每一类被认为是neg的IOU最大值
        anchor_cache = {
            "anchors": anchors,
            "anchors_bv": anchors_bv,
            "matched_thresholds": matched_thresholds,
            "unmatched_thresholds": unmatched_thresholds,
        }
        self._prep_func = partial(prep_func, anchor_cache=anchor_cache)

    def __len__(self):
        return len(self._kitti_infos)

    @property
    def kitti_infos(self):
        return self._kitti_infos

    def __getitem__(self, idx):
        return _read_and_prep_v9(
            info=self._kitti_infos[idx],
            root_path=self._root_path,
            num_point_features=self._num_point_features,
            prep_func=self._prep_func)
