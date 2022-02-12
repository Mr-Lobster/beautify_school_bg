import math
from aip import AipBodyAnalysis
import cv2
import numpy as np
import base64
import io
from PIL import Image
from io import BytesIO


def get_edited_image(raw_image):
    # 在百度云中申请，每天各接口有 500 次调用限制.
    APP_ID = '24948404'
    API_KEY = 'EkvToGU9o6GA1e4RqsBouCNE'
    SECRET_KEY = 'LWAlynHgSKRNF7O1zPuX0z6ZUA7ZSRwE'
    client = AipBodyAnalysis(APP_ID, API_KEY, SECRET_KEY)
    """ 带参数调用人像分割 """
    seg_res = client.bodySeg(raw_image)  # Base64编码后的png格式图片
    foreground_bs64 = seg_res['foreground']  # Base64编码后的png格式图片
    return foreground_bs64  # 返回base64格式编码的照片数据


def add_alpha_channel(img):
    """ 为jpg图像添加alpha通道 """

    b_channel, g_channel, r_channel = cv2.split(img)  # 剥离jpg图像通道
    alpha_channel = np.ones(
        b_channel.shape, dtype=b_channel.dtype) * 255  # 创建Alpha通道

    img_new = cv2.merge(
        (b_channel, g_channel, r_channel, alpha_channel))  # 融合通道
    return img_new


def merge_img(jpg_img, png_img, y1, y2, x1, x2):
    """ 将png透明图像与jpg图像叠加
        y1,y2,x1,x2为叠加位置坐标值
    """

    # 判断jpg图像是否已经为4通道
    if jpg_img.shape[2] == 3:
        jpg_img = add_alpha_channel(jpg_img)

    '''
    当叠加图像时，可能因为叠加位置设置不当，导致png图像的边界超过背景jpg图像，而程序报错
    这里设定一系列叠加位置的限制，可以满足png图像超出jpg图像范围时，依然可以正常叠加
    '''
    yy1 = 0
    yy2 = png_img.shape[0]
    xx1 = 0
    xx2 = png_img.shape[1]

    if x1 < 0:
        xx1 = -x1
        x1 = 0
    if y1 < 0:
        yy1 = - y1
        y1 = 0
    if x2 > jpg_img.shape[1]:
        xx2 = png_img.shape[1] - (x2 - jpg_img.shape[1])
        x2 = jpg_img.shape[1]
    if y2 > jpg_img.shape[0]:
        yy2 = png_img.shape[0] - (y2 - jpg_img.shape[0])
        y2 = jpg_img.shape[0]

    # 获取要覆盖图像的alpha值，将像素值除以255，使值保持在0-1之间
    alpha_png = png_img[yy1:yy2, xx1:xx2, 3] / 255.0
    alpha_jpg = 1 - alpha_png

    # 开始叠加
    for c in range(0, 3):
        jpg_img[y1:y2, x1:x2, c] = (
                (alpha_jpg * jpg_img[y1:y2, x1:x2, c]) + (alpha_png * png_img[yy1:yy2, xx1:xx2, c]))

    return jpg_img


# 压缩base64的图片
def compress_image_bs4(b64, mb=190, k=0.9):
    """不改变图片尺寸压缩到指定大小
    :param outfile: 压缩文件保存地址
    :param mb: 压缩目标，KB
    :param step: 每次调整的压缩比率
    :param quality: 初始压缩比率
    :return: 压缩文件地址，压缩文件大小
    """
    f = base64.b64decode(b64)
    with io.BytesIO(f) as im:
        o_size = len(im.getvalue()) // 1024
        if o_size <= mb:
            return b64
        im_out = im
        while o_size > mb:
            img = Image.open(im_out)
            x, y = img.size
            out = img.resize((int(x * k), int(y * k)), Image.ANTIALIAS)
            im_out.close()
            im_out = io.BytesIO()
            out.save(im_out, 'png')
            o_size = len(im_out.getvalue()) / 1024
    b64 = base64.b64encode(im_out.getvalue())
    im_out.close()
    return str(b64, encoding='utf8')


def load_bs64compressed_bg_by_id(bg_id):
    img_jpg_path = "assets/" + bg_id + ".jpg"
    img_jpg = cv2.imread(img_jpg_path, cv2.IMREAD_UNCHANGED)  # np.array
    # 将np.array 转换为 base64编码
    pil_img = Image.fromarray(cv2.cvtColor(img_jpg, cv2.COLOR_BGR2RGB))
    buff = BytesIO()
    pil_img.save(buff, format="JPEG")
    new_image_string = base64.b64encode(buff.getvalue()).decode("utf-8")
    compressed_bs64 = compress_image_bs4(new_image_string)
    return compressed_bs64


def convert_bs64_to_nparray(img_b64encode):
    img_b64decode = base64.b64decode(img_b64encode)  # base64解码
    image = io.BytesIO(img_b64decode)
    img = np.array(Image.open(image))
    return img


def base64_to_image(base64_code):
    # base64解码
    img_data = base64.b64decode(base64_code)
    # 转换为np数组
    img_array = np.fromstring(img_data, np.uint8)
    # 转换成opencv可用格式
    img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
    return img


# 高度 宽度
def my_resize(raw_img, raw_bg, rel_height_ratio):
    rel_height_ratio = float(rel_height_ratio)
    raw_img_ratio = raw_img.shape[0] / raw_img.shape[1]

    target_height = math.ceil(raw_bg.shape[0] * rel_height_ratio)
    target_width = math.ceil(target_height / raw_img_ratio)

    t_fx = target_width / raw_img.shape[1]
    t_fy = target_height / raw_img.shape[0]
    portrait = cv2.resize(raw_img, None, fx=t_fx, fy=t_fy,
                          interpolation=cv2.INTER_CUBIC)
    return portrait


# x
def get_x(raw_bg, rel_x):
    rel_x = float(rel_x)
    return int(raw_bg.shape[1] * rel_x)


# y
def get_y(raw_bg, rel_y):
    rel_y = float(rel_y)
    return int(raw_bg.shape[0] * rel_y)


def rotate_bound(image, angle):
    # grab the dimensions of the image and then determine the
    # center
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)

    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])

    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))

    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY

    # perform the actual rotation and return the image
    return cv2.warpAffine(image, M, (nW, nH))
