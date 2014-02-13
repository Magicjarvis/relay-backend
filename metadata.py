import urllib
from pyquery import PyQuery as pq

OG_TAG = "[property='og:%s']"
TWITTER_TAG = "[name='twitter:%s']"
REGULAR_TAG = "[name='%s']"

def query_metas(pq):
  def _query(field):
    og = pq(OG_TAG % field).attr('content')
    return og or pq(TWITTER_TAG % field).attr('content') or pq(REGULAR_TAG % field).attr('content')
  return _query

def scrape(url):
  query = pq(urllib.urlopen(url).read())
  meta_tags = query("meta")

  meta_info ={}

  meta_info['favicon'] = query('link[rel="shortcut icon"]').attr('href')

  get_field = query_metas(meta_tags)
  meta_info['title'] = get_field('title')
  meta_info['description'] = get_field('description')
  meta_info['id'] = get_field('url') or url
  meta_info['image'] = get_field('image')
  meta_info['site'] = meta_tags(OG_TAG % 'site_name').attr('content')
  meta_info['kind'] = meta_tags(OG_TAG % 'type').attr('content')

  return meta_info
