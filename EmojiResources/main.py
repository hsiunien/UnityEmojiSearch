from urllib import request
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image
from io import BytesIO
import glob
import re
import base64
import math

from unityparser import UnityDocument
from unityparser.constants import OrderedFlowDict

emojis_path = "emojis"
store_emoji_height = 64


class EmojiPageParser(HTMLParser):
    name = None
    isTdCode = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and len(attrs) > 0 and self.isTdCode and attrs[1][0] == 'name':
            self.name = emojis_path + "/" + attrs[1][1] + ".png"
            self.name = self.name.replace("_", "-")
        if tag == 'img' and self.name is not None and self.find_src(attrs) is not None:
            self.decode_save_image(self.find_src(attrs), self.name)
            self.name = None
        if tag == 'td' and len(attrs) > 0 and attrs[0][1] == 'code':
            self.isTdCode = True

    def handle_endtag(self, tag):
        if tag == 'td':
            self.isTdCode = False

    def find_src(self, li):
        for item in li:
            if item[0] == 'src':
                return item[1]
        return None

    def decode_save_image(self, src, filename):
        """
        解码图片
        :param src: 图片编码
            eg:
                src="data:image/gif;base64,R0lGODlhMwAxAIAAAAAAAP///
                    yH5BAAAAAAALAAAAAAzADEAAAK8jI+pBr0PowytzotTtbm/DTqQ6C3hGX
                    ElcraA9jIr66ozVpM3nseUvYP1UEHF0FUUHkNJxhLZfEJNvol06tzwrgd
                    LbXsFZYmSMPnHLB+zNJFbq15+SOf50+6rG7lKOjwV1ibGdhHYRVYVJ9Wn
                    k2HWtLdIWMSH9lfyODZoZTb4xdnpxQSEF9oyOWIqp6gaI9pI1Qo7BijbF
                    ZkoaAtEeiiLeKn72xM7vMZofJy8zJys2UxsCT3kO229LH1tXAAAOw=="

        :return: str 保存到本地的文件名
        """
        # 1、信息提取
        result = re.search("data:image/(?P<ext>.*?);base64,(?P<data>.*)", src, re.DOTALL)
        if result:
            data = result.groupdict().get("data")

        else:
            raise Exception("Do not parse!" + src)

        # 2、base64解码
        img = base64.urlsafe_b64decode(data)
        pillowImg = Image.open(BytesIO(img))
        pillowImg.save(filename)
        return filename


def produce_emoji():
    file_name = "emojislist.txt"
    if Path(file_name).exists():
        with Path(file_name) as path:
            content = path.read_text("utf-8")
    else:
        url = "https://unicode.org/emoji/charts/full-emoji-list.html"
        content = request.urlopen(url).read().decode('utf-8')
        with Path(file_name) as path:
            path.write_text(content, 'utf-8')

    if not Path(emojis_path).exists():
        Path(emojis_path).mkdir()
    parser = EmojiPageParser()
    parser.feed(content)


def createPic(wh=2048):
    folder_path = emojis_path + "/**"
    count = len(glob.glob(folder_path))
    if count == 0:
        return
    n = math.ceil(count ** 0.5)
    maxW = math.floor(wh / n)
    k = wh - maxW * n
    print("count:", count, " n:", n, " k:", k, " maxw:", maxW)
    p = Path(emojis_path)

    row_column = n
    outPng = Image.new(mode='RGBA', size=(wh, wh), color="#ff000000")
    global row
    row = 0
    global column
    column = 0
    for imgFile in sorted(p.glob('**/*')):
        with Image.open(imgFile.joinpath()) as img:
            iSize: tuple = img.size
            if iSize[0] != 64:
                pass
            rs_img = img.resize((maxW, maxW))
            loc1 = (column * maxW + 1, row * maxW + 1)
            outPng.paste(rs_img, loc1)
            column += 1
            if column >= row_column:
                column = 0
                row += 1

    outPng.show()
    outPng.save("emojis_all.png", "PNG")
    with Path("emojiWH.txt") as path:
         path.write_text(str(maxW), "utf-8")


def rewriteYaml(asset_name):
    with Path("emojiWH.txt") as path:
        if path.exists():
            store_emoji_height = path.read_text("utf-8")

    global entry
    doc = UnityDocument.load_yaml(asset_name)
    for et in doc.entries:
        if 'm_SpriteGlyphTable' in et.get_attrs():
            entry = et
    if entry is None:
        return
    spriteGlyphTable: OrderedFlowDict = entry.m_SpriteGlyphTable;
    characterTable: OrderedFlowDict = entry.m_SpriteCharacterTable
    p = Path(emojis_path)
    index = 0
    files = sorted(p.glob('**/*'))
    if len(files) != len(spriteGlyphTable):
        print("not equal files:", len(files), "spriteGlyphTable size:", len(spriteGlyphTable))
        return
    for imgFile in files:
        characterTable[index]["m_Name"] = imgFile.stem
        firstItem = imgFile.stem.split("-")[0]
        print(firstItem, "to int:", int(firstItem, 16))
        characterTable[index]['m_Unicode'] = int(firstItem, 16)
        spriteGlyphTable[index]['m_Metrics']['m_HorizontalBearingX'] = 0
        spriteGlyphTable[index]['m_Metrics'][
            'm_HorizontalBearingY'] = store_emoji_height  # to modify to fit your baseline

        index += 1

    # characterTable[0]["m_Name"]="test0"
    print(len(characterTable))
    doc.dump_yaml()


if __name__ == '__main__':
    ## step 1
    # produce_emoji()
    print("completed download images into  emojis, create picture")
    # createPic(4096)

    #Step2
    # remove hash tag below ,copy emoji_all.png to your project,and splice it by sprite editor,them copy .asset file to
    # this project (root folder)
    rewriteYaml("EmojiV15_4096.asset")
