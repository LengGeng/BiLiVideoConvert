import re
import os
import json
import warnings
from sys import argv
from getopt import getopt
from typing import Union
from subprocess import Popen

DEVNULL = open(os.devnull, 'w')
CONFIG = {}
CONFIG_PATH = "config.json"
FORMAT_VIDEO_NAME = "{i}、{title}-{name}"


class BiLiVideoConvert:

    def __init__(self, input_dir: str = None, output_dir: str = None):
        """
        input_dir 相当于 Android/data/tv.danmaku.bili/download 目录，即该文件夹下存在多个下载的视频项目
        :param input_dir: 下载视频路径
        :param output_dir: 转换后视频存放路径
        """
        # 参数为空时读取配置文件，配置文件中不存在则使用默认配置
        if input_dir is None:
            input_dir = CONFIG.get("input_dir", "download")
        if output_dir is None:
            output_dir = CONFIG.get("output_dir", "output")
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.movie_dirs = os.listdir(input_dir)
        self.movies = {}

    def parse_movies(self):
        for movie_info in self.get_movie_infos():
            avid = movie_info.get("avid")
            if avid:
                avid = f"AV{avid}"
            bvid = movie_info["bvid"]
            season_id = movie_info["season_id"]
            if season_id:
                season_id = f"S_{season_id}"
            vid = avid or bvid or season_id
            # 不存在添加默认信息
            if vid not in self.movies:
                self.movies[vid] = {
                    "avid": avid,
                    "bvid": bvid,
                    "season_id": season_id,
                    "title": movie_info['title'],  # 标题
                    "total": 0,  # 总量
                    "download_total": 0,  # 下载总量
                    "page_data": []  # 视频Page数据
                }
            # 判断视频是否下载完成，添加分P数据
            is_completed = movie_info['is_completed']  # 是否下载完成
            self.movies[vid]["total"] += 1
            page_data = {
                "page": movie_info["page"],
                "part": movie_info["part"],
                "is_completed": is_completed
            }
            if is_completed:
                self.movies[vid]["download_total"] += 1
                page_data["video_path"] = movie_info["video_path"]
                page_data["audio_path"] = movie_info["audio_path"]
            self.movies[vid]["page_data"].append(page_data)

    def get_movie_infos(self) -> dict:
        """
        获取 input_dir 下视频项目的信息
        :return:
        """
        for movie_dir in self.movie_dirs:
            # 拼接视频项目的绝对路径
            movie_ads_dir = os.path.join(self.input_dir, movie_dir)
            # 遍历视频项目下的目录
            for folder_name, sub_folders, file_names in os.walk(movie_ads_dir):
                entry_file = os.path.join(folder_name, "entry.json")
                # 以存在entry.json文件为判断视频目录依据
                if os.path.exists(entry_file):
                    # 解析 entry 文件
                    entry = parse_entry(entry_file)
                    if entry:
                        yield entry
                        # if movie_dir == str(entry['vid'])

    def convert(self, vid: Union[int, str]):
        # 视频项目目录
        if vid in self.movies:
            movie_info = self.movies.get(vid)
            print(movie_info)
        else:
            print("无效的视频ID")
            return
        # 拼接视频输出目录
        project_output_dir = filename_filter(os.path.join(self.output_dir, movie_info["title"]))
        # 判断目录是否存在,没有就创建
        if not os.path.exists(project_output_dir):
            os.makedirs(project_output_dir)
        # 转换视频
        for page_data in movie_info["page_data"]:
            # 判断视频是否下载完成
            if page_data["is_completed"]:
                # 获取格式化后的文件名
                page_name = format_video_name(**movie_info, **page_data)
                composite_video(
                    os.path.abspath(page_data["video_path"]),
                    os.path.abspath(page_data["audio_path"]),
                    os.path.abspath(os.path.join(project_output_dir, filename_filter(page_name)))
                )
            else:
                print(f"{movie_info.get('title')}-{page_data.get('part')}未下载完成!")

    def show_info(self):
        """
        展示视频信息
        :return:
        """
        movies_list = []
        for index, [vid, movie] in enumerate(self.movies.items()):
            movies_list.append(vid)
            print(f"{index + 1}、({vid: <12})[{movie['download_total']:-3}/{movie['total']:-3}] {movie['title']}")

        index: str = input("请输入要转换的编号(all 全部, exit 退出): ")
        if index == "all":
            for vid in movies_list:
                self.convert(vid)
        elif index in ["exit"]:
            print("用户退出")
            exit(0)
        else:
            self.convert(movies_list[int(index) - 1])

    def run(self):
        """
        主程序
        :return:
        """
        print("开始解析视频信息...")
        self.parse_movies()
        print("解析视频信息完成")
        self.show_info()
        pass


def format_video_name(**video_info: dict) -> str:
    """
    根据 FORMAT_VIDEO_NAME 格式化转换的视频文件名
    {title} 视频标题
    {name} {part} 视频名称
    {i} {page} {index} 视频索引,从1开始
    :param video_info: 视频信息
    :return: 格式化后的文件名
    """
    title = video_info.get("title", "")
    part = video_info.get("part", "")
    page = str(video_info.get("page", ""))
    # TODO 判断视频名称是否包序号 part.startswith(page), 存在则不添加序号
    result = FORMAT_VIDEO_NAME + ".mp4"
    # 视频索引
    result = result.replace("{i}", page)
    result = result.replace("{index}", page)
    result = result.replace("{page}", page)
    # 视频名称
    result = result.replace("{name}", part)
    result = result.replace("{part}", part)
    # 视频标题
    result = result.replace("{title}", title)
    return result


def composite_video(video_path: str, audio_path: str, out_path: str):
    """
    合成mp4文件
    :param video_path: 视频路径
    :param audio_path: 音频路径
    :param out_path: 输出路径
    :return:
    """
    # 生成合成命令
    cmd = f'ffmpeg -y -i "{video_path}" -i "{audio_path}" -codec copy "{out_path}"'
    print('*' * 50)
    print("视频源：" + video_path)
    print("音频源：" + audio_path)
    print("输出源：" + out_path)
    Popen(cmd, stderr=DEVNULL).wait()


def filename_filter(filename: str, repl: str = '') -> str:
    """
    将文件名替换成合法的文件名
    :param filename: 原文件名
    :param repl: 替换字符
    :return: 合法文件名
    """
    return re.sub('[/:*?"<>|]', repl, filename)


def parse_entry(entry_file):
    """
    解析视频配置(入口)文件
    :param entry_file: 文件路径
    :return: 视频信息
    """
    # 打开文件
    try:
        with open(entry_file, 'r', encoding='utf-8') as fp:
            entry: dict = json.load(fp)
            # 解析媒体类型
            media_type: int = entry.get('media_type')  # 媒体类型,1的可能是blv格式
            if media_type not in [2]:
                # 不支持的媒体类型
                warnings.warn(f"Warning Unsupported media type:{media_type} in {entry_file}")
                return
            # 解析视频 ID
            avid: int = entry.get('avid')  # avid
            bvid: str = entry.get('bvid')  # bvid
            season_id: int = entry.get('season_id')  # season_id, 番剧id
            # 视频信息
            title: str = entry.get("title")  # 视频标题
            is_completed: bool = entry.get("is_completed", False)  # 是否下载完成
            # 获取当前视频分集的信息数据
            if avid or bvid:
                page = entry["page_data"]["page"]  # 视频索引
                part = entry["page_data"]["part"]  # 视频标题
            if season_id:
                page = entry["ep"]["page"]
                part = entry["ep"]["index_title"]

            item = {
                "avid": avid,
                "bvid": bvid,
                "season_id": season_id,
                "title": title,
                "is_completed": is_completed,
                "page": page,
                "part": part
            }
            # 判断视频下载完成, 获取视频文件及音频文件信息
            if is_completed:
                # 视频、音频下载目录
                type_tag = entry.get('type_tag')
                # 视频路径
                video_path = os.path.join(os.path.dirname(entry_file), type_tag, "video.m4s")
                if os.path.exists(video_path):  # 判断文件是否存在
                    item["video_path"] = video_path
                # 音频路径
                audio_path = os.path.join(os.path.dirname(entry_file), type_tag, "audio.m4s")
                if os.path.exists(audio_path):  # 判断文件是否存在
                    item["audio_path"] = audio_path
            return item
    except json.decoder.JSONDecodeError as e:
        # 文件无法解析
        warnings.warn(f"Warning file could not parse: {entry_file} \n{e.msg}")


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
