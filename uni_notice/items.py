# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class UniNoticeItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field() #공지사항 제목
    url = scrapy.Field() # 상세 페이지 URL
    writer = scrapy.Field() #공지사항 글쓴이
    posted_at = scrapy.Field() #공지사항 올라온 날짜
    content = scrapy.Field() # 본문 텍스트
    attachments = scrapy.Field() # 첨부파일 목록

