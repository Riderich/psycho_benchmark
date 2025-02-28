from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
import csv

#生成搜索url
driver= ChromiumPage()
driver.listen.start('edith.xiaohongshu.com/api/sns/web/v1/search/notes')
driver.get("https://www.xiaohongshu.com/search_result?keyword=和父母吵架")
    
driver.scroll.to_bottom()

#获取搜索结果中的视频信息
resp= driver.listen.wait()
json_data=resp.response.body
comments=json_data['data']['items']
texts=[]
tokens=[]
for index in comments[:5]:
    text= index['id']
    texts.append(text)
    token= index['xsec_token']
    tokens.append(token)

#根据视频信息生成视频url
with open('xiaohongshu.csv',mode='w',encoding='utf-8-sig', newline='') as f:
    csv_writer=csv.writer(f,delimiter=" ")

    for j in range(len(texts)):
        driver.listen.start('api/sns/web/v2/comment/')
        driver.get(f"https://www.xiaohongshu.com/explore/{texts[j]}?xsec_token={tokens[j]}")

#爬取评论
        print(f"正在打印第{j+1}篇推文评论")
        for page in range(1,5):
            driver.scroll.to_bottom()
            print(f"正在打印第{page}页内容")
            resp= driver.listen.wait()
            json_data=resp.response.body
            comments=json_data['data']['comments']
            for index in comments:
                text= index['content']
                text=text.replace("\n"," ")
                csv_writer.writerow(text)
                print(text)

            driver.scroll.to_bottom()

f.close()