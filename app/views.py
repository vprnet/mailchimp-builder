from index import app
from config import BASE_URL, NPR_API_KEY, API_KEY_URL
from flask import Flask, request, url_for, \
    render_template, flash, make_response
import requests
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
from bs4 import BeautifulSoup

@app.route('/')
def news_feeds():
    """ This view pulls appropriate stories from the NPR API, parses the XML
    to grab the relevant information, and sends that data to a template"""

    url = ('http://api.npr.org/query?id=%s%s'
        '&fields=title,storyDate,teaser,byline,image'
        '&dateType=story&sort=assigned&output=NPRML'
        '&numResults=25&apiKey=%s')
    npr_xml = requests.get(url % ('1001', '', NPR_API_KEY))
    vpr_xml = requests.get(url % ('161419865', '&orgid=692', NPR_API_KEY))
    vt_ed_xml = requests.get(url % ('175255325', '&orgid=692', NPR_API_KEY))
    commentary_xml = requests.get(url % ('176665462', '&orgid=692', NPR_API_KEY))

    npr_root = ET.fromstring(npr_xml.text.encode('utf-8'))
    vpr_root = ET.fromstring(vpr_xml.text.encode('utf-8'))
    vt_ed_root = ET.fromstring(vt_ed_xml.text.encode('utf-8'))
    commentary_root = ET.fromstring(commentary_xml.text.encode('utf-8'))


    def dictionary_generator(root):
        """ Returns an ordered dictionary of desired information """
        story_dict = OrderedDict()
        for story in root.iter('story'):
            story_id = story.attrib['id']
            url = story.find('link').text
            title = story.find('title').text

            if story.find('byline') is not None:
                byline = story.find('byline').find('name').text
            else:
                byline = 'No author listed'
            date = story.find('storyDate').text

            if story.find('teaser') is not None:
                teaser = story.find('teaser').text
            else:
                teaser = ''

            if story.find('image') is not None:
                image = story.find('image').attrib['src']
            else:
                image = 'http://media.tumblr.com/tumblr_lv5hpkCtcs1qejsea.gif'
            story_dict[story_id] = {'title': title, 'byline': byline,
                                    'url': url, 'image': image,
                                    'teaser': teaser, 'date': date}
        return story_dict

    npr_dict = dictionary_generator(npr_root)
    vpr_dict = dictionary_generator(vpr_root)
    vt_ed_dict = dictionary_generator(vt_ed_root)
    commentary_dict = dictionary_generator(commentary_root)
    return render_template('news_feed.html', npr_dict=npr_dict,
                           vpr_dict=vpr_dict, vt_ed_dict=vt_ed_dict,
                           commentary_dict=commentary_dict)


@app.route('/id_list', methods=['GET'])
def id_list():
    """ Allows the user to select stories for publication in News Link and
    generates an HTML snippet which can be pasted into Mailchimp. """

    query_string = request.args
    api_id = query_string.getlist('api_id')
    rank = query_string.getlist('rank')
    rank_list = []
    for i in range(len(rank)):
        if rank[i]:
            rank_list.append(i)

    api_list = []
    for i in rank_list:
        api_list.append((rank[i], api_id[i]))
    api_list.sort()

    story_list = []
    for story in api_list:
        story_list.append(story[1])

    url_part1 = "http://api.npr.org/query?id="
    url_part2 = API_KEY_URL

    story_dict = OrderedDict()
    for story_id in story_list:
        story_url = url_part1 + story_id + url_part2
        story_xml = requests.get(story_url)
        root = ET.fromstring(story_xml.text.encode('utf-8'))
        story = root.find('list').find('story')
        url = story.find('link').text
        title = story.find('title').text
        try:
            byline = story.find('byline').find('name').text
        except AttributeError:
            byline = 'No Author Listed'
        teaser = vpr_teaser(story)
        story_dict[story_id] = {'title': title, 'url': url,
                                'byline': byline, 'teaser': teaser}

    today = datetime.today()
    day_of_week = today.strftime("%A")
    date = today.strftime("%d").lstrip('0')
    month = today.strftime("%B")
    year = today.strftime("%Y")
    date_of_post = day_of_week + " - " + month + " " + date + ", " + year
    flash('IDs successfully posted')

    # resp generates HTML but doesn't return rendered page
    resp = make_response(render_template('mailchimp_template.html',
        story_dict=story_dict, date_of_post=date_of_post,))
    resp.mimetype = 'text/plain'
    return resp

def vpr_teaser(story):
    """ Returns the first paragraph of the VPR story text and assigns
    it to the variable 'teaser' """

    if story.find('text') is not None:
        p_list = story.find('text').findall('paragraph')
        for i in range(len(p_list)):

            if p_list[i].text is not None:
                teaser = BeautifulSoup(p_list[i].text)
                teaser = teaser.prettify(formatter=None)
                break
            else:
                teaser = ''
    else:
        teaser = ''
    return teaser
