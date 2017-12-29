#!/usr/bin/env python
# -_- coding: utf-8 -_-


import gevent
from gevent import monkey
monkey.patch_all()

import os
import string
import threading

import requests
from bs4 import BeautifulSoup
import matplotlib
from matplotlib import pyplot as plt


HE_DICT = {}
SHE_DICT = {}


class LiteroticaArticle:
    """obtain an article from literotica.com"""

    def __init__(self, url, code=None):
        assert url.startswith('https://www.literotica.com/s/')
        self.code = code if code else url[29:]
        self.url = url

    def get_article(self):
        r = requests.get(self.url)
        soup = BeautifulSoup(r.text, 'lxml')
        self.pagenum = int(soup.find('span', {'class': 'b-pager-caption-t'}).text.split()[0])
        self.article = soup.find('div', {'class': 'b-story-body-x'}).div.p.text
        self.title = soup.find('div', {'class': 'b-story-header'}).h1.text
        self.category = soup.find('div', {'class': 'b-breadcrumbs'}).find_all('a')[1].text
        # self.tags = ''
        a = gevent.joinall([gevent.spawn(self._get_page, i)
                            for i in range(2, self.pagenum+1)], timeout=10)
        self.article += ''.join(map(lambda x: x[1], sorted((t.value for t in a),
                                key=lambda x: x[0])))
        # a = [self._get_page(i) for i in range(2, pagenum+1)]
        # self.article += ''.join(map(lambda x: x[1], sorted(a, key=lambda x: x[0])))

        return self.article

    def _get_page(self, num):
        r = requests.get(self.url+'?page={0}'.format(num))
        soup = BeautifulSoup(r.text, 'lxml')
        article = soup.find('div', {'class': 'b-story-body-x'}).div.p.text
        # if num == self.pagenum:
        #     self.tags = soup.find('div', {'class': 'b-s-story-tag-list'}).ul.text
        return (num, article)

    def save(self):
        with open('articles/' + self.code + '.txt', 'w') as f:
            f.write(self.article)


def download_article(url):
    if not os.path.isdir('articles'):
        os.mkdir('articles')
    a = LiteroticaArticle(url)
    a.get_article()
    a.save()


def download_all_articles(page_url):
    r = requests.get(page_url)
    soup = BeautifulSoup(r.text, 'lxml')
    # print(soup.find('table'))
    article_urls = map(lambda x: x.find('a')['href'], soup.find('table').find_all('td', {'class': 'mcol'})[1:])
    for url in article_urls:
        threading.Thread(target=download_article, args=(url, )).start()


def process_article(filename):
    with open('articles/' + filename) as f:
        for line in f:
            translator = str.maketrans('', '', string.punctuation)
            line = line.translate(translator)
            words = line.split()
            for idx, word in enumerate(words):
                try:
                    if word in ('he', 'He'):
                        HE_DICT[words[idx+1]] = HE_DICT.setdefault(words[idx+1], 0) + 1
                    elif word in ('she', 'She'):
                        SHE_DICT[words[idx+1]] = SHE_DICT.setdefault(words[idx+1], 0) + 1
                except IndexError:
                    pass


def explore_articles():
    for filename in os.listdir('articles'):
        process_article(filename)


def draw_absolute():
    heset = set(HE_DICT)
    sheset = set(SHE_DICT)
    data = []
    for word in heset.intersection(sheset):
        if HE_DICT[word] > 80 or SHE_DICT[word] > 80:
            data.append((word, HE_DICT[word], SHE_DICT[word]))
    data.sort(key=lambda x: x[1]+x[2])

    bar_width = 0.35
    index = list(range(len(data)))
    matplotlib.rcParams['font.size'] = 8
    matplotlib.rcParams["figure.figsize"] = [16, 4.8]
    rects1 = plt.bar(index, list(map(lambda x: x[1], data)), bar_width, color='#0072BC', label='He')
    rects2 = plt.bar(list(map(lambda x: x + bar_width, index)), 
                     list(map(lambda x: x[2], data)), bar_width, color='#ED1C24', label='She')
    plt.xticks(list(map(lambda x: x + bar_width, index)), list(map(lambda x: x[0], data)))
    plt.savefig('absolute.png')
    plt.close()


def draw_difference():
    heset = set(HE_DICT)
    sheset = set(SHE_DICT)
    data = []
    for word in heset.intersection(sheset):
        if HE_DICT[word] > 10 or SHE_DICT[word] > 10:
            data.append((word, HE_DICT[word] - SHE_DICT[word]))
    data.sort(key=lambda x: x[1])
    helist = data[-10:]
    shelist = data[:10]

    matplotlib.rcParams['font.size'] = 8
    bar_width = 0.35
    rects1 = plt.bar(list(range(10)), list(map(lambda x: x[1], shelist)),
                     bar_width, color='#ED1C24', label='She')
    rects2 = plt.bar(list(range(10, 20)), list(map(lambda x: x[1], helist)),
                     bar_width, color='#0072BC', label='He')
    plt.xticks(list(range(20)), list(map(lambda x: x[0], shelist + helist)))

    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06), fancybox=True, ncol=5)

    plt.savefig('difference.png')


def main():
    # download_all_articles('https://www.literotica.com/top/NonConsent-Reluctance-13/alltime/?page=1')
    explore_articles()
    draw_absolute()
    draw_difference()

if __name__ == '__main__':
    main()
