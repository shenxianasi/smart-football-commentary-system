# bbox是一个包含x1,y1,x2,y2的列表或者元组
def get_center_of_bbox(bbox):
    # (x1,y1) 是左上角坐标 ， (x2,y2) 是右下角坐标
    x1 , y1 , x2 , y2 = bbox     # 解构bbox为x1 , y1 , x2 , y2
    return int((x1 + x2) / 2) , int((y1 + y2) / 2)

def get_bbox_width(bbox):
    return bbox[2] - bbox[0]

# 计算两点之间的欧几里得距离（直线距离）
def measure_distance(p1,p2):  # p1是点1(x1,y1)，p2是点2(x2,y2)
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

# 计算两点在x方向和y方向上的差值
def measure_xy_distance(p1,p2):
    return p1[0] - p2[0] , p1[1] - p2[1]

# 计算bbox的底部中心点（用于人的脚部位置）
def get_foot_postion(bbox):
    x1 , y1 , x2 , y2 = bbox
    return int((x1 + x2) / 2) , int(y2)