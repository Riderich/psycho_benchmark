from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
import csv

driver= ChromiumPage()
driver.listen.start('x/player/wbi/v2')
driver.get("https://search.bilibili.com/video?keyword=和父母吵架")

resp= driver.listen.wait(count=5)
bvids=[]
for i in range(len(resp)):
    json_data=resp[i].response.body
    bvid=json_data['data']['bvid']
    print(bvid)
    bvids.append(bvid)

with open('bilibili.csv',mode='w',encoding='utf-8-sig', newline='') as f:
    csv_writer=csv.writer(f,delimiter=" ")

    for j in range(len(bvids)):
        driver.listen.start('x/v2/reply/wbi/')
        driver.get(f"https://www.bilibili.com/video/{bvids[j]}")

        print(f"正在打印第{j+1}个视频评论")
        for page in range(1,10):
            driver.scroll.to_bottom()
            print(f"正在打印第{page}页内容")
            resp= driver.listen.wait()
            json_data=resp.response.body
            comments=json_data['data']['replies']
            for index in comments:
                text= index['content']['message']
                text=text.replace("\n"," ")
                csv_writer.writerow(text)
                print(text)

            driver.scroll.to_bottom()

f.close()
