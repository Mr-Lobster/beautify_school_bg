import assets.list
import base64
import cv2
import json
import datetime
import utils
from flask import *
from PIL import Image
from io import BytesIO
import imutils

app = Flask(__name__)


@app.route('/get_edited_image', methods={"POST"})
def handle_get_edited_image():
    try:
        # 获取请求体的图片数据base64格式
        image_string = json.loads(request.data)['data']["image"]  # 生成dict
        # base64 解码成 --> byte[]
        img_data = base64.b64decode(image_string)
        # 调用 百度api接口
        bs64_result = utils.get_edited_image(img_data)
        compressed_bs64 = utils.compress_image_bs4(bs64_result)  # 压缩返回的数据
        # 返回给客户端的数据
        return_data = jsonify({
            'data': [
                {
                    'image_bs64': compressed_bs64,
                    'result': "获取人像成功"
                }
            ]
        })
        # 返回响应体
        return return_data, 200
    except Exception as err:
        print(str(err.with_traceback()))
        return "I'm err：" + str(err), 400


@app.route('/merge_with_bg', methods={"POST"})
def handle_merge_with_bg():
    try:
        # 获取请求体的图片数据 base64格式 + 融合坐标
        portrait = json.loads(request.data)['data']["image"]  # 生成dict
        bg_id = json.loads(request.data)['data']["bg_id"]
        rel_height_ratio = json.loads(request.data)['data']["rel_height_ratio"]
        rel_x = json.loads(request.data)['data']["rel_x"]
        rel_y = json.loads(request.data)['data']["rel_y"]
        rotate_d = json.loads(request.data)['data']["rotate_d"]

        # 获取照片
        chosen_bg = cv2.imread("assets/" + bg_id +
                               ".jpg", cv2.IMREAD_UNCHANGED)
        portrait = utils.base64_to_image(portrait)
        # 人像旋转
        portrait = utils.rotate_bound(portrait, float(rotate_d))
        # 人像缩放变换
        portrait = utils.my_resize(portrait, chosen_bg, rel_height_ratio)

        # rows, cols = portrait.shape[:2]
        # m1 = cv2.getRotationMatrix2D((cols / 2, rows / 2), float(rotate_d), 1)
        # portrait = cv2.warpAffine(portrait, m1, (cols, rows))

        # 开始叠加两张图片
        x1 = utils.get_x(chosen_bg, rel_x)
        y1 = utils.get_y(chosen_bg, rel_y)
        x2 = x1 + portrait.shape[1]
        y2 = y1 + portrait.shape[0]
        res_img = utils.merge_img(chosen_bg, portrait, y1, y2, x1, x2)

        # 保存照片至本地
        save_dir = datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')  # 获取当前时间并转化成字符串
        cv2.imwrite('output/' + save_dir + ".jpg", res_img)

        # 将np.array 转换为 base64编码

        pil_img = Image.fromarray(cv2.cvtColor(res_img, cv2.COLOR_BGR2RGB))
        buff = BytesIO()
        pil_img.save(buff, format="JPEG")
        new_image_string = base64.b64encode(buff.getvalue()).decode("utf-8")

        # new_image_string = utils.compress_image_bs4(new_image_string)

        # 返回给客户端的数据
        return_data = jsonify({
            'data': [
                {
                    'image_bs64': new_image_string,
                    'result': "人像与背景 " + bg_id + " 融合完成"
                }
            ]
        })
        # 返回响应体
        return return_data, 200
    except Exception as err:
        print(str(err.with_traceback()))
        return "报错信息：" + str(err.with_traceback()), 400


@app.route('/get_bg_list', methods={"GET"})
def handle_get_bg_list():
    try:
        # 返回给客户端的数据
        return_data = jsonify({
            'data': [
                {
                    'bg_list': assets.list.bg_list,
                    'length': len(assets.list.bg_list["data"]),
                    'result': "获取背景id列表成功"
                }
            ]
        })
        # 返回响应体
        return return_data, 200
    except Exception as err:
        return "报错信息：" + str(err), 400


@app.route('/get_bg_item', methods={"GET"})
def handle_get_bg_item():
    try:
        query_id = request.args.get("bg_id")  # <class 'str'>
        compressed_bs64 = utils.load_bs64compressed_bg_by_id(query_id)
        # 返回给客户端的数据
        return_data = jsonify({
            'data': [
                {
                    'bg_item_bs64': compressed_bs64,
                    'result': "获取背景id=" + query_id + " 成功"
                }
            ]
        })
        # 返回响应体
        return return_data, 200
    except Exception as err:
        return "报错信息：" + str(err), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=8080)
