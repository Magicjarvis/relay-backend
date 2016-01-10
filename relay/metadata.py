import urllib2
from util import extract_url, add_http
from pyquery import PyQuery as pq


OG_TAG = "[property='og:%s']"
TWITTER_TAG = "[name='twitter:%s']"
REGULAR_TAG = "[name='%s']"

default_http_headers = {
  'User-agent': 'Mozilla/5.0',
}


def query_metas(pq):
  def _query(field):
    og = pq(OG_TAG % field).attr('content')
    return og or pq(TWITTER_TAG % field).attr('content') or pq(REGULAR_TAG % field).attr('content')
  return _query

def relay_url_opener(request):
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
  opener.addheaders = default_http_headers.items()
  return opener.open(request, timeout=60)

def scrape(url):
  response = relay_url_opener(add_http(url))
  content_type = response.info().getheader('Content-Type')
  query = pq(response.read())

  meta_tags = query("meta")

  meta_info ={}

  meta_info['favicon'] = query('link[rel="shortcut icon"]').attr('href')

  get_field = query_metas(meta_tags)
  meta_info['title'] = get_field('title') or query('title').text()
  meta_info['description'] = get_field('description')
  meta_info['id'] = get_field('url') or url
  meta_info['image'] = get_field('image') or (add_http(url) if 'image' in content_type else None)
  meta_info['site'] = meta_tags(OG_TAG % 'site_name').attr('content')
  meta_info['kind'] = meta_tags(OG_TAG % 'type').attr('content')

  return meta_info
