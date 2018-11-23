import requests
from urllib.parse import urlencode
from django.utils import dateparse

def get_location_string(location):
    if 'displayName' in location:
        return location['displayName']
    ads = []
    if 'city' in location:
        ads.append(location['city'])
    if 'state' in location:
        ads.append(location['state'])
    if 'country' in location:
        ads.append(location['country'])
    return ', '.join(ads)


def get_tweets_list_in_campaign(campaign, page_num=1, size=20):
    api_base = 'https://beta-smartz-app.mybluemix.net/'
    query_fields = {
        'from': page_num,
        'size': size,
        'search_term': campaign.search_term,
        'followers': campaign.followers,
        'following': campaign.following,
        # 'posted': campaign.posted_time,
        'location': campaign.location,
        'statuses_count': campaign.statuses_count,
        'sentiment': campaign.sentiment
    }
    query_fields = {k:v for k,v in query_fields.items() if v is not None}
    query = urlencode(query_fields)
    url = '{}?{}'.format(api_base, query)
    response = requests.get(url=url)
    res_json = response.json()
    tweets_list = []
    for item in res_json['tweets']:
        tweet = {}
        tweet['twitter_id'] = int(item['message']['actor']['id'].replace('id:twitter.com:', ''))
        tweet['twitter_username'] = item['message']['actor']['preferredUsername']
        tweet['twitter_display_name'] = item['message']['actor']['displayName']
        tweet['twitter_image'] = item['message']['actor']['image']
        tweet['message'] = item['message']['body']
        tweet['posted_time'] = dateparse.parse_datetime(item['message']['postedTime'])
        tweet['location'] = get_location_string(item['cde']['author']['location'])
        tweets_list.append(tweet)
    return tweets_list


def get_personality_insight_data(twitter_id):
    url = 'https://beta-smartz-app.mybluemix.net/twitter-personality-insights/{}'.format(twitter_id)
    response = requests.get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        return None
