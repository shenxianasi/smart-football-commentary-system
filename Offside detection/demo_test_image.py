import random
import cv2
import numpy as np
from hashlib import md5
from model import Web_Detector
from chinese_name_list import Label_list

def generate_color_based_on_name(name):
    # 使用哈希函数生成稳定的颜色
    hash_object = md5(name.encode())
    hex_color = hash_object.hexdigest()[:6]  # 取前6位16进制数
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (b, g, r)  # OpenCV 使用BGR格式

def calculate_polygon_area(points):
    return cv2.contourArea(points.astype(np.float32))


def adjust_parameter(image_size, base_size=1000):
    max_size = max(image_size)
    return max_size / base_size


def draw_detections(image, info, alpha=0.2):
    name, bbox, conf, cls_id, mask = info['class_name'], info['bbox'], info['score'], info['class_id'], info['mask']
    adjust_param = adjust_parameter(image.shape[:2])

    if mask is None:
        x1, y1, x2, y2 = bbox
        aim_frame_area = (x2 - x1) * (y2 - y1)
        cv2.rectangle(image, (x1, y1), (x2, y2), color=(0, 0, 255), thickness=int(3 * adjust_param))
    else:
        mask_points = np.concatenate(mask)
        aim_frame_area = calculate_polygon_area(mask_points)
        mask_color = generate_color_based_on_name(name)
        try:
            overlay = image.copy()
            cv2.fillPoly(overlay, [mask_points.astype(np.int32)], mask_color)
            image = cv2.addWeighted(overlay, 0.3, image, 0.7, 0)
            cv2.drawContours(image, [mask_points.astype(np.int32)], -1, (0, 0, 255), thickness=int(8 * adjust_param))

        except Exception as e:
            print(f"An error occurred: {e}")

    return image, aim_frame_area


def process_frame(model, image):
    pre_img = model.preprocess(image)
    pred = model.predict(pre_img)
    det = pred[0]

    if det is not None and len(det):
        det_info = model.postprocess(pred)
        for info in det_info:
            image, _ = draw_detections(image, info)
    return image


if __name__ == "__main__":
    cls_name = Label_list
    model = Web_Detector()
    model.load_model("./runs/segment/train4/weights/best.pt")

    # 图片处理
    image_path = './icon/football.png'
    image = cv2.imread(image_path)
    if image is not None:
        processed_image = process_frame(model, image)
        cv2.imshow('Processed Image', processed_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print('Image not found.')

