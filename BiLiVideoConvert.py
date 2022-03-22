import json
import os
from sys import argv
from getopt import getopt

DEVNULL = open(os.devnull, 'w')
CONFIG = {}
CONFIG_PATH = "config.json"


class BiLiVideoConvert:

    def __init__(self, input_dir: str = None, output_dir: str = None):
        """
        input_dir 相当于 Android/data/tv.danmaku.bili/download 目录，即该文件夹下存在多个下载的视频项目
        :param input_dir: 下载视频路径
        :param output_dir: 转换后视频存放路径
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.movie_dirs = os.listdir(input_dir)
        self.movies = self.get_movie_info()

    def run(self):
        """
        主程序
        :return:
        """
        pass

    def get_movie_info(self) -> dict:
        """
        获取 input_dir 下视频项目的信息
        :return:
        """
        pass


def get_command_args() -> tuple:
    """
    获取命令行输入的参数
    :return:
    """
    i = o = None
    opts, args = getopt(argv[1:], "i:o:")
    for opt, arg in opts:
        if opt in ["i"]:
            i = arg
        if opt in ["o"]:
            o = arg
    return i, o


def load_config():
    """
    从文件读取配置
    :return:
    """
    try:
        global CONFIG
        with open(CONFIG_PATH, "r") as fp:
            CONFIG = json.load(fp)
    except FileNotFoundError:
        print("create default config.")
        CONFIG = {
            "input_dir": "download",
            "output_dir": "output"
        }
        refresh_config()
    except json.decoder.JSONDecodeError:
        print("读取配置文件错误，请检查配置文件，若无法使用可尝试删除配置文件。")


def refresh_config():
    """
    保存配置到文件
    :return:
    """
    with open(CONFIG_PATH, 'w', encoding="utf-8") as fp:
        json.dump(CONFIG, fp, ensure_ascii=False)


def main():
    load_config()
    video_convert = BiLiVideoConvert(*get_command_args())
    video_convert.run()


if __name__ == '__main__':
    main()
